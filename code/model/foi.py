import numpy as np
from utils import _,deco,linear_comb,nan_to_value

@deco.nowarn
#@profile
def f_beta_p(P,t):
  # return.shape = (p:4, s:2, i:4, s':2, i':1, h':6, c':5)
  PA_condom = P['PA_condom_t'](t) * P['RPA_condom_s']
  PA_circum = P['PA_circum_t'](t)
  P_gud_t   = P['P_gud_t'](t) * P['P_gud']
  Rbeta_gud_sus = linear_comb(P_gud_t,P['Rbeta_gud_sus'],1).reshape([1,1,2,4,1,1,1,1])
  Rbeta_gud_inf = linear_comb(P_gud_t,P['Rbeta_gud_inf'],1).reshape([1,1,1,1,2,4,1,1])
  beta_a = P['beta_a'] * Rbeta_gud_sus * Rbeta_gud_inf
  beta_a = np.minimum(beta_a,.5) # protect against nan (assumed max beta_a = .5)
  B = 1 - np.exp(np.sum( # for speeed: equivalent to 1 - np.prod((1-R*beta)^(A) * ...)
    np.log(1-beta_a)                                     * (P['A_ap']*(1-PA_condom)*(1-PA_circum)) +
    np.log(1-beta_a*P['Rbeta_condom'])                   * (P['A_ap']*PA_condom*(1-PA_circum)) +
    np.log(1-beta_a*P['Rbeta_circum'])                   * (P['A_ap']*(1-PA_condom)*PA_circum) +
    np.log(1-beta_a*P['Rbeta_condom']*P['Rbeta_circum']) * (P['A_ap']*(PA_condom)*PA_circum), 
  axis=0))
  return B

#@profile
@deco.nanzero # TODO: better solution
def f_beta_pp(P,X):
  # return.shape = (p:4, s:2, i:1, s':2, i':4)
  return (P['beta_p'] * X[_,_,_,:,:,:,:]).sum(axis=(5,6))\
                      / X[_,_,_,:,:,:,:].sum(axis=(5,6))

@deco.nowarn
#@profile
def f_mix(P,X):
  # return.shape = (p:4, s:2, i:1, s':2, i':4)
  tol = 1e-7
  XS = X.sum(axis=(2,3))
  XC = XS[_,:,:] * P['C_psi']
  M0 = XC[:,0,:,_] * XC[:,1,_,:] / XC.sum(axis=2).mean(axis=1)[:,_,_] + tol/10
  m1 = M0.sum(axis=1)
  m2 = M0.sum(axis=2)
  # print(m1 / XC[:,1,:]) # DEBUG == 1, unless XC unbalanced
  # print(m2 / XC[:,0,:]) # DEBUG == 1, unless XC unbalanced
  M = M0 * np.exp(P['pref_pii'])
  for k in range(100):
    r1 = m1 / M.sum(axis=1)
    M *= r1[:,_,:]
    r2 = m2 / M.sum(axis=2)
    M *= r2[:,:,_]
    if (abs(r1-1) < tol).all() and (abs(r2-1) < tol).all():
      break
  M[abs(M)<tol] = 0
  P['mix'][:,0,:,1,:] = M / XS[_,0,:,_]
  P['mix'][:,1,:,0,:] = M.swapaxes(1,2) / XS[_,1,:,_]
  return(P['mix'])

#@profile
def f_lambda(P,X):
  # lam.shape = (s:2, i:4)
  return 1 - np.prod(
    (1 - P['beta_pp'])**(P['mix']),
  axis=(0,3,4))

#@profile
def f_turnover(P,X):
  # turn.shape = (s:2, i:4, i':4, h:6, c:5)
  turn = P['turn_sii'][:,:,:,_,_] * X[:,:,_,:,:]
  # P['ORturn_sus:hiv'] = 0 # DEBUG
  if np.any(X[:,:,1:,:]): # HIV introduced
    Xhiv = X[:,:,1:,:].sum(axis=(2,3))
    # odds of turnover aomng sus vs hiv (source-group-specific)
    Osus = P['ORturn_sus:hiv'] * nan_to_value(X[:,:,0,0] / Xhiv, 1)[:,:,_]
    Phc_hiv = nan_to_value(X[:,:,1:,:] / Xhiv[:,:,_,_], 0)
    turn_hiv = turn.sum(axis=(3,4)) / (1 + Osus)
    turn[:,:,:,1:,:] = turn_hiv[:,:,:,_,_] * Phc_hiv[:,:,_,:,:]
    turn[:,:,:,0,0]  = turn_hiv * Osus
  return turn
