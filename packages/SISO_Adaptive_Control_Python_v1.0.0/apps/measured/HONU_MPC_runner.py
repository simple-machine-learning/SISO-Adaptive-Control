# -*- coding: utf-8 -*-
"""Batch-frozen or sliding-retraining LNU/QNU/MLP identification with receding-horizon MPC."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter_ns
import numpy as np
from scipy.optimize import minimize

from honu_basis import qnu_feature_count, qnu_features, qnu_features_and_jacobian
from lm_identification import solve_linear_lm




IDENTIFICATION_CONFIG_KEYS = (
    "data_source", "honu",
    "plant_learning", "lm_epochs", "lambda",
    "dt_control", "n_y", "n_u", "duration_sec",
    "u_min", "u_max", "tau_u", "excitation_hold_sec",
    "excitation_mode", "u_excitation_mode", "seed",
    "pca_selection_mode", "pca_retained_variability",
    "mlp_hidden_layers", "mlp_epochs", "mlp_learning_rate", "mlp_optimizer", "prediction_target",
)

def identification_config_snapshot(cfg):
    """Canonical subset of GUI settings that determines the identified HONU model."""
    out = {}
    for key in IDENTIFICATION_CONFIG_KEYS:
        if key not in cfg:
            continue
        value = cfg[key]
        if isinstance(value, np.generic):
            value = value.item()
        out[key] = value
    return out

def identification_config_json(cfg):
    return json.dumps(identification_config_snapshot(cfg), sort_keys=True, separators=(",", ":"))

def validate_identification_config(data, cfg):
    """Reject a frozen model if any identification-dependent widget changed."""
    if "identification_config_json" not in data:
        raise ValueError("Identified HONU has no complete configuration signature; identify it again")
    stored = str(np.asarray(data["identification_config_json"]).reshape(-1)[0])
    active = identification_config_json(cfg)
    if stored == active:
        return
    try:
        old = json.loads(stored)
        new = json.loads(active)
    except Exception:
        raise ValueError("Identified HONU configuration signature is invalid")
    changed = []
    for key in sorted(set(old) | set(new)):
        if old.get(key) != new.get(key):
            changed.append(f"{key}: identified={old.get(key)!r}, active={new.get(key)!r}")
    detail = "; ".join(changed[:8])
    if len(changed) > 8:
        detail += f"; and {len(changed)-8} more"
    raise ValueError("Identified HONU does not match current identification settings: " + detail)


def load_measured_dataset(path="data_uy.txt"):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Measured dataset not found: {path}")
    data = np.loadtxt(path, comments="#", ndmin=2)
    if data.shape[1] < 3:
        raise ValueError("Measured dataset must contain columns t, u, y")
    t, u, y = data[:, 0], data[:, 1], data[:, 2]
    if len(t) < 3 or not np.all(np.isfinite(data[:, :3])):
        raise ValueError("Measured dataset is invalid")
    return np.asarray(t,float), np.asarray(u,float), np.asarray(y,float)

def downsample_measured_dataset(t, u, y, target_dt):
    t = np.asarray(t, dtype=float); u = np.asarray(u, dtype=float); y = np.asarray(y, dtype=float)
    raw_dt = float(np.median(np.diff(t)))
    target_dt = float(target_dt)
    if not np.isfinite(target_dt) or target_dt <= 0.0:
        raise ValueError("dt_MPC must be positive")
    if target_dt < raw_dt * (1.0 - 1e-9):
        raise ValueError(f"dt_MPC={target_dt:g} s is smaller than active data sampling {raw_dt:g} s")
    if np.isclose(target_dt, raw_dt, rtol=1e-9, atol=1e-12):
        return t.copy(), u.copy(), y.copy()
    tq = np.arange(t[0], t[-1] + 0.5 * target_dt, target_dt)
    idx = np.searchsorted(t, tq, side="left")
    idx = np.clip(idx, 0, len(t)-1)
    left = np.clip(idx-1, 0, len(t)-1)
    idx = np.where(np.abs(tq-t[left]) <= np.abs(t[idx]-tq), left, idx)
    return tq, u[idx], y[idx]

def honu_plant_step(y_hist, u_hist, local):
    base = current_base_from_hist(np.asarray(y_hist,float), np.asarray(u_hist,float), local)
    value, _ = model_output_and_base_gradient(base, local)
    if not np.isfinite(value):
        raise FloatingPointError("Non-finite trained HONU plant output")
    return float(value)

def input_delay_samples(cfg):
    dt = float(cfg["dt_control"])
    tau = float(cfg.get("tau_u", 0.0))
    if tau < 0.0:
        raise ValueError("tau_u must be non-negative")
    return max(0, int(round(tau / dt)))

def reference_delay_samples(cfg):
    dt = float(cfg["dt_control"])
    tau = float(cfg.get("tau_d", 0.0))
    if tau < 0.0:
        raise ValueError("tau_d must be non-negative")
    return max(0, int(round(tau / dt)))

def build_base_dataset(y, u, ny, nu, delay_u=0):
    """Build [y[k-i], u[k-delay_u-i]] for one-step HONU identification."""
    start = max(ny - 1, delay_u + nu - 1)
    rows, targets = [], []
    last = min(len(u) - 1 + delay_u, len(y) - 2)
    for k in range(start, last + 1):
        base = np.asarray([y[k-i] for i in range(ny)] + [u[k-delay_u-i] for i in range(nu)], dtype=float)
        rows.append(base)
        targets.append(y[k+1])
    if not rows:
        raise ValueError("Insufficient samples for the selected embedding")
    return np.asarray(rows), np.asarray(targets)


def initialise_fixed_pca(y, u, cfg):
    """Compute one frozen PCA/SVD basis from the base regressor matrix.

    PCA is applied to [x_1, ..., x_(n_y+n_u)] before adding x_0=1 and
    before constructing the QNU basis. Centering is used only to obtain the
    fixed PCA directions; fitting and prediction use the uncentred projection.
    """
    base_matrix, _ = build_base_dataset(y, u, cfg["n_y"], cfg["n_u"], input_delay_samples(cfg))
    mean_for_basis = np.mean(base_matrix, axis=0)
    centered = base_matrix - mean_for_basis
    _, singular_values, vt = np.linalg.svd(centered, full_matrices=False)
    if singular_values.size == 0:
        raise ValueError("PCA/SVD failed: empty singular-value spectrum")

    rank_tolerance = singular_values[0] * max(centered.shape) * np.finfo(singular_values.dtype).eps
    rank = int(np.sum(singular_values > rank_tolerance))
    if rank < 1:
        raise ValueError("Initial window has zero PCA rank; increase excitation richness")

    mode = str(cfg.get("pca_selection_mode", "variability")).strip().lower()
    if mode not in {"rank", "variability"}:
        raise ValueError("pca_selection_mode must be 'rank' or 'variability'")

    energy = singular_values[:rank] ** 2
    cumulative = np.cumsum(energy) / np.sum(energy)
    target_variability = float(np.clip(cfg.get("pca_retained_variability", 0.999), 1e-12, 1.0))
    if mode == "rank":
        selected_components = rank
    else:
        selected_components = int(np.searchsorted(cumulative, target_variability, side="left") + 1)
        selected_components = min(max(1, selected_components), rank)

    retained_variability = float(cumulative[selected_components - 1])
    projection = vt[:selected_components].T
    model_feature_count = 1 + selected_components if cfg["honu"] == "LNU" else qnu_feature_count(1 + selected_components)
    return {
        "P": projection,
        "mean_for_basis": mean_for_basis,
        "singular_values": singular_values,
        "rank": rank,
        "rank_tolerance": rank_tolerance,
        "selection_mode": mode,
        "selected_components": selected_components,
        "target_variability": target_variability,
        "retained_variability": retained_variability,
        "raw_feature_count": base_matrix.shape[1],
        "model_feature_count": model_feature_count,
    }


def compressed_state(base, pca):
    """Project the uncentred base regressor into the frozen PCA coordinates."""
    base = np.asarray(base, dtype=float).reshape(-1)
    return pca["P"].T @ base


def model_features(base, model, pca):
    """PCA first, then add x_0=1, then construct the HONU basis."""
    z = compressed_state(base, pca)
    z_aug = np.concatenate(([1.0], z))
    if model == "LNU":
        return z_aug
    return qnu_features(z_aug)


def model_feature_matrix(bases, model, pca):
    """Vectorized HONU design matrix for a matrix of base regressors."""
    bases = np.asarray(bases, dtype=float)
    z = bases @ np.asarray(pca["P"], dtype=float)
    z_aug = np.concatenate((np.ones((z.shape[0], 1), dtype=float), z), axis=1)
    if model == "LNU":
        return z_aug
    rows, cols = np.triu_indices(z_aug.shape[1])
    return z_aug[:, rows] * z_aug[:, cols]


def _fit_mlp_preprocessor(raw_bases, history_dim, cfg):
    raw_bases=np.asarray(raw_bases,float)
    history=np.asarray(raw_bases[:,:history_dim],float)
    future=np.asarray(raw_bases[:,history_dim:],float)
    h_mean=history.mean(axis=0); h_std=history.std(axis=0); h_std=np.where(h_std>1e-12,h_std,1.0)
    hs=(history-h_mean)/h_std
    _,sv,vt=np.linalg.svd(hs-hs.mean(axis=0),full_matrices=False)
    if sv.size:
        tol=sv[0]*max(hs.shape)*np.finfo(float).eps; rank=max(1,int(np.sum(sv>tol)))
        energy=sv[:rank]**2; cum=np.cumsum(energy)/np.sum(energy)
        mode=str(cfg.get('pca_selection_mode','variability')).lower()
        target=float(np.clip(cfg.get('pca_retained_variability',.999),1e-12,1.0))
        n=rank if mode=='rank' else min(rank,max(1,int(np.searchsorted(cum,target)+1)))
        P=vt[:n].T; retained=float(cum[n-1])
    else:
        sv=np.ones(1); tol=0.0; rank=history_dim; n=history_dim; P=np.eye(history_dim); retained=1.0; mode='rank'; target=1.0
    if future.shape[1]:
        f_mean=future.mean(axis=0); f_std=future.std(axis=0); f_std=np.where(f_std>1e-12,f_std,1.0)
    else:
        f_mean=np.empty(0); f_std=np.empty(0)
    return {'history_dim':int(history_dim),'history_mean':h_mean,'history_std':h_std,'P':P,
            'future_mean':f_mean,'future_std':f_std,'singular_values':sv,'rank':rank,'rank_tolerance':tol,
            'selection_mode':mode,'selected_components':n,'target_variability':target,
            'retained_variability':retained,'raw_feature_count':raw_bases.shape[1],
            'model_feature_count':int(n+future.shape[1]), 'mean_for_basis':h_mean}


def _mlp_transform_base(base, prep):
    b=np.asarray(base,float).reshape(-1); hd=int(prep['history_dim'])
    hs=(b[:hd]-prep['history_mean'])/prep['history_std']; z=hs@prep['P']
    if b.size>hd:
        fs=(b[hd:]-prep['future_mean'])/prep['future_std']; return np.r_[z,fs]
    return np.asarray(z,float)


def _mlp_input_jacobian(prep, raw_dim):
    hd=int(prep['history_dim']); P=np.asarray(prep['P'],float); J=np.zeros((P.shape[1]+raw_dim-hd,raw_dim),float)
    J[:P.shape[1],:hd]=(P/np.asarray(prep['history_std'])[:,None]).T
    if raw_dim>hd:
        J[P.shape[1]:,hd:]=np.diag(1.0/np.asarray(prep['future_std']))
    return J

def _parse_mlp_hidden_layers(cfg):
    value=cfg.get('mlp_hidden_layers', None)
    if value is None or value == '':
        value=[int(cfg.get('mlp_hidden_1',32)), int(cfg.get('mlp_hidden_2',32))]
    if isinstance(value,str):
        parts=[part.strip() for part in value.replace(';',',').split(',') if part.strip()]
        try: layers=[int(part) for part in parts]
        except ValueError as exc: raise ValueError("MLP hidden layers must be comma-separated positive integers, e.g. 8 or 16,8") from exc
    else:
        layers=[int(v) for v in np.asarray(value).reshape(-1)]
    if not layers or any(v <= 0 for v in layers):
        raise ValueError("MLP hidden layers must contain at least one positive integer")
    return layers


def _mlp_layer_sizes(n_in, hidden_layers, n_out):
    return [int(n_in), *[int(v) for v in hidden_layers], int(n_out)]


def _mlp_init_parameters(layer_sizes, rng):
    weights=[]; biases=[]
    for index,(n_prev,n_next) in enumerate(zip(layer_sizes[:-1],layer_sizes[1:])):
        scale=np.sqrt(1.0/max(1,n_prev)) if index < len(layer_sizes)-2 else 0.05
        weights.append(rng.normal(0.0,scale,(n_next,n_prev)))
        biases.append(np.zeros(n_next,float))
    return _mlp_pack_layers(weights,biases)


def _mlp_pack_layers(weights,biases):
    chunks=[]
    for W,b in zip(weights,biases): chunks.extend((np.asarray(W,float).ravel(),np.asarray(b,float).ravel()))
    return np.concatenate(chunks)


def _mlp_unpack_layers(theta,layer_sizes):
    theta=np.asarray(theta,float).reshape(-1); weights=[]; biases=[]; i=0
    for n_prev,n_next in zip(layer_sizes[:-1],layer_sizes[1:]):
        n=n_prev*n_next; weights.append(theta[i:i+n].reshape(n_next,n_prev)); i+=n
        biases.append(theta[i:i+n_next]); i+=n_next
    if i != theta.size: raise ValueError(f"MLP parameter size mismatch: used {i}, stored {theta.size}")
    return weights,biases


def _mlp_batch_loss_gradient(theta,bases,target,layer_sizes,target_scale,lam):
    weights,biases=_mlp_unpack_layers(theta,layer_sizes)
    activations=[np.asarray(bases,float)]
    for W,b in zip(weights[:-1],biases[:-1]): activations.append(np.tanh(activations[-1]@W.T+b))
    output=activations[-1]@weights[-1].T+biases[-1]
    target_2d=np.asarray(target,float).reshape(output.shape)
    err=output-target_2d; delta=2.0*err/max(1,err.size)
    grad_w=[None]*len(weights); grad_b=[None]*len(biases)
    grad_w[-1]=delta.T@activations[-1]+lam*weights[-1]; grad_b[-1]=delta.sum(0)
    for layer in range(len(weights)-2,-1,-1):
        delta=(delta@weights[layer+1])*(1.0-activations[layer+1]**2)
        grad_w[layer]=delta.T@activations[layer]+lam*weights[layer]; grad_b[layer]=delta.sum(0)
    gradient=_mlp_pack_layers(grad_w,grad_b)
    loss=float(np.mean(err*err)+0.5*lam*sum(np.sum(W*W) for W in weights))
    rmse=float(np.sqrt(np.mean((target_scale*err)**2)))
    return loss,gradient,rmse


def _mlp_forward_generic(x,theta,layer_sizes,compute_jacobian=True):
    weights,biases=_mlp_unpack_layers(theta,layer_sizes); a=np.asarray(x,float).reshape(-1); hidden=[]
    for W,b in zip(weights[:-1],biases[:-1]):
        a=np.tanh(W@a+b); hidden.append(a)
    out=weights[-1]@a+biases[-1]
    if not compute_jacobian: return out,None
    J=weights[-1].copy()
    for layer in range(len(weights)-2,-1,-1):
        J=(J*(1.0-hidden[layer]**2)[None,:])@weights[layer]
    return out,J


def _local_hidden_layers(local):
    value=local.get('hidden_layers',None)
    if value is not None and len(np.asarray(value).reshape(-1)):
        return [int(v) for v in np.asarray(value).reshape(-1)]
    return [int(local.get('h1',32)),int(local.get('h2',32))]


def _mlp_forward(base, local):
    raw=np.asarray(base,float).reshape(-1); prep=local['mlp_preprocess']; x=_mlp_transform_base(raw,prep)
    hidden=_local_hidden_layers(local); sizes=_mlp_layer_sizes(x.size,hidden,1)
    out_n,Jx=_mlp_forward_generic(x,local['c'],sizes,True)
    target_value=local['target_scale']*float(out_n[0]); is_delta=str(local.get('prediction_target','delta')).lower()=='delta'
    y=float(raw[0]+target_value) if is_delta else float(target_value)
    grad=local['target_scale']*(_mlp_input_jacobian(prep,raw.size).T@Jx.reshape(-1))
    if is_delta: grad[0]+=1.0
    return y,grad


def _direct_mlp_forward_base(base, local, compute_jacobian=True):
    raw=np.asarray(base,float).reshape(-1); prep=local['mlp_preprocess']; x=_mlp_transform_base(raw,prep)
    H=int(local['horizon']); hidden=_local_hidden_layers(local); sizes=_mlp_layer_sizes(x.size,hidden,H)
    out_n,Jx=_mlp_forward_generic(x,local['W'],sizes,compute_jacobian)
    target_values=local['target_scale']*np.asarray(out_n,float); is_delta=str(local.get('prediction_target','delta')).lower()=='delta'
    out=float(raw[0])+target_values if is_delta else target_values
    if not compute_jacobian: return np.asarray(out,float),None
    J=local['target_scale']*(Jx@_mlp_input_jacobian(prep,raw.size))
    if is_delta: J[:,0]+=1.0
    return np.asarray(out,float),np.asarray(J,float)


def _mlp_optimizer_mode(cfg):
    value=str(cfg.get('mlp_optimizer', cfg.get('plant_learning','adam'))).strip().lower()
    aliases={'l-bfgs':'lbfgs','l_bfgs':'lbfgs','adam + l-bfgs':'adam_lbfgs','adam+lbfgs':'adam_lbfgs','hybrid':'adam_lbfgs'}
    return aliases.get(value,value if value in {'adam','lbfgs','adam_lbfgs'} else 'adam_lbfgs')


def _run_lbfgs(theta, loss_grad, maxiter, hist, wh):
    def fun(th):
        loss,grad,rmse=loss_grad(th)
        return float(loss),np.asarray(grad,float)
    def callback(th):
        _,_,rmse=loss_grad(th); hist.append(float(rmse)); wh.append(np.asarray(th,float).copy())
    result=minimize(fun,np.asarray(theta,float),method='L-BFGS-B',jac=True,callback=callback,
                    options={'maxiter':max(1,int(maxiter)),'ftol':1e-12,'gtol':1e-8,'maxls':30})
    theta=np.asarray(result.x,float)
    if not wh or not np.array_equal(wh[-1],theta):
        _,_,rmse=loss_grad(theta); hist.append(float(rmse)); wh.append(theta.copy())
    return theta

def fit_direct_mlp_model(y,u,cfg,return_history=False):
    H=int(cfg['horizon']); raw,Y=build_direct_dataset(y,u,int(cfg['n_y']),int(cfg['n_u']),H,input_delay_samples(cfg))
    hd=int(cfg['n_y'])+int(cfg['n_u']); prep=_fit_mlp_preprocessor(raw,hd,cfg); bases=np.asarray([_mlp_transform_base(b,prep) for b in raw])
    target_mode=str(cfg.get('prediction_target','delta')).lower(); target_physical=Y-raw[:,[0]] if target_mode=='delta' else Y
    target_scale=max(float(np.std(target_physical)),1e-8); target=target_physical/target_scale
    hidden=_parse_mlp_hidden_layers(cfg); sizes=_mlp_layer_sizes(bases.shape[1],hidden,H); rng=np.random.default_rng(int(cfg.get('seed',0)))
    theta=_mlp_init_parameters(sizes,rng); lr=float(cfg.get('mlp_learning_rate',1e-3)); epochs=max(1,int(cfg.get('mlp_epochs',300))); lam=float(cfg.get('lambda',1e-5))
    hist=[]; wh=[]; mode=_mlp_optimizer_mode(cfg)
    def loss_grad(th): return _mlp_batch_loss_gradient(th,bases,target,sizes,target_scale,lam)
    if mode in {'adam','adam_lbfgs'}:
        n_adam=epochs if mode=='adam' else max(1,epochs//2); m=np.zeros_like(theta); v=np.zeros_like(theta)
        for ep in range(1,n_adam+1):
            _,grad,rmse=loss_grad(theta); m=.9*m+.1*grad; v=.999*v+.001*grad*grad; theta-=lr*(m/(1-.9**ep))/(np.sqrt(v/(1-.999**ep))+1e-8); hist.append(rmse); wh.append(theta.copy())
    if mode in {'lbfgs','adam_lbfgs'}: theta=_run_lbfgs(theta,loss_grad,epochs if mode=='lbfgs' else max(1,epochs//2),hist,wh)
    local={'prediction_mode':'direct_multi_horizon','model':'MLP','W':theta,'ny':int(cfg['n_y']),'nu':int(cfg['n_u']),'delay_u':input_delay_samples(cfg),'horizon':H,'pca':prep,'mlp_preprocess':prep,'target_scale':target_scale,'hidden_layers':hidden,'h1':hidden[0],'h2':hidden[1] if len(hidden)>1 else 0,'mlp_optimizer':mode,'prediction_target':target_mode}
    out=(local,theta,np.nan,np.nan)
    if return_history:return out+(np.asarray(hist),np.asarray(wh),np.asarray([],float))
    return out


def fit_mlp_model(y,u,cfg,return_history=False):
    raw,target_y=build_base_dataset(y,u,int(cfg['n_y']),int(cfg['n_u']),input_delay_samples(cfg)); prep=_fit_mlp_preprocessor(raw,raw.shape[1],cfg); bases=np.asarray([_mlp_transform_base(b,prep) for b in raw])
    target_mode=str(cfg.get('prediction_target','delta')).lower(); target_physical=target_y-raw[:,0] if target_mode=='delta' else target_y
    target_scale=max(float(np.std(target_physical)),1e-8); target=(target_physical/target_scale).reshape(-1,1)
    hidden=_parse_mlp_hidden_layers(cfg); sizes=_mlp_layer_sizes(bases.shape[1],hidden,1); rng=np.random.default_rng(int(cfg.get('seed',0)))
    theta=_mlp_init_parameters(sizes,rng); lr=float(cfg.get('mlp_learning_rate',1e-3)); epochs=max(1,int(cfg.get('mlp_epochs',300))); lam=float(cfg.get('lambda',1e-5)); hist=[]; wh=[]; mode=_mlp_optimizer_mode(cfg)
    def loss_grad(th): return _mlp_batch_loss_gradient(th,bases,target,sizes,target_scale,lam)
    if mode in {'adam','adam_lbfgs'}:
        n_adam=epochs if mode=='adam' else max(1,epochs//2); m=np.zeros_like(theta); v=np.zeros_like(theta)
        for ep in range(1,n_adam+1):
            _,grad,rmse=loss_grad(theta); m=.9*m+.1*grad; v=.999*v+.001*grad*grad; theta-=lr*(m/(1-.9**ep))/(np.sqrt(v/(1-.999**ep))+1e-8); hist.append(rmse); wh.append(theta.copy())
    if mode in {'lbfgs','adam_lbfgs'}: theta=_run_lbfgs(theta,loss_grad,epochs if mode=='lbfgs' else max(1,epochs//2),hist,wh)
    local={'prediction_mode':'recursive','model':'MLP','c':theta,'ny':int(cfg['n_y']),'nu':int(cfg['n_u']),'delay_u':input_delay_samples(cfg),'pca':prep,'mlp_preprocess':prep,'target_scale':target_scale,'hidden_layers':hidden,'h1':hidden[0],'h2':hidden[1] if len(hidden)>1 else 0,'mlp_optimizer':mode,'prediction_target':target_mode}
    rho=exact_local_output_spectral_radius(raw[-1],local); out=(local,theta,np.nan,rho)
    if return_history:return out+(np.asarray(hist),np.asarray(wh),np.asarray([],float))
    return out



def model_output_and_base_gradient(base, local):
    """Return HONU output and exact gradient with respect to the base regressor."""
    base = np.asarray(base, dtype=float).reshape(-1)
    if local.get("model") == "MLP":
        return _mlp_forward(base, local)
    theta = np.asarray(local["c"], dtype=float)
    pca = local["pca"]
    z = compressed_state(base, pca)
    z_aug = np.concatenate(([1.0], z))
    if local["model"] == "LNU":
        output = float(theta @ z_aug)
        grad_base = np.asarray(pca["P"], dtype=float) @ theta[1:]
    else:
        features, jac_qnu = qnu_features_and_jacobian(z_aug)
        output = float(theta @ features)
        grad_z_aug = theta @ jac_qnu
        grad_base = np.asarray(pca["P"], dtype=float) @ grad_z_aug[1:]
    if str(local.get("prediction_target","absolute")).lower()=="delta":
        output += float(base[0])
        grad_base = np.asarray(grad_base,dtype=float)
        grad_base[0] += 1.0
    return output, np.asarray(grad_base, dtype=float)


def exact_local_output_spectral_radius(base, local):
    """Return the exact local output-history spectral radius.

    For LNU this is rho(A_y). For nonlinear QNU and MLP models it is the
    spectral radius of the local Jacobian J_y(k), with the input-history
    coordinates held fixed. The companion shift rows are included, so the
    diagnostic describes the complete output-history recursion used by MPC.
    """
    base = np.asarray(base, dtype=float).reshape(-1)
    ny = int(local["ny"])
    if local.get("model") == "MLP":
        _, grad_base = _mlp_forward(base, local)
    else:
        theta = np.asarray(local["c"], dtype=float)
        pca = local["pca"]
        if local["model"] == "LNU":
            grad_base = pca["P"] @ theta[1:]
        else:
            z = compressed_state(base, pca)
            z_aug = np.concatenate(([1.0], z))
            _, jac_qnu = qnu_features_and_jacobian(z_aug)
            grad_z_aug = theta @ jac_qnu
            grad_base = pca["P"] @ grad_z_aug[1:]
        if str(local.get("prediction_target","absolute")).lower()=="delta":
            grad_base=np.asarray(grad_base,float).copy(); grad_base[0]+=1.0
    Ay = np.zeros((ny, ny), dtype=float)
    Ay[0, :] = grad_base[:ny]
    if ny > 1:
        Ay[1:, :-1] = np.eye(ny - 1)
    return float(np.max(np.abs(np.linalg.eigvals(Ay))))


def base_at_index(y, u, k, local):
    """Current regressor [y(k-i), u(k-delay-i)] for local diagnostics."""
    ny, nu = int(local["ny"]), int(local["nu"])
    delay_u = int(local.get("delay_u", 0))
    y_part = [float(y[k-i]) if k-i >= 0 else 0.0 for i in range(ny)]
    u_part = [float(u[k-delay_u-i]) if k-delay_u-i >= 0 else 0.0 for i in range(nu)]
    return np.asarray(y_part + u_part, dtype=float)


def fit_model(y, u, cfg, pca, return_history=False):
    if str(cfg.get("honu", "LNU")).upper() == "MLP":
        return fit_mlp_model(y, u, cfg, return_history=return_history)
    model, ny, nu = cfg["honu"], cfg["n_y"], cfg["n_u"]
    bases, target = build_base_dataset(y, u, ny, nu, input_delay_samples(cfg))
    Phi = model_feature_matrix(bases, model, pca)
    identification_method = str(cfg.get("plant_learning", "ridge")).strip().lower()
    rho_aw_history = np.asarray([], dtype=float)
    if identification_method == "ridge":
        reg = float(cfg.get("lambda", cfg.get("ridge", 0.1))) * np.eye(Phi.shape[1])
        reg[0, 0] = 0.0
        theta = np.linalg.solve(Phi.T @ Phi + reg, Phi.T @ target)
        weight_history = theta[None, :]
        residual = target - Phi @ theta
        rmse_history = np.asarray([np.sqrt(np.mean(residual**2))], dtype=float)
    elif identification_method == "lm":
        theta, weight_history, sse_history, damping_history = solve_linear_lm(
            Phi, target,
            iterations=int(cfg.get("lm_epochs", cfg.get("lm_iterations", 20))),
            damping=float(cfg.get("lambda", cfg.get("lm_lambda", cfg.get("ridge", 1.0e-2)))),
            verbose=False,
        )
        rmse_history = np.sqrt(np.maximum(sse_history, 0.0) / max(1, target.size))
        hessian = Phi.T @ Phi
        diagonal = np.maximum(np.diag(hessian), 1.0e-12)
        damping_matrix = np.diag(diagonal)
        identity = np.eye(hessian.shape[0], dtype=float)
        rho_aw_values = []
        for damping in np.asarray(damping_history, dtype=float).reshape(-1):
            system = hessian + float(damping) * damping_matrix
            try:
                update_map = identity - np.linalg.solve(system, hessian)
            except np.linalg.LinAlgError:
                update_map = identity - (np.linalg.pinv(system) @ hessian)
            rho_aw_values.append(float(np.max(np.abs(np.linalg.eigvals(update_map)))))
        rho_aw_history = np.asarray(rho_aw_values, dtype=float)
    else:
        raise ValueError(f"Unsupported plant_learning: {identification_method}")

    local_model = {"model": model, "c": theta, "ny": ny, "nu": nu,
                   "delay_u": input_delay_samples(cfg), "pca": pca}
    rho_aw = float(rho_aw_history[-1]) if rho_aw_history.size else np.nan
    rho_ay = exact_local_output_spectral_radius(bases[-1], local_model)

    result = (local_model, theta, rho_aw, rho_ay)
    if return_history:
        return result + (
            np.asarray(rmse_history, dtype=float),
            np.asarray(weight_history, dtype=float),
            np.asarray(rho_aw_history, dtype=float),
        )
    return result


def prepare_prediction_history(y_hist, u_hist, local):
    """Keep only the history tails needed by one MPC horizon rollout."""
    ny, nu = int(local["ny"]), int(local["nu"])
    delay_u = int(local.get("delay_u", 0))
    y = np.asarray(y_hist, dtype=float).reshape(-1)
    u = np.asarray(u_hist, dtype=float).reshape(-1)
    y_tail = y[-ny:].tolist()
    u_keep = max(0, delay_u + nu)
    u_tail = u[-u_keep:].tolist() if u_keep else []
    return y_tail, u_tail


def predict_sequence(candidate_u, y_hist, u_hist, local):
    y_out, _ = predict_sequence_and_jacobian(candidate_u, y_hist, u_hist, local, compute_jacobian=False)
    return y_out


def predict_sequence_and_jacobian(candidate_u, y_hist, u_hist, local, compute_jacobian=True):
    """Roll the HONU model forward and optionally return dy_h/d(candidate_u)."""
    candidate_u = np.asarray(candidate_u, dtype=float).reshape(-1)
    horizon = candidate_u.size
    ny, nu = int(local["ny"]), int(local["nu"])
    delay_u = int(local.get("delay_u", 0))
    y_seq, u_seq = prepare_prediction_history(y_hist, u_hist, local)
    y_grad_seq = [np.zeros(horizon, dtype=float) for _ in y_seq]
    u_grad_seq = [np.zeros(horizon, dtype=float) for _ in u_seq]
    y_out = np.empty(horizon, dtype=float)
    jacobian = np.zeros((horizon, horizon), dtype=float) if compute_jacobian else None

    for h, uk in enumerate(candidate_u):
        u_seq.append(float(uk))
        if compute_jacobian:
            grad_uk = np.zeros(horizon, dtype=float)
            grad_uk[h] = 1.0
            u_grad_seq.append(grad_uk)

        y_part = [y_seq[-1-i] if len(y_seq) > i else 0.0 for i in range(ny)]
        u_part = []
        for i in range(nu):
            idx = len(u_seq) - 1 - delay_u - i
            u_part.append(u_seq[idx] if idx >= 0 else 0.0)
        base = np.asarray(y_part + u_part, dtype=float)

        if compute_jacobian:
            base_grad = np.zeros((ny + nu, horizon), dtype=float)
            for i in range(ny):
                if len(y_grad_seq) > i:
                    base_grad[i] = y_grad_seq[-1-i]
            for i in range(nu):
                idx = len(u_grad_seq) - 1 - delay_u - i
                if idx >= 0:
                    base_grad[ny+i] = u_grad_seq[idx]
            y_next, grad_base = model_output_and_base_gradient(base, local)
            y_next_grad = grad_base @ base_grad
            jacobian[h] = y_next_grad
            y_grad_seq.append(y_next_grad)
        else:
            y_next, _ = model_output_and_base_gradient(base, local)

        y_out[h] = y_next
        y_seq.append(y_next)

    return y_out, jacobian


def current_base_from_hist(y_hist, u_hist, local):
    """Return the current local regressor before the new MPC action is applied."""
    ny, nu = int(local["ny"]), int(local["nu"])
    delay_u = int(local.get("delay_u", 0))
    y_seq, u_seq = prepare_prediction_history(y_hist, u_hist, local)
    y_part = [y_seq[-1-i] if len(y_seq) > i else 0.0 for i in range(ny)]
    u_part = []
    for i in range(nu):
        idx = len(u_seq) - 1 - delay_u - i
        u_part.append(u_seq[idx] if idx >= 0 else 0.0)
    return np.asarray(y_part + u_part, dtype=float)


def optimize_u(ref, y_hist, u_hist, local, warm, cfg):
    """Compute the MPC move by damped iterative least squares (Gauss-Newton).

    The same solver is used for LNU and QNU prediction models.  Unlike an
    unconstrained BFGS line search, every trial step is local and is accepted
    only when the true nonlinear MPC objective decreases.  This is essential
    for recursive QNU rollouts, where a remote trial point can overflow before
    it has any physical meaning.
    """
    ref = np.asarray(ref, dtype=float).reshape(-1)
    h = ref.size
    prev = float(u_hist[-1]) if len(u_hist) else 0.0
    prev2 = float(u_hist[-2]) if len(u_hist) > 1 else prev
    x = np.full(h, prev, dtype=float) if warm is None or len(warm) != h else np.r_[warm[1:], warm[-1]].astype(float)
    if not np.all(np.isfinite(x)):
        x = np.full(h, prev, dtype=float)

    q, rd, rd2, ru = (max(0.0, float(cfg[k])) for k in ("q_track", "r_du", "r_ddu", "r_u"))

    # Constant finite-difference operators for delta-u and delta-delta-u penalties.
    D1 = np.eye(h, dtype=float)
    if h > 1:
        D1[np.arange(1, h), np.arange(h-1)] = -1.0
    b1 = np.zeros(h, dtype=float)
    b1[0] = -prev

    D2 = np.eye(h, dtype=float)
    if h > 1:
        D2[np.arange(1, h), np.arange(h-1)] = -2.0
    if h > 2:
        D2[np.arange(2, h), np.arange(h-2)] = 1.0
    b2 = np.zeros(h, dtype=float)
    b2[0] = -2.0 * prev + prev2
    if h > 1:
        b2[1] = prev

    sq_q, sq_rd, sq_rd2, sq_ru = np.sqrt(q), np.sqrt(rd), np.sqrt(rd2), np.sqrt(ru)
    eye_h = np.eye(h, dtype=float)

    def residual_and_jacobian(candidate, with_jacobian):
        candidate = np.asarray(candidate, dtype=float).reshape(-1)
        if candidate.size != h or not np.all(np.isfinite(candidate)):
            return None, None, np.inf
        try:
            yh, Jy = predict_sequence_and_jacobian(
                candidate, y_hist, u_hist, local, compute_jacobian=with_jacobian
            )
        except (FloatingPointError, OverflowError, ValueError, np.linalg.LinAlgError):
            return None, None, np.inf
        if not np.all(np.isfinite(yh)) or (with_jacobian and not np.all(np.isfinite(Jy))):
            return None, None, np.inf

        tracking = yh - ref
        du = D1 @ candidate + b1
        ddu = D2 @ candidate + b2
        residual = np.concatenate((
            sq_q * tracking,
            sq_rd * du,
            sq_rd2 * ddu,
            sq_ru * candidate,
        ))
        if not np.all(np.isfinite(residual)):
            return None, None, np.inf
        value = float(residual @ residual)
        if not with_jacobian:
            return residual, None, value
        jac = np.vstack((
            sq_q * Jy,
            sq_rd * D1,
            sq_rd2 * D2,
            sq_ru * eye_h,
        ))
        if not np.all(np.isfinite(jac)):
            return None, None, np.inf
        return residual, jac, value

    _, _, value = residual_and_jacobian(x, False)
    if not np.isfinite(value):
        # The shifted warm start can be invalid for a recursive QNU model.
        x = np.full(h, prev, dtype=float)
        _, _, value = residual_and_jacobian(x, False)
    if not np.isfinite(value):
        return x, False, np.nan

    # A dimensionless local trust radius.  It limits one GN correction, not the
    # final control signal; repeated accepted corrections may still move U far.
    excitation_span = abs(float(cfg.get("u_max", 1.0)) - float(cfg.get("u_min", -1.0)))
    trust_radius = max(1.0e-6, 0.5 * max(excitation_span, abs(prev), 1.0)) * np.sqrt(h)
    max_trust_radius = max(trust_radius, 8.0 * max(excitation_span, abs(prev), 1.0) * np.sqrt(h))
    damping = max(1.0e-8, 1.0e-4 * (q + rd + rd2 + ru + 1.0))
    success = False

    for _ in range(max(1, int(cfg["opt_iter"]))):
        residual, jac, value = residual_and_jacobian(x, True)
        if residual is None:
            damping *= 10.0
            trust_radius *= 0.25
            if trust_radius <= 1.0e-12:
                break
            continue

        # Solve the regularized linearized residual problem directly as least
        # squares; do not form J.T @ J (which squares the condition number).
        A = np.vstack((jac, np.sqrt(damping) * eye_h))
        b = np.concatenate((-residual, np.zeros(h, dtype=float)))
        try:
            step = np.linalg.lstsq(A, b, rcond=None)[0]
        except np.linalg.LinAlgError:
            damping *= 10.0
            continue
        if not np.all(np.isfinite(step)):
            damping *= 10.0
            continue

        step_norm = float(np.linalg.norm(step))
        if step_norm <= 1.0e-9 * (1.0 + float(np.linalg.norm(x))):
            success = True
            break
        if step_norm > trust_radius:
            step *= trust_radius / step_norm

        accepted = False
        alpha = 1.0
        best_x, best_value = x, value
        for _backtrack in range(12):
            trial = x + alpha * step
            _, _, trial_value = residual_and_jacobian(trial, False)
            if np.isfinite(trial_value) and trial_value < best_value:
                best_x, best_value = trial, trial_value
                accepted = True
                break
            alpha *= 0.5

        if accepted:
            relative_drop = (value - best_value) / max(1.0, value)
            x, value = best_x, best_value
            damping = max(1.0e-12, damping * 0.3)
            trust_radius = min(max_trust_radius, trust_radius * 1.5)
            success = True
            if relative_drop <= 1.0e-10:
                break
        else:
            damping *= 10.0
            trust_radius *= 0.5
            if trust_radius <= 1.0e-12:
                break

    return np.asarray(x, dtype=float), bool(success), float(value) if np.isfinite(value) else np.nan



def selected_step_mode(cfg, key):
    """Return the explicitly selected GUI step mode for u or d."""
    mode = str(cfg.get(key, cfg.get("excitation_mode", "random_steps"))).strip().lower()
    aliases = {
        "random steps": "random_steps",
        "alternating steps": "alternating_steps",
        "random_steps": "random_steps",
        "alternating_steps": "alternating_steps",
    }
    if mode not in aliases:
        raise ValueError(f"Unsupported step mode: {mode}")
    return aliases[mode]

def make_reference(n, excitation, cfg, rng):
    """Generate MPC reference d using the same selected step mode as excitation u."""
    d = np.zeros(n)
    lo, hi = float(cfg["d_min"]), float(cfg["d_max"])
    if not lo < hi:
        raise ValueError("d_min must be smaller than d_max")
    hold = max(1, int(round(float(cfg["hold_sec"]) / float(cfg["dt_control"]))))
    active = max(0, n - excitation)
    blocks = max(1, int(np.ceil(active / hold)))
    excitation_mode = selected_step_mode(cfg, "d_reference_mode")
    if excitation_mode == "alternating_steps":
        values = np.where(np.arange(blocks) % 2 == 0, hi, lo).astype(float)
    elif excitation_mode == "random_steps":
        values = rng.uniform(lo, hi, size=blocks)
    else:
        raise ValueError(f"Unsupported excitation_mode: {excitation_mode}")
    for k in range(excitation, n):
        d[k] = values[min((k - excitation) // hold, blocks - 1)]
    a1 = np.exp(-float(cfg["dt_control"])/float(cfg["tau1"]))
    a2 = np.exp(-float(cfg["dt_control"])/float(cfg["tau2"]))
    ym = np.zeros(n); z1 = 0.0; z2 = 0.0
    delay_d = reference_delay_samples(cfg)
    for k in range(n):
        d_delayed = d[k-delay_d] if k >= delay_d else 0.0
        z1 = a1*z1 + (1-a1)*d_delayed; z2 = a2*z2 + (1-a2)*z1; ym[k] = z2
    return d, ym



def run_simulation_only(cfg):
    t, u, y = load_measured_dataset(cfg.get("data_file", "data_uy.txt"))
    t_mpc, u_mpc, y_mpc = downsample_measured_dataset(t, u, y, cfg["dt_control"])
    return dict(t=t, u=u, y=y, t_mpc=t_mpc, u_mpc=u_mpc, y_mpc=y_mpc,
                config_dt_control=np.asarray([float(cfg["dt_control"])]),
                run_mode=np.asarray(["simulate"]))

def effective_window_samples(cfg):
    """Convert the user-entered sliding-window duration to MPC samples."""
    dt_mpc = float(cfg["dt_control"])
    if dt_mpc <= 0.0:
        raise ValueError("dt_MPC must be positive")
    if "window_length_sec" in cfg:
        window_length_sec = float(cfg["window_length_sec"])
    else:
        # Backward compatibility for older saved configurations.
        window_length_sec = float(cfg["window_samples"]) * dt_mpc
    if window_length_sec <= 0.0:
        raise ValueError("window_length_sec must be positive")
    requested = max(1, int(np.ceil(window_length_sec / dt_mpc)))
    minimum = max(int(cfg["n_y"]), input_delay_samples(cfg) + int(cfg["n_u"])) + 3
    samples = max(requested, minimum)
    return samples, samples * dt_mpc

def generate_full_identification_data(cfg, rng, total):
    t, u, y = load_measured_dataset(cfg.get("data_file", "data_uy.txt"))
    _t, u, y = downsample_measured_dataset(t, u, y, cfg["dt_control"])
    return y, u


def run_identify(cfg):
    """Simulate a complete identification record and batch-train one HONU plant model."""
    rng = np.random.default_rng(int(cfg["seed"]))
    dt = float(cfg["dt_control"])
    train_y, train_u = generate_full_identification_data(cfg, rng, 0)
    total = len(train_y)
    t_raw, u_raw, y_raw = load_measured_dataset(cfg.get("data_file", "data_uy.txt"))
    t_measured, _, _ = downsample_measured_dataset(t_raw, u_raw, y_raw, cfg["dt_control"])
    ident_start = perf_counter_ns()
    pca = None if str(cfg.get("honu", "LNU")).upper() == "MLP" else initialise_fixed_pca(train_y, train_u[:-1], cfg)
    local, theta, rho_aw0, rho_ay0, rmse_history, weight_history, rho_aw_history = fit_model(
        train_y, train_u[:-1], cfg, pca, return_history=True)
    pca = local["pca"]
    batch_ident_time = (perf_counter_ns() - ident_start) * 1.0e-9

    bases, targets = build_base_dataset(train_y, train_u[:-1], cfg["n_y"], cfg["n_u"], input_delay_samples(cfg))
    if str(cfg.get("honu", "LNU")).upper() == "MLP":
        predictions = np.asarray([model_output_and_base_gradient(base, local)[0] for base in bases], dtype=float)
    else:
        Phi = model_feature_matrix(bases, cfg["honu"], pca)
        predictions = Phi @ theta
    y_n = np.full(total, np.nan, dtype=float)
    first_target = total - len(targets)
    y_n[first_target:first_target + len(predictions)] = predictions
    error = train_y - y_n

    epochs = np.arange(1, len(rmse_history) + 1, dtype=int)
    return dict(
        t=t_measured, y=train_y, y_n=y_n, e_ident=error, u=train_u,
        w=np.asarray(theta)[None, :], training_epochs=epochs,
        training_rmse=np.asarray(rmse_history, dtype=float),
        training_weight_history=np.asarray(weight_history, dtype=float),
        rho_aw=np.asarray(rho_aw_history, dtype=float),
        rho_ay=np.asarray([exact_local_output_spectral_radius(base_at_index(train_y, train_u, k, local), local)
                           if k >= max(int(local["ny"])-1, int(local.get("delay_u", 0))+int(local["nu"])-1) else np.nan
                           for k in range(total)], dtype=float),
        pca_rank=np.asarray([pca["rank"]], dtype=int),
        pca_raw_feature_count=np.asarray([pca["raw_feature_count"]], dtype=int),
        pca_rank_tolerance=np.asarray([pca["rank_tolerance"]], dtype=float),
        pca_selection_mode=np.asarray([pca["selection_mode"]]),
        pca_selected_components=np.asarray([pca["selected_components"]], dtype=int),
        pca_target_variability=np.asarray([pca["target_variability"]], dtype=float),
        pca_retained_variability=np.asarray([pca["retained_variability"]], dtype=float),
        model_feature_count=np.asarray([pca["model_feature_count"]], dtype=int),
        pca_singular_values=np.asarray(pca["singular_values"], dtype=float),
        pca_projection=np.asarray(pca["P"], dtype=float),
        pca_mean_for_basis=np.asarray(pca["mean_for_basis"], dtype=float),
        mlp_history_dim=np.asarray([int(pca.get("history_dim", pca["raw_feature_count"]))], dtype=int),
        mlp_history_mean=np.asarray(pca.get("history_mean", pca["mean_for_basis"]), dtype=float),
        mlp_history_std=np.asarray(pca.get("history_std", np.ones(pca["raw_feature_count"])), dtype=float),
        mlp_future_mean=np.asarray(pca.get("future_mean", []), dtype=float),
        mlp_future_std=np.asarray(pca.get("future_std", []), dtype=float),
        theta=np.asarray(theta, dtype=float),
        mlp_hidden_layers=np.asarray(local.get("hidden_layers", []), dtype=int),
        mlp_target_scale=np.asarray([float(local.get("target_scale", 1.0))], dtype=float),
        prediction_target=np.asarray([str(local.get("prediction_target", "absolute"))]),
        mlp_optimizer=np.asarray([str(local.get("mlp_optimizer", ""))]),
        model=np.asarray([local["model"]]), ny=np.asarray([local["ny"]], dtype=int),
        nu=np.asarray([local["nu"]], dtype=int), delay_u=np.asarray([local["delay_u"]], dtype=int),
        identification_time_sec=np.asarray([batch_ident_time], dtype=float),
        run_mode=np.asarray(["identify"]), mpc_model_mode=np.asarray(["batch_identified"]),
        preg_blackbox_enabled=np.asarray([bool(cfg.get("preg_blackbox_enabled", False))]),
        r_preg=np.asarray([float(cfg.get("r_preg", 1.0))]),
        plant_learning=np.asarray([str(cfg.get("plant_learning", "ridge"))]),
        config_data_source=np.asarray([str(cfg.get("data_source", "measured"))]),
        config_honu=np.asarray([str(cfg["honu"])]),
        config_n_y=np.asarray([int(cfg["n_y"])], dtype=int),
        config_n_u=np.asarray([int(cfg["n_u"])], dtype=int),
        config_dt_control=np.asarray([float(cfg["dt_control"])], dtype=float),
        config_tau_u=np.asarray([float(cfg["tau_u"])], dtype=float),
        config_preg_blackbox_enabled=np.asarray([bool(cfg.get("preg_blackbox_enabled", False))]),
        config_r_preg=np.asarray([float(cfg.get("r_preg", 1.0))], dtype=float),
        identification_config_json=np.asarray([identification_config_json(cfg)]),
    )


def load_identified_local(path):
    data = np.load(path, allow_pickle=False)
    pca = {
        "P": np.asarray(data["pca_projection"], dtype=float),
        "mean_for_basis": np.asarray(data["pca_mean_for_basis"], dtype=float),
        "singular_values": np.asarray(data["pca_singular_values"], dtype=float),
        "rank": int(np.asarray(data["pca_rank"]).ravel()[0]),
        "rank_tolerance": float(np.asarray(data["pca_rank_tolerance"]).ravel()[0]),
        "selection_mode": str(np.asarray(data["pca_selection_mode"]).ravel()[0]),
        "selected_components": int(np.asarray(data["pca_selected_components"]).ravel()[0]),
        "target_variability": float(np.asarray(data["pca_target_variability"]).ravel()[0]),
        "retained_variability": float(np.asarray(data["pca_retained_variability"]).ravel()[0]),
        "raw_feature_count": int(np.asarray(data["pca_projection"]).shape[0]),
        "model_feature_count": int(np.asarray(data["model_feature_count"]).ravel()[0]),
    }
    theta = np.asarray(data["theta"], dtype=float)
    model_name = str(np.asarray(data["model"]).ravel()[0])
    local = {
        "model": model_name, "c": theta,
        "ny": int(np.asarray(data["ny"]).ravel()[0]), "nu": int(np.asarray(data["nu"]).ravel()[0]),
        "delay_u": int(np.asarray(data["delay_u"]).ravel()[0]), "pca": pca,
    }
    if model_name.upper() == "MLP":
        pca.update({
            "history_dim": int(np.asarray(data.get("mlp_history_dim", [pca["raw_feature_count"]])).ravel()[0]),
            "history_mean": np.asarray(data.get("mlp_history_mean", pca["mean_for_basis"]), dtype=float),
            "history_std": np.asarray(data.get("mlp_history_std", np.ones(pca["raw_feature_count"])), dtype=float),
            "future_mean": np.asarray(data.get("mlp_future_mean", []), dtype=float),
            "future_std": np.asarray(data.get("mlp_future_std", []), dtype=float),
        })
        hidden = [int(v) for v in np.asarray(data.get("mlp_hidden_layers", [32, 32])).reshape(-1)]
        local.update({
            "mlp_preprocess": pca, "hidden_layers": hidden,
            "h1": hidden[0] if hidden else 32, "h2": hidden[1] if len(hidden) > 1 else 0,
            "target_scale": float(np.asarray(data.get("mlp_target_scale", [1.0])).ravel()[0]),
            "prediction_target": str(np.asarray(data.get("prediction_target", ["delta"])).ravel()[0]),
            "mlp_optimizer": str(np.asarray(data.get("mlp_optimizer", [""])).ravel()[0]),
            "prediction_mode": "recursive",
        })
    rho_aw_values = np.asarray(data.get("rho_aw", []), dtype=float).ravel()
    rho_ay_values = np.asarray(data.get("rho_ay", []), dtype=float).ravel()
    rho_aw0 = float(rho_aw_values[0]) if rho_aw_values.size else float("nan")
    finite_ay = rho_ay_values[np.isfinite(rho_ay_values)]
    rho_ay0 = float(finite_ay[0]) if finite_ay.size else float("nan")
    return local, theta, rho_aw0, rho_ay0

def run_frozen(cfg):
    """Load the model produced by Identify HONU Plant and keep it frozen in MPC."""
    rng = np.random.default_rng(int(cfg["seed"]))
    dt = float(cfg["dt_control"])
    total = max(2, int(round(float(cfg.get("reference_duration_sec", cfg["duration_sec"])) / dt)) + 1)
    model_path = Path(cfg.get("identified_model_file", ""))
    if not model_path.exists():
        raise FileNotFoundError("Frozen MPC requires an existing identified_model_file")
    data = np.load(model_path, allow_pickle=False)
    local, theta, rho_aw0, rho_ay0 = load_identified_local(model_path)
    pca = local["pca"]
    batch_ident_time = 0.0

    d, ym = make_reference(total, 0, cfg, rng)
    t = np.arange(total) * dt
    y = np.zeros(total); u = np.zeros(total)
    _tm, _um, ym_data = load_measured_dataset(cfg.get("data_file", "data_uy.txt"))
    y[0] = float(ym_data[0])
    pred = np.full(total, np.nan); obj = np.full(total, np.nan); ok = np.zeros(total)
    w_trace = np.full((total, len(theta)), np.nan); w_trace[:] = theta
    rho_aw = np.full(total, np.nan); rho_ay = np.full(total, np.nan)
    identification_time_sec = np.full(total, np.nan); identification_time_sec[0] = batch_ident_time
    control_time_sec = np.full(total, np.nan)
    warm = None
    for k in range(total - 1):
        h = min(int(cfg["horizon"]), total - k - 1)
        start = perf_counter_ns()
        seq, success, value = optimize_u(ym[k+1:k+1+h], y[:k+1], u[:k], local, None if warm is None else warm[:h], cfg)
        control_time_sec[k] = (perf_counter_ns() - start) * 1e-9
        u[k] = seq[0]; warm = seq; ok[k] = success; obj[k] = value
        pred[k+1] = predict_sequence(seq[:1], y[:k+1], u[:k], local)[0]
        rho_ay[k] = exact_local_output_spectral_radius(current_base_from_hist(y[:k+1], u[:k], local), local)
        y[k+1] = honu_plant_step(y[:k+1], u[:k+1], local)
    u[-1] = u[-2]
    rho_ay[-1] = exact_local_output_spectral_radius(base_at_index(y, u, total - 1, local), local)
    e = ym - y
    return dict(
        t=t, d=d, ym=ym, y=y, u=u, e=e, pred=pred, objective=obj,
        optimizer_ok=ok, w=w_trace, rho_aw=rho_aw, rho_ay=rho_ay,
        excitation_index=np.asarray([0]),
        window_samples_effective=np.asarray([total - 1], dtype=int),
        window_length_sec_requested=np.asarray([float(cfg.get("reference_duration_sec", cfg["duration_sec"]))], dtype=float),
        window_length_sec_effective=np.asarray([float(cfg.get("reference_duration_sec", cfg["duration_sec"]))], dtype=float),
        pca_rank=np.asarray([pca["rank"]], dtype=int),
        pca_rank_tolerance=np.asarray([pca["rank_tolerance"]], dtype=float),
        pca_selection_mode=np.asarray([pca["selection_mode"]]),
        pca_selected_components=np.asarray([pca["selected_components"]], dtype=int),
        pca_target_variability=np.asarray([pca["target_variability"]], dtype=float),
        pca_retained_variability=np.asarray([pca["retained_variability"]], dtype=float),
        pca_raw_feature_count=np.asarray([pca["raw_feature_count"]], dtype=int),
        model_feature_count=np.asarray([pca["model_feature_count"]], dtype=int),
        pca_singular_values=np.asarray(pca["singular_values"], dtype=float),
        pca_projection=np.asarray(pca["P"], dtype=float), pca_mean_for_basis=np.asarray(pca["mean_for_basis"], dtype=float),
        identification_time_sec=identification_time_sec, control_time_sec=control_time_sec,
        run_mode=np.asarray(["mpc_frozen"]), mpc_model_mode=np.asarray(["frozen_batch"]),
        preg_blackbox_enabled=np.asarray([bool(cfg.get("preg_blackbox_enabled", False))]),
        r_preg=np.asarray([float(cfg.get("r_preg", 1.0))]), plant_learning=np.asarray([str(cfg.get("plant_learning", "ridge"))]),
        config_data_source=np.asarray([str(cfg.get("data_source", "measured"))]), config_honu=np.asarray([str(cfg["honu"])]),
        config_n_y=np.asarray([int(cfg["n_y"])], dtype=int), config_n_u=np.asarray([int(cfg["n_u"])], dtype=int),
        config_dt_control=np.asarray([float(cfg["dt_control"])], dtype=float),
        config_horizon=np.asarray([int(cfg["horizon"])], dtype=int),
        identification_config_json=np.asarray([identification_config_json(cfg)]),
        honu_source=np.asarray(["loaded_identified_model"]),
    )


def run(cfg):
    run_mode = str(cfg.get("run_mode", "mpc_sliding")).strip().lower()
    if run_mode == "simulate":
        return run_simulation_only(cfg)
    if run_mode == "identify":
        return run_identify(cfg)
    if run_mode in {"mpc_frozen", "frozen"}:
        return run_frozen(cfg)
    rng = np.random.default_rng(int(cfg["seed"]))
    dt = float(cfg["dt_control"]); total = max(2, int(round(float(cfg.get("reference_duration_sec", cfg["duration_sec"]))/dt))+1)
    excitation, effective_window_sec = effective_window_samples(cfg)
    if excitation > total - 2:
        raise ValueError("The selected data/reference duration must exceed the effective window length")
    d, ym = make_reference(total, excitation, cfg, rng)
    model_path = Path(cfg.get("identified_model_file", ""))
    if not model_path.exists():
        raise FileNotFoundError("Sliding MPC requires an identified HONU model")
    true_local, _, _, _ = load_identified_local(model_path)
    t = np.arange(total)*dt; y = np.zeros(total); u = np.zeros(total)
    _tm, _um, ym_data = load_measured_dataset(cfg.get("data_file", "data_uy.txt"))
    y[0] = float(ym_data[0])
    pred = np.full(total, np.nan); obj = np.full(total, np.nan); ok = np.zeros(total)
    if str(cfg.get("honu", "LNU")).upper() == "MLP":
        hidden = _parse_mlp_hidden_layers(cfg)
        layer_sizes = _mlp_layer_sizes(int(cfg["n_y"] + cfg["n_u"]), hidden, 1)
        raw_feature_count = sum(a*b + b for a, b in zip(layer_sizes[:-1], layer_sizes[1:]))
    else:
        raw_feature_count = qnu_feature_count(1 + cfg["n_y"] + cfg["n_u"]) if cfg["honu"] == "QNU" else 1 + cfg["n_y"] + cfg["n_u"]
    # Maximum storage width; actual QNU width depends on selected PCA components.
    w_trace = np.full((total, raw_feature_count), np.nan); rho_aw = np.full(total, np.nan); rho_ay = np.full(total, np.nan)
    # Wall-clock computation times measured independently in every active MPC step.
    # The first identification sample also includes construction of the frozen PCA basis.
    identification_time_sec = np.full(total, np.nan)
    control_time_sec = np.full(total, np.nan)
    blocks = int(np.ceil(excitation/max(1, int(round(float(cfg["excitation_hold_sec"])/dt)))))
    # The initial identification phase uses the u_min/u_max range selected in
    # the GUI. After this phase, the MPC control action remains unrestricted.
    u_min = float(cfg["u_min"]); u_max = float(cfg["u_max"])
    if not u_min < u_max:
        raise ValueError("u_min must be smaller than u_max")
    excitation_mode = selected_step_mode(cfg, "u_excitation_mode")
    if excitation_mode == "alternating_steps":
        exvals = np.where(np.arange(blocks) % 2 == 0, u_max, u_min).astype(float)
    elif excitation_mode == "random_steps":
        exvals = rng.uniform(u_min, u_max, size=blocks)
    else:
        raise ValueError(f"Unsupported excitation_mode: {excitation_mode}")
    warm = None; local = None; pca = None; eh = max(1, int(round(float(cfg["excitation_hold_sec"])/dt)))
    for k in range(total-1):
        if k < excitation:
            u[k] = exvals[min(k//eh, blocks-1)]
        else:
            ws = max(0, k+1-excitation)
            if k+1-ws >= max(cfg["n_y"], input_delay_samples(cfg) + cfg["n_u"])+3:
                identification_start_ns = perf_counter_ns()
                if pca is None and str(cfg.get("honu", "LNU")).upper() != "MLP":
                    # One frozen basis from the completed initial excitation phase.
                    # Its one-off construction is included in the first identification time.
                    pca = initialise_fixed_pca(y[:k+1], u[:k], cfg)
                local, theta, _rho_aw_unused, rho_ay[k] = fit_model(y[ws:k+1], u[ws:k], cfg, pca)
                if pca is None:
                    pca = local["pca"]
                identification_time_sec[k] = (perf_counter_ns() - identification_start_ns) * 1e-9
                w_trace[k, :len(theta)] = theta
                h = min(int(cfg["horizon"]), total-k-1)
                control_start_ns = perf_counter_ns()
                seq, success, value = optimize_u(ym[k+1:k+1+h], y[:k+1], u[:k], local, None if warm is None else warm[:h], cfg)
                control_time_sec[k] = (perf_counter_ns() - control_start_ns) * 1e-9
                u[k] = seq[0]; warm = seq; ok[k] = success; obj[k] = value
                pred[k+1] = predict_sequence(seq[:1], y[:k+1], u[:k], local)[0]
                rho_ay[k] = exact_local_output_spectral_radius(current_base_from_hist(y[:k+1], u[:k], local), local)
            else: u[k] = u[k-1] if k else 0.0
        y[k+1] = honu_plant_step(y[:k+1], u[:k+1], true_local)
    u[-1] = u[-2]; e = ym-y
    if pca is None:
        raise RuntimeError("PCA basis was not initialised")
    return dict(
        t=t, d=d, ym=ym, y=y, u=u, e=e, pred=pred, objective=obj,
        optimizer_ok=ok, w=w_trace, rho_aw=rho_aw, rho_ay=rho_ay,
        excitation_index=np.asarray([excitation]),
        window_samples_effective=np.asarray([excitation], dtype=int),
        window_length_sec_requested=np.asarray([float(cfg.get("window_length_sec", excitation*dt))], dtype=float),
        window_length_sec_effective=np.asarray([effective_window_sec], dtype=float),
        pca_rank=np.asarray([pca["rank"]], dtype=int),
        pca_rank_tolerance=np.asarray([pca["rank_tolerance"]], dtype=float),
        pca_selection_mode=np.asarray([pca["selection_mode"]]),
        pca_selected_components=np.asarray([pca["selected_components"]], dtype=int),
        pca_target_variability=np.asarray([pca["target_variability"]], dtype=float),
        pca_retained_variability=np.asarray([pca["retained_variability"]], dtype=float),
        pca_raw_feature_count=np.asarray([pca["raw_feature_count"]], dtype=int),
        model_feature_count=np.asarray([pca["model_feature_count"]], dtype=int),
        pca_singular_values=np.asarray(pca["singular_values"], dtype=float),
        pca_projection=np.asarray(pca["P"], dtype=float),
        pca_mean_for_basis=np.asarray(pca["mean_for_basis"], dtype=float),
        identification_time_sec=identification_time_sec,
        control_time_sec=control_time_sec,
        run_mode=np.asarray(["mpc_sliding"]), mpc_model_mode=np.asarray(["sliding_retraining"]),
        preg_blackbox_enabled=np.asarray([bool(cfg.get("preg_blackbox_enabled", False))]),
        r_preg=np.asarray([float(cfg.get("r_preg", 1.0))]),
        plant_learning=np.asarray([str(cfg.get("plant_learning", "ridge"))]),
        identification_config_json=np.asarray([identification_config_json(cfg)]),
        honu_source=np.asarray(["fresh_sliding_retraining"]),
        config_data_source=np.asarray([str(cfg.get("data_source", "measured"))]),
        config_honu=np.asarray([str(cfg["honu"])]),
        config_n_y=np.asarray([int(cfg["n_y"])], dtype=int),
        config_n_u=np.asarray([int(cfg["n_u"])], dtype=int),
        config_dt_control=np.asarray([float(cfg["dt_control"])], dtype=float),
        config_horizon=np.asarray([int(cfg["horizon"])], dtype=int),
    )



def print_timing_summary(result, dt_mpc):
    """Print compact wall-clock statistics for measured active MPC steps."""
    ident = np.asarray(result.get("identification_time_sec", []), dtype=float)
    control = np.asarray(result.get("control_time_sec", []), dtype=float)
    mask = np.isfinite(ident) & np.isfinite(control)
    if not np.any(mask):
        return

    def stats_line(name, values):
        values = np.asarray(values, dtype=float)
        return (
            f"{name}: n={values.size}, mean={1e3*np.mean(values):.6f} ms, "
            f"std={1e3*np.std(values):.6f} ms, min={1e3*np.min(values):.6f} ms, "
            f"max={1e3*np.max(values):.6f} ms"
        )

    ident = ident[mask]
    control = control[mask]
    total = ident + control
    print("Timing:")
    print(stats_line("HONU identification", ident))
    print(stats_line("MPC control action", control))
    print(stats_line("Identification + control", total))
    if dt_mpc > 0.0:
        deadline_misses = int(np.count_nonzero(total > dt_mpc))
        print(
            f"Relative to dt MPC={dt_mpc:.9g} s: mean total={100.0*np.mean(total)/dt_mpc:.6f} %, "
            f"max total={100.0*np.max(total)/dt_mpc:.6f} %, "
            f"deadline misses={deadline_misses}/{total.size}"
        )



def print_algorithm_parameter_summary(cfg, result):
    """Print concise identification and control parameters after an MPC run."""
    selected = int(np.asarray(result.get("pca_selected_components", [0])).ravel()[0])
    model_features = int(np.asarray(result.get("model_feature_count", [selected + 1])).ravel()[0])
    raw = int(np.asarray(result.get("pca_raw_feature_count", [0])).ravel()[0])
    retained = float(np.asarray(result.get("pca_retained_variability", [np.nan])).ravel()[0])
    numerical_rank = int(np.asarray(result.get("pca_rank", [0])).ravel()[0])

    print("Identification:")
    print(
        f"HONU={cfg['honu']}; n_y={int(cfg['n_y'])}; n_u={int(cfg['n_u'])}; "
        f"dt_MPC={float(cfg['dt_control']):.9g} s; training_length={float(np.asarray(result.get('window_length_sec_effective', [cfg.get('window_length_sec', 0.0)])).ravel()[0]):.9g} s; "
        f"window_samples={int(np.asarray(result.get('window_samples_effective', [0])).ravel()[0])}"
    )
    learning = str(cfg.get('plant_learning', 'ridge')).strip().lower()
    is_mlp = str(cfg.get('honu', '')).strip().upper() == "MLP"
    if is_mlp:
        optimizer = str(cfg.get('mlp_optimizer', learning)).strip().lower()
        optimizer_name = {
            "adam": "Adam",
            "lbfgs": "L-BFGS",
            "adam_lbfgs": "Adam + L-BFGS",
        }.get(optimizer, optimizer)
        learning_details = (
            f"optimizer={optimizer_name}; epochs/iterations={int(cfg.get('mlp_epochs', cfg.get('lm_epochs', 20)))}; "
            f"L2={float(cfg.get('lambda', 0.0)):.9g}"
        )
    elif learning == "lm":
        learning_details = (
            f"learning=lm; lambda_0={float(cfg.get('lambda', cfg.get('ridge', 0.1))):.9g}; "
            f"epochs={int(cfg.get('lm_epochs', cfg.get('lm_iterations', 20)))}"
        )
    else:
        learning_details = f"learning=ridge; ridge_lambda={float(cfg.get('lambda', cfg.get('ridge', 0.1))):.9g}"
    print(
        f"{learning_details}; PCA_mode={cfg.get('pca_selection_mode', 'rank')}; "
        f"PCA_target={100.0*float(cfg.get('pca_retained_variability', 1.0)):.9g} %; "
        f"PCA_components={selected}"
    )
    print(f"PCA_rank={numerical_rank}")
    print(
        f"PCA_components={selected}; HONU_features={model_features}; "
        f"PCA_retained={100.0*retained:.9g} %"
    )
    if not is_mlp:
        print(
            f"mu_bibs={float(cfg.get('mu_bibs', 0.0)):.9g}; eps_bibs={float(cfg.get('eps_bibs', 0.0)):.9g}"
        )

    print(
        f"plant=trained HONU; data_source={cfg.get('data_source', 'measured')}"
    )

    print("Control:")
    print(
        f"Np={int(cfg['horizon'])}; opt_iter={int(cfg['opt_iter'])}; seed={int(cfg['seed'])}"
    )
    print(
        f"Q={float(cfg['q_track']):.9g}; R_du={float(cfg['r_du']):.9g}; "
        f"R_ddu={float(cfg['r_ddu']):.9g}; R_u={float(cfg['r_u']):.9g}"
    )
    print(
        f"tau1={float(cfg['tau1']):.9g} s; tau2={float(cfg['tau2']):.9g} s; "
        f"d_min={float(cfg['d_min']):.9g}; d_max={float(cfg['d_max']):.9g}; "
        f"d_step_width={float(cfg['hold_sec']):.9g} s; tau_d={float(cfg.get('tau_d', 0.0)):.9g} s"
    )
    print(
        f"u_mode={selected_step_mode(cfg, 'u_excitation_mode')}; "
        f"d_mode={selected_step_mode(cfg, 'd_reference_mode')}; "
        f"u_step_width={float(cfg['excitation_hold_sec']):.9g} s; tau_u={float(cfg.get('tau_u', 0.0)):.9g} s"
    )

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("config"); ap.add_argument("output"); a=ap.parse_args()
    cfg=json.loads(Path(a.config).read_text(encoding="utf-8")); result=dict(run(cfg))
    # Store the exact configuration inside every result, including the plain
    # ODE simulation. The GUI can then redraw titles after widget changes
    # without ever substituting values from a later, unexecuted setup.
    result["run_config_json"] = np.asarray([
        json.dumps(cfg, sort_keys=True, separators=(",", ":"))
    ])
    np.savez(a.output, **result)
    mode=str(cfg.get("run_mode", "mpc")).strip().lower()
    label = 'measured data' if mode == 'simulate' else ('HONU Plant identification' if mode == 'identify' else ('frozen-HONU MPC' if mode in {'mpc_frozen','frozen'} else 'sliding-retraining MPC'))
    print(f"Saved {label} result: {Path(a.output).resolve()}")
    if mode != "simulate":
        print_timing_summary(result, float(cfg["dt_control"]))
        print_algorithm_parameter_summary(cfg, result)

if __name__ == "__main__": main()
