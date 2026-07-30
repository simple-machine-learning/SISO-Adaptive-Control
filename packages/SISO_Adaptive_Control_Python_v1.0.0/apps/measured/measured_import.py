# -*- coding: utf-8 -*-
"""Import measured t,u,y data into the Simulated-compatible workflow files."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np


def _load(path: Path):
    suffix = path.suffix.lower()
    if suffix == '.npz':
        z = np.load(path, allow_pickle=False)
        keys = {k.lower(): k for k in z.files}
        if all(k in keys for k in ('t','u','y')):
            return np.asarray(z[keys['t']],float), np.asarray(z[keys['u']],float), np.asarray(z[keys['y']],float)
        raise ValueError('NPZ must contain arrays t, u and y.')
    if suffix == '.npy':
        a = np.asarray(np.load(path, allow_pickle=False), float)
    else:
        delimiter = ',' if suffix == '.csv' else None
        try:
            a = np.loadtxt(path, comments='#', delimiter=delimiter, ndmin=2)
        except Exception:
            a = np.genfromtxt(path, comments='#', delimiter=delimiter, names=True, dtype=float)
            if getattr(a, 'dtype', None) is not None and a.dtype.names:
                names = {n.lower(): n for n in a.dtype.names}
                if all(k in names for k in ('t','u','y')):
                    return np.asarray(a[names['t']],float), np.asarray(a[names['u']],float), np.asarray(a[names['y']],float)
            raise
    if a.ndim != 2 or a.shape[1] < 3:
        raise ValueError('Measured table must have at least three columns: t, u, y.')
    return a[:,0], a[:,1], a[:,2]


def import_measured_file(source, base_dir, dt=None):
    source = Path(source)
    base_dir = Path(base_dir)
    data_dir = base_dir / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    t,u,y = _load(source)
    mask = np.isfinite(t) & np.isfinite(u) & np.isfinite(y)
    t,u,y = t[mask],u[mask],y[mask]
    if len(t) < 3:
        raise ValueError('At least three finite measured samples are required.')
    order = np.argsort(t)
    t,u,y = t[order],u[order],y[order]
    keep = np.r_[True, np.diff(t) > 0]
    t,u,y = t[keep],u[keep],y[keep]
    raw_dt = float(np.median(np.diff(t)))
    target_dt = float(dt) if dt is not None and float(dt) > 0 else raw_dt
    if target_dt < raw_dt * (1-1e-9):
        raise ValueError(f'dt={target_dt:g} s is smaller than measured sampling {raw_dt:g} s.')
    if not np.isclose(target_dt, raw_dt, rtol=1e-6, atol=1e-12):
        tq = np.arange(t[0], t[-1] + 0.5*target_dt, target_dt)
        idx = np.searchsorted(t, tq, side='left')
        idx = np.clip(idx, 0, len(t)-1)
        left = np.clip(idx-1, 0, len(t)-1)
        idx = np.where(np.abs(tq-t[left]) <= np.abs(t[idx]-tq), left, idx)
        t,u,y = tq,t[idx],y[idx]
    out = np.column_stack([t,u,y])
    header = 't u y\nsource=measured; source_file=' + str(source.resolve()) + f'; dt={target_dt:.17g}'
    np.savetxt(base_dir/'data_uy.txt', out, header=header)
    mu_u, sig_u = float(np.mean(u)), max(float(np.std(u)), 1e-12)
    mu_y, sig_y = float(np.mean(y)), max(float(np.std(y)), 1e-12)
    un=(u-mu_u)/sig_u; yn=(y-mu_y)/sig_y
    np.savetxt(data_dir/'data_uy_normalized.txt', np.column_stack([t,un,yn]), header='t u_z y_z')
    np.savez(data_dir/'simulated_normalization.npz', mu_u=mu_u, sigma_u=sig_u, scale_u=sig_u, mu_y=mu_y, sigma_y=sig_y, scale_y=sig_y, std_multiplier=1.0, model_name='measured', dt=target_dt, source_file=str(source.resolve()))
    meta={'source':'measured','source_file':str(source.resolve()),'samples':int(len(t)),'dt_raw':raw_dt,'dt':target_dt,'t_start':float(t[0]),'t_stop':float(t[-1])}
    (data_dir/'data_uy.txt.runmeta.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    return meta


def import_selected_arrays(t, u, y, source, base_dir, dt, metadata=None):
    source = Path(source)
    base_dir = Path(base_dir)
    data_dir = base_dir / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    t = np.asarray(t, dtype=float).ravel()
    u = np.asarray(u, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    mask = np.isfinite(t) & np.isfinite(u) & np.isfinite(y)
    t, u, y = t[mask], u[mask], y[mask]
    if len(t) < 3:
        raise ValueError('At least three finite selected samples are required.')
    if not np.all(np.diff(t) > 0):
        raise ValueError('Selected time values must be strictly increasing.')
    raw_dt = float(np.median(np.diff(t)))
    target_dt = float(dt)
    if not np.isfinite(target_dt) or target_dt <= 0:
        raise ValueError('dt must be positive and finite.')
    if target_dt < raw_dt * (1 - 1e-9):
        raise ValueError(f'dt={target_dt:g} s is smaller than measured sampling {raw_dt:g} s.')
    if not np.isclose(target_dt, raw_dt, rtol=1e-6, atol=1e-12):
        tq = np.arange(t[0], t[-1] + 0.5 * target_dt, target_dt)
        idx = np.searchsorted(t, tq, side='left')
        idx = np.clip(idx, 0, len(t)-1)
        left = np.clip(idx-1, 0, len(t)-1)
        idx = np.where(np.abs(tq-t[left]) <= np.abs(t[idx]-tq), left, idx)
        t, u, y = tq, u[idx], y[idx]
    out = np.column_stack([t, u, y])
    extra = dict(metadata or {})
    header = 't u y\nsource=measured; source_file=' + str(source.resolve()) + f'; dt={target_dt:.17g}'
    np.savetxt(base_dir/'data_uy.txt', out, header=header)
    mu_u, sig_u = float(np.mean(u)), max(float(np.std(u)), 1e-12)
    mu_y, sig_y = float(np.mean(y)), max(float(np.std(y)), 1e-12)
    un=(u-mu_u)/sig_u; yn=(y-mu_y)/sig_y
    np.savetxt(data_dir/'data_uy_normalized.txt', np.column_stack([t,un,yn]), header='t u_z y_z')
    np.savez(data_dir/'simulated_normalization.npz', mu_u=mu_u, sigma_u=sig_u, scale_u=sig_u, mu_y=mu_y, sigma_y=sig_y, scale_y=sig_y, std_multiplier=1.0, model_name='measured', dt=target_dt, source_file=str(source.resolve()))
    meta={'source':'measured','source_file':str(source.resolve()),'samples':int(len(t)),'dt_raw':raw_dt,'dt':target_dt,'t_start':float(t[0]),'t_stop':float(t[-1]), **extra}
    (data_dir/'data_uy.txt.runmeta.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    return meta
