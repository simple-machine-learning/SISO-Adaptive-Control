#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <numpy/arrayobject.h>

#include <algorithm>
#include <cmath>
#include <cstring>
#include <vector>
#include <limits>

namespace {

PyArrayObject* as_double_1d(PyObject* obj) {
    return reinterpret_cast<PyArrayObject*>(PyArray_FROM_OTF(obj, NPY_DOUBLE, NPY_ARRAY_IN_ARRAY));
}

PyArrayObject* as_double_2d(PyObject* obj) {
    PyArrayObject* arr = reinterpret_cast<PyArrayObject*>(
        PyArray_FROM_OTF(obj, NPY_DOUBLE, NPY_ARRAY_IN_ARRAY));
    if (arr && PyArray_NDIM(arr) != 2) {
        PyErr_SetString(PyExc_ValueError, "P must be a 2-D float64 array");
        Py_DECREF(arr);
        return nullptr;
    }
    return arr;
}

inline double dot(const double* a, const double* b, npy_intp n) {
    double s = 0.0;
    for (npy_intp i = 0; i < n; ++i) s += a[i] * b[i];
    return s;
}

void model_output_gradient(
    const std::vector<double>& base,
    const double* P,
    npy_intp base_dim,
    npy_intp components,
    const double* theta,
    npy_intp theta_len,
    bool qnu,
    double& output,
    std::vector<double>& grad_base)
{
    std::vector<double> z(static_cast<size_t>(components), 0.0);
    for (npy_intp j = 0; j < components; ++j) {
        double s = 0.0;
        for (npy_intp i = 0; i < base_dim; ++i) s += P[i * components + j] * base[static_cast<size_t>(i)];
        z[static_cast<size_t>(j)] = s;
    }

    std::vector<double> za(static_cast<size_t>(components + 1), 1.0);
    for (npy_intp j = 0; j < components; ++j) za[static_cast<size_t>(j + 1)] = z[static_cast<size_t>(j)];
    std::vector<double> grad_za(static_cast<size_t>(components + 1), 0.0);

    if (!qnu) {
        output = dot(theta, za.data(), components + 1);
        for (npy_intp j = 1; j < components + 1; ++j) grad_za[static_cast<size_t>(j)] = theta[j];
    } else {
        const npy_intp n = components + 1;
        output = 0.0;
        npy_intp k = 0;
        for (npy_intp i = 0; i < n; ++i) {
            for (npy_intp j = i; j < n; ++j, ++k) {
                const double t = theta[k];
                output += t * za[static_cast<size_t>(i)] * za[static_cast<size_t>(j)];
                grad_za[static_cast<size_t>(i)] += t * za[static_cast<size_t>(j)];
                grad_za[static_cast<size_t>(j)] += t * za[static_cast<size_t>(i)];
            }
        }
    }

    grad_base.assign(static_cast<size_t>(base_dim), 0.0);
    for (npy_intp i = 0; i < base_dim; ++i) {
        double s = 0.0;
        for (npy_intp j = 0; j < components; ++j) s += P[i * components + j] * grad_za[static_cast<size_t>(j + 1)];
        grad_base[static_cast<size_t>(i)] = s;
    }
}

PyObject* predict_sequence_and_jacobian(PyObject*, PyObject* args, PyObject* kwargs) {
    PyObject *candidate_obj, *y_obj, *u_obj, *theta_obj, *P_obj;
    int ny, nu, delay_u, qnu, compute_jacobian = 1;
    static const char* names[] = {
        "candidate_u", "y_hist", "u_hist", "theta", "P", "ny", "nu", "delay_u", "qnu", "compute_jacobian", nullptr
    };
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OOOOOiiii|p", const_cast<char**>(names),
                                     &candidate_obj, &y_obj, &u_obj, &theta_obj, &P_obj,
                                     &ny, &nu, &delay_u, &qnu, &compute_jacobian)) return nullptr;

    PyArrayObject* candidate = as_double_1d(candidate_obj);
    PyArrayObject* y_hist = as_double_1d(y_obj);
    PyArrayObject* u_hist = as_double_1d(u_obj);
    PyArrayObject* theta = as_double_1d(theta_obj);
    PyArrayObject* P_arr = as_double_2d(P_obj);
    if (!candidate || !y_hist || !u_hist || !theta || !P_arr) {
        Py_XDECREF(candidate); Py_XDECREF(y_hist); Py_XDECREF(u_hist); Py_XDECREF(theta); Py_XDECREF(P_arr);
        return nullptr;
    }

    const npy_intp horizon = PyArray_SIZE(candidate);
    const npy_intp y_n = PyArray_SIZE(y_hist);
    const npy_intp u_n = PyArray_SIZE(u_hist);
    const npy_intp theta_n = PyArray_SIZE(theta);
    const npy_intp base_dim = PyArray_DIM(P_arr, 0);
    const npy_intp components = PyArray_DIM(P_arr, 1);
    const npy_intp expected_theta = qnu ? (components + 1) * (components + 2) / 2 : components + 1;
    if (theta_n != expected_theta) {
        PyErr_SetString(PyExc_ValueError, "Coefficient count does not match LNU/QNU model dimensions");
        Py_DECREF(candidate); Py_DECREF(y_hist); Py_DECREF(u_hist); Py_DECREF(theta); Py_DECREF(P_arr);
        return nullptr;
    }
    if (base_dim != ny + nu || ny < 1 || nu < 0 || delay_u < 0) {
        PyErr_SetString(PyExc_ValueError, "Inconsistent ny, nu, delay_u or P dimensions");
        Py_DECREF(candidate); Py_DECREF(y_hist); Py_DECREF(u_hist); Py_DECREF(theta); Py_DECREF(P_arr);
        return nullptr;
    }

    const double* candidate_p = static_cast<const double*>(PyArray_DATA(candidate));
    const double* y_p = static_cast<const double*>(PyArray_DATA(y_hist));
    const double* u_p = static_cast<const double*>(PyArray_DATA(u_hist));
    const double* theta_p = static_cast<const double*>(PyArray_DATA(theta));
    const double* P = static_cast<const double*>(PyArray_DATA(P_arr));

    npy_intp out_dims[1] = {horizon};
    PyArrayObject* out = reinterpret_cast<PyArrayObject*>(PyArray_SimpleNew(1, out_dims, NPY_DOUBLE));
    PyArrayObject* jac = nullptr;
    if (compute_jacobian) {
        npy_intp jac_dims[2] = {horizon, horizon};
        jac = reinterpret_cast<PyArrayObject*>(PyArray_ZEROS(2, jac_dims, NPY_DOUBLE, 0));
    }
    if (!out || (compute_jacobian && !jac)) {
        Py_XDECREF(out); Py_XDECREF(jac);
        Py_DECREF(candidate); Py_DECREF(y_hist); Py_DECREF(u_hist); Py_DECREF(theta); Py_DECREF(P_arr);
        return PyErr_NoMemory();
    }

    std::vector<double> y_seq;
    const npy_intp y_start = std::max<npy_intp>(0, y_n - ny);
    y_seq.assign(y_p + y_start, y_p + y_n);
    std::vector<double> u_seq;
    const npy_intp u_keep = delay_u + nu;
    const npy_intp u_start = std::max<npy_intp>(0, u_n - u_keep);
    if (u_keep > 0) u_seq.assign(u_p + u_start, u_p + u_n);

    std::vector<std::vector<double>> y_grad_seq(y_seq.size(), std::vector<double>(static_cast<size_t>(horizon), 0.0));
    std::vector<std::vector<double>> u_grad_seq(u_seq.size(), std::vector<double>(static_cast<size_t>(horizon), 0.0));
    std::vector<double> base(static_cast<size_t>(base_dim), 0.0), grad_base;
    std::vector<double> base_grad(static_cast<size_t>(base_dim * horizon), 0.0);
    std::vector<double> next_grad(static_cast<size_t>(horizon), 0.0);
    double* out_p = static_cast<double*>(PyArray_DATA(out));
    double* jac_p = jac ? static_cast<double*>(PyArray_DATA(jac)) : nullptr;

    try {
        Py_BEGIN_ALLOW_THREADS
        for (npy_intp h = 0; h < horizon; ++h) {
            u_seq.push_back(candidate_p[h]);
            if (compute_jacobian) {
                std::vector<double> gu(static_cast<size_t>(horizon), 0.0);
                gu[static_cast<size_t>(h)] = 1.0;
                u_grad_seq.push_back(std::move(gu));
            }

            std::fill(base.begin(), base.end(), 0.0);
            for (int i = 0; i < ny; ++i) {
                if (static_cast<size_t>(i) < y_seq.size()) base[static_cast<size_t>(i)] = y_seq[y_seq.size() - 1 - static_cast<size_t>(i)];
            }
            for (int i = 0; i < nu; ++i) {
                const long idx = static_cast<long>(u_seq.size()) - 1L - delay_u - i;
                if (idx >= 0) base[static_cast<size_t>(ny + i)] = u_seq[static_cast<size_t>(idx)];
            }

            double y_next = 0.0;
            model_output_gradient(base, P, base_dim, components, theta_p, theta_n, qnu != 0, y_next, grad_base);
            out_p[h] = y_next;

            if (compute_jacobian) {
                std::fill(base_grad.begin(), base_grad.end(), 0.0);
                for (int i = 0; i < ny; ++i) {
                    if (static_cast<size_t>(i) < y_grad_seq.size()) {
                        const auto& src = y_grad_seq[y_grad_seq.size() - 1 - static_cast<size_t>(i)];
                        std::copy(src.begin(), src.end(), base_grad.begin() + static_cast<size_t>(i) * horizon);
                    }
                }
                for (int i = 0; i < nu; ++i) {
                    const long idx = static_cast<long>(u_grad_seq.size()) - 1L - delay_u - i;
                    if (idx >= 0) {
                        const auto& src = u_grad_seq[static_cast<size_t>(idx)];
                        std::copy(src.begin(), src.end(), base_grad.begin() + static_cast<size_t>(ny + i) * horizon);
                    }
                }
                std::fill(next_grad.begin(), next_grad.end(), 0.0);
                for (npy_intp r = 0; r < base_dim; ++r) {
                    const double g = grad_base[static_cast<size_t>(r)];
                    const double* row = base_grad.data() + r * horizon;
                    for (npy_intp c = 0; c < horizon; ++c) next_grad[static_cast<size_t>(c)] += g * row[c];
                }
                std::copy(next_grad.begin(), next_grad.end(), jac_p + h * horizon);
                y_grad_seq.push_back(next_grad);
            }
            y_seq.push_back(y_next);
        }
        Py_END_ALLOW_THREADS
    } catch (const std::exception& e) {
        PyErr_SetString(PyExc_RuntimeError, e.what());
        Py_DECREF(out); Py_XDECREF(jac);
        Py_DECREF(candidate); Py_DECREF(y_hist); Py_DECREF(u_hist); Py_DECREF(theta); Py_DECREF(P_arr);
        return nullptr;
    }

    Py_DECREF(candidate); Py_DECREF(y_hist); Py_DECREF(u_hist); Py_DECREF(theta); Py_DECREF(P_arr);
    PyObject* jac_obj = compute_jacobian ? reinterpret_cast<PyObject*>(jac) : Py_None;
    if (!compute_jacobian) Py_INCREF(Py_None);
    PyObject* result = PyTuple_Pack(2, reinterpret_cast<PyObject*>(out), jac_obj);
    Py_DECREF(out); Py_DECREF(jac_obj);
    return result;
}


bool solve_spd_cholesky(std::vector<double> A, std::vector<double> b, npy_intp n, std::vector<double>& x) {
    for (npy_intp i = 0; i < n; ++i) {
        for (npy_intp j = 0; j <= i; ++j) {
            double sum = A[static_cast<size_t>(i*n+j)];
            for (npy_intp k = 0; k < j; ++k) sum -= A[static_cast<size_t>(i*n+k)] * A[static_cast<size_t>(j*n+k)];
            if (i == j) {
                if (!(sum > 1e-20) || !std::isfinite(sum)) return false;
                A[static_cast<size_t>(i*n+j)] = std::sqrt(sum);
            } else {
                A[static_cast<size_t>(i*n+j)] = sum / A[static_cast<size_t>(j*n+j)];
            }
        }
    }
    std::vector<double> y(static_cast<size_t>(n), 0.0);
    for (npy_intp i = 0; i < n; ++i) {
        double sum = b[static_cast<size_t>(i)];
        for (npy_intp k = 0; k < i; ++k) sum -= A[static_cast<size_t>(i*n+k)] * y[static_cast<size_t>(k)];
        y[static_cast<size_t>(i)] = sum / A[static_cast<size_t>(i*n+i)];
    }
    x.assign(static_cast<size_t>(n), 0.0);
    for (npy_intp ii = n; ii-- > 0;) {
        double sum = y[static_cast<size_t>(ii)];
        for (npy_intp k = ii + 1; k < n; ++k) sum -= A[static_cast<size_t>(k*n+ii)] * x[static_cast<size_t>(k)];
        x[static_cast<size_t>(ii)] = sum / A[static_cast<size_t>(ii*n+ii)];
    }
    return true;
}

bool rollout_native(const double* candidate, npy_intp horizon, const double* y_p, npy_intp y_n,
                    const double* u_p, npy_intp u_n, const double* theta_p, const double* P,
                    npy_intp base_dim, npy_intp components, int ny, int nu, int delay_u, bool qnu,
                    bool with_jac, std::vector<double>& out, std::vector<double>& jac) {
    out.assign(static_cast<size_t>(horizon), 0.0);
    if (with_jac) jac.assign(static_cast<size_t>(horizon*horizon), 0.0); else jac.clear();
    std::vector<double> y_seq;
    const npy_intp y_start = std::max<npy_intp>(0, y_n - ny);
    y_seq.assign(y_p + y_start, y_p + y_n);
    std::vector<double> u_seq;
    const npy_intp u_keep = delay_u + nu;
    const npy_intp u_start = std::max<npy_intp>(0, u_n - u_keep);
    if (u_keep > 0) u_seq.assign(u_p + u_start, u_p + u_n);
    std::vector<std::vector<double>> yg(y_seq.size(), std::vector<double>(static_cast<size_t>(horizon),0.0));
    std::vector<std::vector<double>> ug(u_seq.size(), std::vector<double>(static_cast<size_t>(horizon),0.0));
    std::vector<double> base(static_cast<size_t>(base_dim),0.0), grad_base, bg(static_cast<size_t>(base_dim*horizon),0.0), ng(static_cast<size_t>(horizon),0.0);
    for (npy_intp h=0; h<horizon; ++h) {
        u_seq.push_back(candidate[h]);
        if (with_jac) { std::vector<double> g(static_cast<size_t>(horizon),0.0); g[static_cast<size_t>(h)]=1.0; ug.push_back(std::move(g)); }
        std::fill(base.begin(),base.end(),0.0);
        for(int i=0;i<ny;++i) if(static_cast<size_t>(i)<y_seq.size()) base[static_cast<size_t>(i)]=y_seq[y_seq.size()-1-static_cast<size_t>(i)];
        for(int i=0;i<nu;++i){ long idx=static_cast<long>(u_seq.size())-1L-delay_u-i; if(idx>=0) base[static_cast<size_t>(ny+i)]=u_seq[static_cast<size_t>(idx)]; }
        double yn=0.0; model_output_gradient(base,P,base_dim,components,theta_p,0,qnu,yn,grad_base);
        if(!std::isfinite(yn)) return false; out[static_cast<size_t>(h)]=yn;
        if(with_jac){
            std::fill(bg.begin(),bg.end(),0.0);
            for(int i=0;i<ny;++i) if(static_cast<size_t>(i)<yg.size()) std::copy(yg[yg.size()-1-static_cast<size_t>(i)].begin(),yg[yg.size()-1-static_cast<size_t>(i)].end(),bg.begin()+static_cast<size_t>(i)*horizon);
            for(int i=0;i<nu;++i){ long idx=static_cast<long>(ug.size())-1L-delay_u-i; if(idx>=0) std::copy(ug[static_cast<size_t>(idx)].begin(),ug[static_cast<size_t>(idx)].end(),bg.begin()+static_cast<size_t>(ny+i)*horizon); }
            std::fill(ng.begin(),ng.end(),0.0);
            for(npy_intp r=0;r<base_dim;++r){ double g=grad_base[static_cast<size_t>(r)]; const double* row=bg.data()+r*horizon; for(npy_intp c=0;c<horizon;++c) ng[static_cast<size_t>(c)]+=g*row[c]; }
            for(npy_intp c=0;c<horizon;++c){ if(!std::isfinite(ng[static_cast<size_t>(c)])) return false; jac[static_cast<size_t>(h*horizon+c)]=ng[static_cast<size_t>(c)]; }
            yg.push_back(ng);
        }
        y_seq.push_back(yn);
    }
    return true;
}

PyObject* optimize_u_native(PyObject*, PyObject* args, PyObject* kwargs) {
    PyObject *ref_obj,*y_obj,*u_obj,*theta_obj,*P_obj,*warm_obj=Py_None;
    int ny,nu,delay_u,qnu,opt_iter;
    double q,rd,rd2,ru,u_min,u_max;
    static const char* names[]={"ref","y_hist","u_hist","theta","P","ny","nu","delay_u","qnu","warm","q_track","r_du","r_ddu","r_u","u_min","u_max","opt_iter",nullptr};
    if(!PyArg_ParseTupleAndKeywords(args,kwargs,"OOOOOiiiiOddddddi",const_cast<char**>(names),&ref_obj,&y_obj,&u_obj,&theta_obj,&P_obj,&ny,&nu,&delay_u,&qnu,&warm_obj,&q,&rd,&rd2,&ru,&u_min,&u_max,&opt_iter)) return nullptr;
    PyArrayObject *ref=as_double_1d(ref_obj),*yh=as_double_1d(y_obj),*uh=as_double_1d(u_obj),*theta=as_double_1d(theta_obj),*Pa=as_double_2d(P_obj),*warm=nullptr;
    if(warm_obj!=Py_None) warm=as_double_1d(warm_obj);
    if(!ref||!yh||!uh||!theta||!Pa||(warm_obj!=Py_None&&!warm)){Py_XDECREF(ref);Py_XDECREF(yh);Py_XDECREF(uh);Py_XDECREF(theta);Py_XDECREF(Pa);Py_XDECREF(warm);return nullptr;}
    const npy_intp h=PyArray_SIZE(ref), y_n=PyArray_SIZE(yh),u_n=PyArray_SIZE(uh),base_dim=PyArray_DIM(Pa,0),components=PyArray_DIM(Pa,1);
    const double *rp=(double*)PyArray_DATA(ref),*yp=(double*)PyArray_DATA(yh),*up=(double*)PyArray_DATA(uh),*tp=(double*)PyArray_DATA(theta),*P=(double*)PyArray_DATA(Pa);
    double prev=u_n?up[u_n-1]:0.0, prev2=u_n>1?up[u_n-2]:prev;
    std::vector<double> x(static_cast<size_t>(h),prev);
    if(warm && PyArray_SIZE(warm)==h){ const double* wp=(double*)PyArray_DATA(warm); for(npy_intp i=0;i<h-1;++i)x[static_cast<size_t>(i)]=wp[i+1]; if(h)x[static_cast<size_t>(h-1)]=wp[h-1]; }
    for(double v:x) if(!std::isfinite(v)){std::fill(x.begin(),x.end(),prev);break;}
    q=std::max(0.0,q);rd=std::max(0.0,rd);rd2=std::max(0.0,rd2);ru=std::max(0.0,ru);
    const double sq_q=std::sqrt(q),sq_rd=std::sqrt(rd),sq_rd2=std::sqrt(rd2),sq_ru=std::sqrt(ru);
    auto evaluate=[&](const std::vector<double>& cand,bool with_jac,std::vector<double>& residual,std::vector<double>& J,double& value)->bool{
        std::vector<double> yout,Jy; if(!rollout_native(cand.data(),h,yp,y_n,up,u_n,tp,P,base_dim,components,ny,nu,delay_u,qnu!=0,with_jac,yout,Jy)) return false;
        residual.assign(static_cast<size_t>(4*h),0.0); if(with_jac)J.assign(static_cast<size_t>(4*h*h),0.0); else J.clear(); value=0.0;
        for(npy_intp i=0;i<h;++i){
            double du=cand[static_cast<size_t>(i)]-(i?cand[static_cast<size_t>(i-1)]:prev);
            double ddu=cand[static_cast<size_t>(i)]-2.0*(i?cand[static_cast<size_t>(i-1)]:prev)+(i>1?cand[static_cast<size_t>(i-2)]:(i==1?prev:prev2));
            double vals[4]={sq_q*(yout[static_cast<size_t>(i)]-rp[i]),sq_rd*du,sq_rd2*ddu,sq_ru*cand[static_cast<size_t>(i)]};
            for(int b=0;b<4;++b){residual[static_cast<size_t>(b*h+i)]=vals[b];value+=vals[b]*vals[b];}
            if(with_jac){
                for(npy_intp c=0;c<h;++c)J[static_cast<size_t>(i*h+c)]=sq_q*Jy[static_cast<size_t>(i*h+c)];
                J[static_cast<size_t>((h+i)*h+i)]=sq_rd; if(i>0)J[static_cast<size_t>((h+i)*h+i-1)]=-sq_rd;
                J[static_cast<size_t>((2*h+i)*h+i)]=sq_rd2; if(i>0)J[static_cast<size_t>((2*h+i)*h+i-1)]=-2.0*sq_rd2; if(i>1)J[static_cast<size_t>((2*h+i)*h+i-2)]=sq_rd2;
                J[static_cast<size_t>((3*h+i)*h+i)]=sq_ru;
            }
        }
        return std::isfinite(value);
    };
    std::vector<double> residual,J; double value=0.0;
    if(!evaluate(x,false,residual,J,value)){std::fill(x.begin(),x.end(),prev);if(!evaluate(x,false,residual,J,value))value=std::numeric_limits<double>::quiet_NaN();}
    bool success=false;
    if(std::isfinite(value)){
        double span=std::abs(u_max-u_min),scale=std::max({span,std::abs(prev),1.0});
        double trust=std::max(1e-6,0.5*scale)*std::sqrt(static_cast<double>(h)),maxtrust=std::max(trust,8.0*scale*std::sqrt(static_cast<double>(h)));
        double damping=std::max(1e-8,1e-4*(q+rd+rd2+ru+1.0));
        for(int it=0;it<std::max(1,opt_iter);++it){
            if(!evaluate(x,true,residual,J,value)){damping*=10;trust*=0.25;if(trust<=1e-12)break;continue;}
            std::vector<double> H(static_cast<size_t>(h*h),0.0),g(static_cast<size_t>(h),0.0),step;
            for(npy_intp r=0;r<4*h;++r){const double* row=J.data()+r*h;double rv=residual[static_cast<size_t>(r)];for(npy_intp i=0;i<h;++i){g[static_cast<size_t>(i)]-=row[i]*rv;for(npy_intp j=0;j<=i;++j)H[static_cast<size_t>(i*h+j)]+=row[i]*row[j];}}
            for(npy_intp i=0;i<h;++i){for(npy_intp j=0;j<i;++j)H[static_cast<size_t>(j*h+i)]=H[static_cast<size_t>(i*h+j)];H[static_cast<size_t>(i*h+i)]+=damping;}
            if(!solve_spd_cholesky(H,g,h,step)){damping*=10;continue;}
            double sn=0,xn=0;for(npy_intp i=0;i<h;++i){sn+=step[static_cast<size_t>(i)]*step[static_cast<size_t>(i)];xn+=x[static_cast<size_t>(i)]*x[static_cast<size_t>(i)];}sn=std::sqrt(sn);xn=std::sqrt(xn);
            if(sn<=1e-9*(1+xn)){success=true;break;} if(sn>trust){double z=trust/sn;for(double&v:step)v*=z;}
            bool accepted=false;double alpha=1,best=value;std::vector<double> trial,bestres,bestJ,bestx=x;
            for(int bt=0;bt<12;++bt){trial=x;for(npy_intp i=0;i<h;++i)trial[static_cast<size_t>(i)]+=alpha*step[static_cast<size_t>(i)];double tv; if(evaluate(trial,false,bestres,bestJ,tv)&&tv<best){best=tv;bestx=trial;accepted=true;break;}alpha*=0.5;}
            if(accepted){double drop=(value-best)/std::max(1.0,value);x=bestx;value=best;damping=std::max(1e-12,damping*0.3);trust=std::min(maxtrust,trust*1.5);success=true;if(drop<=1e-10)break;}else{damping*=10;trust*=0.5;if(trust<=1e-12)break;}
        }
    }
    npy_intp dims[1]={h};PyArrayObject* out=(PyArrayObject*)PyArray_SimpleNew(1,dims,NPY_DOUBLE);if(!out){Py_DECREF(ref);Py_DECREF(yh);Py_DECREF(uh);Py_DECREF(theta);Py_DECREF(Pa);Py_XDECREF(warm);return nullptr;}std::memcpy(PyArray_DATA(out),x.data(),static_cast<size_t>(h)*sizeof(double));
    PyObject* result=Py_BuildValue("Nid",out,success?1:0,value);
    Py_DECREF(ref);Py_DECREF(yh);Py_DECREF(uh);Py_DECREF(theta);Py_DECREF(Pa);Py_XDECREF(warm);return result;
}



struct MicrogridParams {
    double T_g, T_t, T_bess, H, D, R, bess_power_max, diesel_bias,
           load_bias, energy_capacity, deadband_hz;
};

inline void microgrid_rhs(const double* x, double u, const MicrogridParams& p, double* dx) {
    const double xg=x[0], pm=x[1], df=x[2], pb=x[3], soc=x[4];
    const double db = std::abs(df) <= p.deadband_hz ? 0.0 : df - std::copysign(p.deadband_hz, df);
    dx[0] = (-xg + p.diesel_bias - db / p.R) / p.T_g;
    dx[1] = (-pm + xg) / p.T_t;
    const double availability = std::clamp(4.0 * soc * (1.0 - soc), 0.0, 1.0);
    const double pb_cmd = p.bess_power_max * availability * std::tanh(u);
    dx[3] = (pb_cmd - pb) / p.T_bess;
    dx[2] = (pm + pb - p.load_bias - p.D * df) / (2.0 * p.H);
    dx[4] = -pb / p.energy_capacity;
    if (soc <= 0.02 && dx[4] < 0.0) dx[4] = 0.0;
    if (soc >= 0.98 && dx[4] > 0.0) dx[4] = 0.0;
}

inline void rk4_step_microgrid(double* x, double u, double h, const MicrogridParams& p, bool preg, double r_preg) {
    double k1[5],k2[5],k3[5],k4[5],tmp[5];
    auto input=[&](const double* state){return preg ? r_preg*(u-state[2]) : u;};
    microgrid_rhs(x,input(x),p,k1);
    for(int i=0;i<5;++i) tmp[i]=x[i]+0.5*h*k1[i];
    microgrid_rhs(tmp,input(tmp),p,k2);
    for(int i=0;i<5;++i) tmp[i]=x[i]+0.5*h*k2[i];
    microgrid_rhs(tmp,input(tmp),p,k3);
    for(int i=0;i<5;++i) tmp[i]=x[i]+h*k3[i];
    microgrid_rhs(tmp,input(tmp),p,k4);
    for(int i=0;i<5;++i) x[i]+=h*(k1[i]+2.0*k2[i]+2.0*k3[i]+k4[i])/6.0;
}

PyObject* simulate_microgrid_interval(PyObject*, PyObject* args, PyObject* kwargs) {
    PyObject* state_obj;
    double u,dt,dt_internal,T_g,T_t,T_bess,H,D,R,bess_power_max,diesel_bias,load_bias,energy_capacity,deadband_hz,r_preg=1.0;
    int preg=0;
    static const char* names[]={"state","u","dt","dt_internal","T_g","T_t","T_bess","H","D","R","bess_power_max","diesel_bias","load_bias","energy_capacity","deadband_hz","preg","r_preg",nullptr};
    if(!PyArg_ParseTupleAndKeywords(args,kwargs,"Odddddddddddddd|pd",const_cast<char**>(names),
        &state_obj,&u,&dt,&dt_internal,&T_g,&T_t,&T_bess,&H,&D,&R,&bess_power_max,&diesel_bias,&load_bias,&energy_capacity,&deadband_hz,&preg,&r_preg)) return nullptr;
    PyArrayObject* state=as_double_1d(state_obj);
    if(!state) return nullptr;
    if(PyArray_SIZE(state)!=5 || dt<=0.0 || dt_internal<=0.0){Py_DECREF(state);PyErr_SetString(PyExc_ValueError,"microgrid state must have 5 elements and time steps must be positive");return nullptr;}
    MicrogridParams p{T_g,T_t,T_bess,H,D,R,bess_power_max,diesel_bias,load_bias,energy_capacity,deadband_hz};
    double x[5]; std::memcpy(x,PyArray_DATA(state),5*sizeof(double));
    const int n=std::max(1,static_cast<int>(std::ceil(dt/dt_internal)));
    const double h=dt/static_cast<double>(n);
    Py_BEGIN_ALLOW_THREADS
    for(int i=0;i<n;++i) rk4_step_microgrid(x,u,h,p,preg!=0,r_preg);
    Py_END_ALLOW_THREADS
    npy_intp dims[1]={5};
    PyArrayObject* out=(PyArrayObject*)PyArray_SimpleNew(1,dims,NPY_DOUBLE);
    if(!out){Py_DECREF(state);return nullptr;}
    std::memcpy(PyArray_DATA(out),x,5*sizeof(double));
    const double u_phys=(preg!=0)?r_preg*(u-x[2]):u;
    Py_DECREF(state);
    return Py_BuildValue("Nd",out,u_phys);
}


PyObject* mrac_adaptive_update(PyObject*, PyObject* args, PyObject* kwargs) {
    PyObject *v_obj,*g_obj,*dv_prev_obj=Py_None;
    double e,r0,gr,mu_v,mu_r,eps,rmin,rmax,alpha_v=1.0,alpha_r=1.0,dr_prev=0.0,vnorm_max=0.0;
    int ngd=1;
    static const char* names[]={"v","g_v","e","r0","g_r0","mu_v","mu_r0","eps","r0_min","r0_max","ngd","dv_prev","dr_prev","alpha_v","alpha_r0","v_norm_max",nullptr};
    if(!PyArg_ParseTupleAndKeywords(args,kwargs,"OOddddddddp|Odddd",const_cast<char**>(names),
        &v_obj,&g_obj,&e,&r0,&gr,&mu_v,&mu_r,&eps,&rmin,&rmax,&ngd,&dv_prev_obj,&dr_prev,&alpha_v,&alpha_r,&vnorm_max)) return nullptr;
    PyArrayObject* va=as_double_1d(v_obj); PyArrayObject* ga=as_double_1d(g_obj);
    if(!va||!ga){Py_XDECREF(va);Py_XDECREF(ga);return nullptr;}
    npy_intp n=PyArray_SIZE(va); if(PyArray_SIZE(ga)!=n){Py_DECREF(va);Py_DECREF(ga);PyErr_SetString(PyExc_ValueError,"v and g_v size mismatch");return nullptr;}
    PyArrayObject* dpa=nullptr;
    if(dv_prev_obj!=Py_None){dpa=as_double_1d(dv_prev_obj); if(!dpa||PyArray_SIZE(dpa)!=n){Py_XDECREF(dpa);Py_DECREF(va);Py_DECREF(ga);PyErr_SetString(PyExc_ValueError,"dv_prev size mismatch");return nullptr;}}
    const double* v=(double*)PyArray_DATA(va); const double* g=(double*)PyArray_DATA(ga); const double* dp=dpa?(double*)PyArray_DATA(dpa):nullptr;
    double g2=0.0; for(npy_intp i=0;i<n;++i) g2+=g[i]*g[i];
    double eta_v=ngd?mu_v/(eps+g2):mu_v; double eta_r=ngd?mu_r/(eps+gr*gr):mu_r;
    npy_intp dims[1]={n}; auto* vo=(PyArrayObject*)PyArray_SimpleNew(1,dims,NPY_DOUBLE); auto* dvo=(PyArrayObject*)PyArray_SimpleNew(1,dims,NPY_DOUBLE);
    double* vn=(double*)PyArray_DATA(vo); double* dvn=(double*)PyArray_DATA(dvo);
    double norm2=0.0;
    for(npy_intp i=0;i<n;++i){double raw=-eta_v*e*g[i]; double sm=alpha_v*raw+(1.0-alpha_v)*(dp?dp[i]:0.0); dvn[i]=sm; vn[i]=v[i]+sm; norm2+=vn[i]*vn[i];}
    if(vnorm_max>0.0){double nm=std::sqrt(norm2); if(nm>vnorm_max){double sc=vnorm_max/nm; for(npy_intp i=0;i<n;++i)vn[i]*=sc;}}
    double dr_raw=-eta_r*e*gr; double dr=alpha_r*dr_raw+(1.0-alpha_r)*dr_prev; double rn=std::clamp(r0+dr,rmin,rmax);
    double rank=1.0-eta_v*g2; double a2=std::max(1.0,std::abs(rank)); double rho=a2; double ar=std::abs(1.0-eta_r*gr*gr);
    Py_XDECREF(dpa);Py_DECREF(va);Py_DECREF(ga);
    return Py_BuildValue("NNddddd",vo,dvo,rn,dr,a2,rho,ar);
}

PyMethodDef methods[] = {
    {"predict_sequence_and_jacobian", reinterpret_cast<PyCFunction>(predict_sequence_and_jacobian), METH_VARARGS | METH_KEYWORDS,
     "Fast recursive HONU rollout and exact Jacobian."},
    {"optimize_u", reinterpret_cast<PyCFunction>(optimize_u_native), METH_VARARGS | METH_KEYWORDS,
     "Native complete HONU MPC Gauss-Newton optimizer."},
    {"simulate_microgrid_interval", reinterpret_cast<PyCFunction>(simulate_microgrid_interval), METH_VARARGS | METH_KEYWORDS,
     "Native RK4 integration of the nonlinear microgrid model."},
    {"mrac_adaptive_update", reinterpret_cast<PyCFunction>(mrac_adaptive_update), METH_VARARGS | METH_KEYWORDS,
     "Native MRAC GD/NGD adaptation update and stability metrics."},
    {nullptr, nullptr, 0, nullptr}
};

PyModuleDef module = {PyModuleDef_HEAD_INIT, "_honu_mpc_native", "C++ HONU MPC kernels", -1, methods};

}  // namespace

PyMODINIT_FUNC PyInit__honu_mpc_native() {
    import_array();
    return PyModule_Create(&module);
}
