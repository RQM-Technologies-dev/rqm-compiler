"""Classify left/right quaternionic bimodule handedness of rank-2 QST maps.

Tests proper SO(3) frames under four action conventions corresponding to
R/R, R/R^T, R^T/R, R^T/R^T around the fixed two-mode core, with independent
spectral weights. This probes action handedness without adding spectral rank.
"""
import json,random,runpy
from pathlib import Path
import numpy as np
ns=runpy.run_path("benchmarks/qst_reconstruction.py",run_name="qst_helpers")
rng=random.Random(43);maps=[]
for k in range(128):
 a01,b01,a12,b12=[rng.uniform(-np.pi,np.pi) for _ in range(4)]
 T12=ns["transfer"](ns["block"](a12,b12),ns["ZERO"],ns["Z"]);O1=ns["apply"](T12,ns["Z"])
 T01=ns["transfer"](ns["block"](a01,b01),ns["ZERO"],O1);maps.extend([(k,"inner",T12),(k,"outer",T01)])
def axis(S):
 W=S[1:,:];u,s,vh=np.linalg.svd(W,full_matrices=False);return u[:,0]
def frame(R):Q=np.eye(4);Q[1:,1:]=R;return Q
CONV=(("L|R",False,False),("L|Rinv",False,True),("Linv|R",True,False),("Linv|Rinv",True,True))
rows=[]
for k,stage,T in maps:
 u,s,vh=np.linalg.svd(T);nl=axis(u[:,:2]);nr=axis(vh.T[:,:2])
 L0=ns["rot_to_z"](nl);R0=ns["rot_to_z"](nr);best=None
 for label,li,ri in CONV:
  L=L0.T if li else L0;R=R0.T if ri else R0;FL=frame(L);FR=frame(R)
  A=FL@np.diag([1,0,0,0])@FR.T;B=FL@np.diag([0,0,0,1])@FR.T
  G=np.array([[np.sum(A*A),np.sum(A*B)],[np.sum(A*B),np.sum(B*B)]])
  y=np.array([np.sum(T*A),np.sum(T*B)]);w=np.linalg.lstsq(G,y,rcond=None)[0]
  res=float(np.linalg.norm(T-w[0]*A-w[1]*B));cand=(res,label,float(w[0]),float(w[1]))
  if best is None or cand[0]<best[0]:best=cand
 rows.append({"case":k,"stage":stage,"residual":best[0],"handedness":best[1],"lambda0":best[2],"lambda1":best[3]})
from collections import Counter
summary={"maps":256,"exact":sum(r["residual"]<=1e-9 for r in rows),"median_residual":float(np.median([r["residual"] for r in rows])),
"max_residual":max(r["residual"] for r in rows),"handedness":dict(Counter(r["handedness"] for r in rows)),
"exact_by_handedness":dict(Counter(r["handedness"] for r in rows if r["residual"]<=1e-9))}
Path("results").mkdir(exist_ok=True);Path("results/qst_handedness.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2));print(json.dumps(summary))
