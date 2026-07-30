#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <numpy/arrayobject.h>
#include <algorithm>
#include <cmath>
#include <vector>

namespace {
PyArrayObject* a1(PyObject* o){return (PyArrayObject*)PyArray_FROM_OTF(o,NPY_DOUBLE,NPY_ARRAY_IN_ARRAY);}
PyArrayObject* ai1(PyObject* o){return (PyArrayObject*)PyArray_FROM_OTF(o,NPY_INT64,NPY_ARRAY_IN_ARRAY);}
PyArrayObject* a2(PyObject* o){auto* a=(PyArrayObject*)PyArray_FROM_OTF(o,NPY_DOUBLE,NPY_ARRAY_IN_ARRAY); if(a&&PyArray_NDIM(a)!=2){PyErr_SetString(PyExc_ValueError,"P must be 2-D");Py_DECREF(a);return nullptr;}return a;}

void mlp_eval(const std::vector<double>& x,const double* th,const std::vector<long long>& sizes,double& out,std::vector<double>& gx){
 size_t pos=0; std::vector<std::vector<double>> acts; acts.push_back(x);
 for(size_t l=0;l+1<sizes.size();++l){size_t ni=sizes[l], no=sizes[l+1]; std::vector<double> z(no); const auto& in=acts.back();
  for(size_t r=0;r<no;++r){double s=0;for(size_t c=0;c<ni;++c)s+=th[pos+r*ni+c]*in[c];z[r]=s;} pos+=no*ni; for(size_t r=0;r<no;++r)z[r]+=th[pos+r]; pos+=no;
  if(l+2<sizes.size())for(double& v:z)v=std::tanh(v); acts.push_back(std::move(z));}
 out=acts.back()[0]; gx.assign((size_t)sizes[0],0.0); std::vector<double> g(1,1.0); pos=0;
 std::vector<size_t> wpos,bpos; for(size_t l=0;l+1<sizes.size();++l){wpos.push_back(pos);pos+=(size_t)sizes[l]*sizes[l+1];bpos.push_back(pos);pos+=sizes[l+1];}
 for(size_t ll=sizes.size()-1;ll-->0;){size_t ni=sizes[ll],no=sizes[ll+1];std::vector<double> gin(ni,0.0);const double* W=th+wpos[ll];
  for(size_t r=0;r<no;++r){double gr=g[r]; if(ll+2<sizes.size()){double a=acts[ll+1][r];gr*=1-a*a;} for(size_t c=0;c<ni;++c)gin[c]+=gr*W[r*ni+c];} g.swap(gin);}
 gx=g;
}

PyObject* predict_mlp(PyObject*,PyObject* args,PyObject* kw){
 PyObject *co,*yo,*uo,*to,*so,*hmo,*hso,*Po,*fmo,*fso; int ny,nu,delay,hd,is_delta,withj=1; double scale;
 static const char* n[]={"candidate_u","y_hist","u_hist","theta","layer_sizes","history_mean","history_std","P","future_mean","future_std","ny","nu","delay_u","history_dim","target_scale","is_delta","compute_jacobian",nullptr};
 if(!PyArg_ParseTupleAndKeywords(args,kw,"OOOOOOOOOOiiiidp|p",(char**)n,&co,&yo,&uo,&to,&so,&hmo,&hso,&Po,&fmo,&fso,&ny,&nu,&delay,&hd,&scale,&is_delta,&withj))return nullptr;
 auto *ca=a1(co),*ya=a1(yo),*ua=a1(uo),*ta=a1(to),*sa=ai1(so),*hma=a1(hmo),*hsa=a1(hso),*pa=a2(Po),*fma=a1(fmo),*fsa=a1(fso);
 if(!ca||!ya||!ua||!ta||!sa||!hma||!hsa||!pa||!fma||!fsa){Py_XDECREF(ca);Py_XDECREF(ya);Py_XDECREF(ua);Py_XDECREF(ta);Py_XDECREF(sa);Py_XDECREF(hma);Py_XDECREF(hsa);Py_XDECREF(pa);Py_XDECREF(fma);Py_XDECREF(fsa);return nullptr;}
 npy_intp H=PyArray_SIZE(ca),bd=ny+nu,pc=PyArray_DIM(pa,1); std::vector<long long> sizes((long long*)PyArray_DATA(sa),(long long*)PyArray_DATA(sa)+PyArray_SIZE(sa));
 if(sizes.size()<2||sizes.front()!=pc+(bd-hd)||sizes.back()!=1){PyErr_SetString(PyExc_ValueError,"MLP dimensions mismatch");goto fail;}
 {npy_intp od[1]={H},jd[2]={H,H};auto* out=(PyArrayObject*)PyArray_SimpleNew(1,od,NPY_DOUBLE);auto* jac=withj?(PyArrayObject*)PyArray_ZEROS(2,jd,NPY_DOUBLE,0):nullptr;
 const double *cp=(double*)PyArray_DATA(ca),*yp=(double*)PyArray_DATA(ya),*up=(double*)PyArray_DATA(ua),*th=(double*)PyArray_DATA(ta),*hm=(double*)PyArray_DATA(hma),*hs=(double*)PyArray_DATA(hsa),*P=(double*)PyArray_DATA(pa),*fm=(double*)PyArray_DATA(fma),*fs=(double*)PyArray_DATA(fsa);double* op=(double*)PyArray_DATA(out);double* jp=jac?(double*)PyArray_DATA(jac):nullptr;
 std::vector<double> ys(yp+std::max<npy_intp>(0,PyArray_SIZE(ya)-ny),yp+PyArray_SIZE(ya)),us; npy_intp keep=delay+nu,un=PyArray_SIZE(ua); if(keep>0)us.assign(up+std::max<npy_intp>(0,un-keep),up+un);
 std::vector<std::vector<double>> yg(ys.size(),std::vector<double>(H)),ug(us.size(),std::vector<double>(H));
 for(npy_intp k=0;k<H;++k){us.push_back(cp[k]);if(withj){std::vector<double> q(H);q[k]=1;ug.push_back(q);}std::vector<double>b(bd);for(int i=0;i<ny;++i)if((size_t)i<ys.size())b[i]=ys[ys.size()-1-i];for(int i=0;i<nu;++i){long ix=(long)us.size()-1-delay-i;if(ix>=0)b[ny+i]=us[ix];}
  std::vector<double>x((size_t)(pc+bd-hd));for(npy_intp j=0;j<pc;++j){double s=0;for(int i=0;i<hd;++i)s+=((b[i]-hm[i])/hs[i])*P[i*pc+j];x[j]=s;}for(npy_intp i=hd;i<bd;++i)x[pc+i-hd]=(b[i]-fm[i-hd])/fs[i-hd];
  double z;std::vector<double>gx;mlp_eval(x,th,sizes,z,gx);double yn=scale*z+(is_delta?b[0]:0.0);op[k]=yn;
  if(withj){std::vector<double>gb(bd);for(int i=0;i<hd;++i){double s=0;for(npy_intp j=0;j<pc;++j)s+=gx[j]*P[i*pc+j]/hs[i];gb[i]=scale*s;}for(npy_intp i=hd;i<bd;++i)gb[i]=scale*gx[pc+i-hd]/fs[i-hd];if(is_delta)gb[0]+=1;
   std::vector<double>ng(H);for(int i=0;i<ny;++i)if((size_t)i<yg.size())for(npy_intp c=0;c<H;++c)ng[c]+=gb[i]*yg[yg.size()-1-i][c];for(int i=0;i<nu;++i){long ix=(long)ug.size()-1-delay-i;if(ix>=0)for(npy_intp c=0;c<H;++c)ng[c]+=gb[ny+i]*ug[ix][c];}for(npy_intp c=0;c<H;++c)jp[k*H+c]=ng[c];yg.push_back(ng);}ys.push_back(yn);}
 PyObject* jo=withj?(PyObject*)jac:Py_None;if(!withj)Py_INCREF(Py_None);PyObject* r=PyTuple_Pack(2,(PyObject*)out,jo);Py_DECREF(out);Py_DECREF(jo);Py_DECREF(ca);Py_DECREF(ya);Py_DECREF(ua);Py_DECREF(ta);Py_DECREF(sa);Py_DECREF(hma);Py_DECREF(hsa);Py_DECREF(pa);Py_DECREF(fma);Py_DECREF(fsa);return r;}
 fail: Py_DECREF(ca);Py_DECREF(ya);Py_DECREF(ua);Py_DECREF(ta);Py_DECREF(sa);Py_DECREF(hma);Py_DECREF(hsa);Py_DECREF(pa);Py_DECREF(fma);Py_DECREF(fsa);return nullptr;
}
PyMethodDef methods[]={{"predict_mlp_sequence_and_jacobian",(PyCFunction)predict_mlp,METH_VARARGS|METH_KEYWORDS,"Fast recursive MLP rollout."},{nullptr,nullptr,0,nullptr}};
PyModuleDef module={PyModuleDef_HEAD_INIT,"_mlp_mpc_native","C++ MLP MPC kernel",-1,methods};
}
PyMODINIT_FUNC PyInit__mlp_mpc_native(){import_array();return PyModule_Create(&module);}
