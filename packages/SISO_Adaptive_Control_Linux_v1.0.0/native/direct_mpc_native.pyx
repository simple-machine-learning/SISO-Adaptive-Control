# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True
import numpy as np
cimport numpy as cnp


def _qnu_features_and_jacobian(cnp.ndarray[cnp.double_t, ndim=1] z):
    cdef Py_ssize_t n=z.shape[0], i, j, k=0
    cdef Py_ssize_t m=n*(n+1)//2
    cdef cnp.ndarray[cnp.double_t, ndim=1] feat=np.empty(m,dtype=np.float64)
    cdef cnp.ndarray[cnp.double_t, ndim=2] jac=np.zeros((m,n),dtype=np.float64)
    for i in range(n):
        for j in range(i,n):
            feat[k]=z[i]*z[j]
            jac[k,i]+=z[j]
            jac[k,j]+=z[i]
            k+=1
    return feat,jac


def predict_honu_direct(candidate_u,y_hist,u_hist,W,P,int ny,int nu,int delay_u,int model_qnu,
                        bint delta_target,bint compute_jacobian=True):
    cdef cnp.ndarray[cnp.double_t, ndim=1] U=np.ascontiguousarray(candidate_u,dtype=np.float64).reshape(-1)
    cdef cnp.ndarray[cnp.double_t, ndim=1] y=np.ascontiguousarray(y_hist,dtype=np.float64).reshape(-1)
    cdef cnp.ndarray[cnp.double_t, ndim=1] u=np.ascontiguousarray(u_hist,dtype=np.float64).reshape(-1)
    cdef cnp.ndarray[cnp.double_t, ndim=2] WW=np.ascontiguousarray(W,dtype=np.float64)
    cdef cnp.ndarray[cnp.double_t, ndim=2] PP=np.ascontiguousarray(P,dtype=np.float64)
    cdef Py_ssize_t H=WW.shape[1], i, idx
    cdef cnp.ndarray[cnp.double_t, ndim=1] U2=np.empty(H,dtype=np.float64)
    if U.shape[0]==0:
        U2[:]=0.0
    else:
        for i in range(H): U2[i]=U[i] if i<U.shape[0] else U[U.shape[0]-1]
    cdef cnp.ndarray[cnp.double_t, ndim=1] base=np.zeros(ny+nu+H,dtype=np.float64)
    for i in range(ny):
        if y.shape[0]>i: base[i]=y[y.shape[0]-1-i]
    for i in range(nu):
        idx=u.shape[0]-1-delay_u-i
        if idx>=0: base[ny+i]=u[idx]
    base[ny+nu:]=U2
    z=PP.T.dot(base)
    za=np.concatenate((np.ones(1,dtype=np.float64),z))
    if model_qnu:
        feat,Jq=_qnu_features_and_jacobian(np.ascontiguousarray(za,dtype=np.float64))
        out=feat.dot(WW)
        if compute_jacobian:
            grad_z=WW.T.dot(Jq)[:,1:]
            grad_base=PP.dot(grad_z.T)
    else:
        out=za.dot(WW)
        if compute_jacobian: grad_base=PP.dot(WW[1:,:])
    if delta_target:
        out=np.asarray(out,dtype=np.float64)+base[0]
        if compute_jacobian:
            grad_base=np.asarray(grad_base,dtype=np.float64)
            grad_base[0,:]+=1.0
    if not compute_jacobian: return np.asarray(out,dtype=np.float64),None
    return np.asarray(out,dtype=np.float64),np.asarray(grad_base[-H:,:].T,dtype=np.float64)


def _activation(x):
    return np.tanh(x)

def _activation_derivative_from_output(a):
    return 1.0-a*a

def predict_mlp_direct(candidate_u,y_hist,u_hist,theta,layer_sizes,history_mean,history_std,P,
                       future_mean,future_std,int ny,int nu,int delay_u,int history_dim,
                       double target_scale,bint delta_target,bint compute_jacobian=True):
    U=np.ascontiguousarray(candidate_u,dtype=np.float64).reshape(-1)
    y=np.ascontiguousarray(y_hist,dtype=np.float64).reshape(-1)
    u=np.ascontiguousarray(u_hist,dtype=np.float64).reshape(-1)
    sizes=np.asarray(layer_sizes,dtype=np.int64).reshape(-1)
    H=int(sizes[sizes.size-1])
    U2=np.empty(H,dtype=np.float64)
    if U.size==0: U2[:]=0.0
    else:
        for i in range(H): U2[i]=U[i] if i<U.size else U[U.size-1]
    base=np.zeros(ny+nu+H,dtype=np.float64)
    for i in range(ny):
        if y.size>i: base[i]=y[y.size-1-i]
    for i in range(nu):
        idx=u.size-1-delay_u-i
        if idx>=0: base[ny+i]=u[idx]
    base[ny+nu:]=U2
    hm=np.asarray(history_mean,dtype=np.float64); hs=np.asarray(history_std,dtype=np.float64)
    fm=np.asarray(future_mean,dtype=np.float64); fs=np.asarray(future_std,dtype=np.float64)
    PP=np.asarray(P,dtype=np.float64)
    hist=(base[:history_dim]-hm)/hs
    x=np.concatenate((hist.dot(PP),(base[history_dim:]-fm)/fs))
    acts=[x]; weights=[]; pos=0
    th=np.asarray(theta,dtype=np.float64).reshape(-1)
    for li in range(sizes.size-1):
        nin=int(sizes[li]); nout=int(sizes[li+1]); count=nout*nin
        W=th[pos:pos+count].reshape(nout,nin); pos+=count
        b=th[pos:pos+nout]; pos+=nout
        z=W.dot(acts[len(acts)-1])+b
        a=z if li==sizes.size-2 else _activation(z)
        weights.append(W); acts.append(a)
    out_n=np.asarray(acts[len(acts)-1],dtype=np.float64)
    out=target_scale*out_n
    if delta_target: out=out+base[0]
    if not compute_jacobian: return out,None
    J=np.eye(H,dtype=np.float64)
    for li in range(len(weights)-1,-1,-1):
        J=J.dot(weights[li])
        if li>0: J=J*_activation_derivative_from_output(acts[li])[None,:]
    raw_j=np.zeros((x.size,base.size),dtype=np.float64)
    raw_j[:PP.shape[1],:history_dim]=PP.T/hs[None,:]
    for i in range(base.size-history_dim): raw_j[PP.shape[1]+i,history_dim+i]=1.0/fs[i]
    Jbase=target_scale*J.dot(raw_j)
    if delta_target: Jbase[:,0]+=1.0
    return np.asarray(out,dtype=np.float64),np.asarray(Jbase[:,-H:],dtype=np.float64)
