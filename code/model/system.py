import numpy as np
from model import params,target,foi
from utils import _,log,deco,parallel,rk4step

def get_t(t0=1980,tf=2050,dt=0.05):
  return np.round(np.arange(t0,tf+dt,dt),9)

@deco.nowarn
def get_X(X0,t):
  X = np.nan * np.ndarray([*t.shape,*X0.shape])
  X[0] = X0
  return X

def drop_fails(*Rss):
  # Rss is a list of lists of R, which are assumed to be paired.
  # e.g. Rss[0][i] is fit i from scenario A, Rss[1][i] is (paired) fit i from scenario B
  # We drop all fits that have any fail across scenarios
  oks = [all(Ris) for Ris in zip(*Rss)]
  return tuple([R for (R,ok) in zip(Rs,oks) if ok] for Rs in Rss)

def run_n(Ps,t=None,T=None,para=True,**kwds):
  log(2,'system.run_n: '+str(len(Ps)))
  if para:
    fun = lambda P: run(P,t=t,T=T,**kwds)
    Rs = parallel.ppool(len(Ps)).map(fun,Ps)
  else:
    Rs = [run(P,t=t,T=T,**kwds) for P in Ps]
  log(1)
  return Rs

def run(P,t=None,T=None,RPts=None,interval=None):
  if t is None: t = get_t()
  if RPts is None:
    RPts = ['PF_condom_t','PF_circum_t','dx_sit','tx_sit','Rtx_ht','unvx_t','revx_t']
  R = solve(P,t)
  log(3,str(P['seed']).rjust(6)+(' ' if R else '!'))
  if not R:
    return R
  R['foi_mode'] = R['P']['foi_mode']
  if T is not None:
    R['ll'] = target.get_model_ll(T,R,t,interval=interval)
    R['P']['ll'] = R['ll']
  if RPts:
    for RPt in RPts:
      R[RPt] = np.rollaxis(P[RPt](t),-1)
  return R

def solve(P,t):
  X   = get_X(P['X0'],t)
  inc = get_X(np.zeros([4,2,4,2,4]),t)
  b_hiv,b_tpaf = True,True
  for i in range(1,t.size):
    # Ri = rk4step(X[i-1],t[i-1],(t[i]-t[i-1]),get_dX,P=P)
    Ri = get_dX(X[i-1],t[i-1],P) # DEBUG: Euler
    X[i] = X[i-1] + (t[i] - t[i-1]) * Ri['dX']
    inc[i] = Ri['inc']
    if b_hiv and t[i] >= P['t0_hiv']: # introduce HIV
      b_hiv = False
      X[i,:,:,0,:,0] = X[i,:,:,0,0,0,_] * P['PX_h_hiv'][_,_,:]
    if b_tpaf and t[i] >= P['t0_tpaf']: # start accumulating tPAF
      b_tpaf = False
      P['mix_mask'] = P['mix_mask_tpaf']
    if np.any(X[i].sum(axis=2) < 0) or np.any(inc[i] < 0): # abort / fail
      return False
  return {
    'P': P,
    'X': X.sum(axis=3), # sum_k
    't': t,
    'inc': inc,
  }

#@profile
def get_dX(X,t,P):
  # initialize
  dX = 0*X # (s:2, i:4, k:4, h:6, c:5)
  # force of infection
  inc = foi.get_apply_inc(dX,X,t,P) # (p:4, s:2, i:4, s':2, i':4)
  # TODO: reorder these steps?
  # HIV transitions
  dXi = X[:,:,:,1:5,0:3] * P['prog_h'] # all hiv & untreated
  dX[:,:,:,1:5,0:3] -= dXi
  dX[:,:,:,2:6,0:3] += dXi
  # CD4 recovery
  dXi = X[:,:,:,3:6,3:5] * P['unprog_h'] # low CD4 & treated
  dX[:,:,:,3:6,3:5] -= dXi
  dX[:,:,:,2:5,3:5] += dXi
  # births & deaths
  birth, PXe, turn = params.solve_turnover(P,t)
  dX[:,:,0,0,0] += X.sum() * P['birth_t'](t) * PXe
  dX -= X * P['death']
  dX -= X * P['death_hc']
  # turnover
  dXi = turn[:,:,:,_,_,_] * X[:,:,_,:,:,:]
  dX -= dXi.sum(axis=2) # (s:2, i:4, k:5, h:6, c:5)
  dX += dXi.sum(axis=1) # (s:2, i':4, k:5, h:6, c:5)
  # cascade: diagnosis
  dXi = X[:,:,:,1:6,0] * P['dx_sit'](t) * P['Rdx_scen']
  dX[:,:,:,1:6,0] -= dXi # undiag
  dX[:,:,:,1:6,1] += dXi # diag
  # cascade: treatment
  dXi = X[:,:,:,1:6,1] * P['tx_sit'](t) * P['Rtx_ht'](t) * P['Rtx_scen']
  dX[:,:,:,1:6,1] -= dXi # diag
  dX[:,:,:,1:6,3] += dXi # treat
  # cascade: VLS
  dXi = X[:,:,:,1:6,3] * P['vx']
  dX[:,:,:,1:6,3] -= dXi # treat
  dX[:,:,:,1:6,4] += dXi # vls
  # cascade: fail
  dXi = X[:,:,:,1:6,4] * P['unvx_t'](t) * P['Runvx_si'] * P['Rux_scen']
  dX[:,:,:,1:6,4] -= dXi # vls
  dX[:,:,:,1:6,2] += dXi # fail
  # cascade: re-VLS
  dXi = X[:,:,:,1:6,2] * P['revx_t'](t)
  dX[:,:,:,1:6,2] -= dXi # fail
  dX[:,:,:,1:6,4] += dXi # vls
  return {
    'dX': dX,
    'inc': inc,
  }
