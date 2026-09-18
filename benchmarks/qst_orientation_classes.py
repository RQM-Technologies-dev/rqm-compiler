"""Classify the unresolved half of exact rank-2 boundary maps.

Tests whether the obstruction to SO(3)-only QST is explained by O(3)
orientation reversal / conjugation (det=-1), and correlates class with Cartan
angle/Weyl-sign features. No extra spectral rank is introduced.
"""
import json,random
from pathlib import Path
import numpy as np
import runpy
ns=runpy.run_path("benchmarks/qst_reconstruction.py",run_name="qst_helpers")
rng=random.Random(43);maps=[]
for k in range(128):
 a01,b01,a12,b12=[rng.uniform(-np.pi,np.pi) for _ in range(4)]
 T12=ns["transfer"](ns["block"](a12,b12),ns["ZERO"],ns["Z"])
 O1=ns["apply"](T12,ns["Z"]);T01=ns["transfer"](ns["block"](a01,b01),ns["ZERO"],O1)
 maps.extend([(k,"inner",T12,a12,b12),(k,"outer",T01,a01,b01)])
P=np.diag([1.,0.,0.,1.])
# canonical vector reflections. det=-1 frames are not unit-quaternion rotations.
REF=[("proper",np.eye(3)),("reflect_x",np.diag([-1,1,1.])),("reflect_y",np.diag([1,-1,1.])),("reflect_z",np.diag([1,1,-1.]))]
def frame(R):Q=np.eye(4);Q[1:,1:]=R;return Q
def axis(S):
 W=S[1:,:];u,s,vh=np.linalg.svd(W,full_matrices=False);return u[:,0]
rows=[]
for k,stage,T,a,b in maps:
 u,s,vh=np.linalg.svd(T);nl=axis(u[:,:2]);nr=axis(vh.T[:,:2])
 RL0=ns["rot_to_z"](nl);RR0=ns["rot_to_z"](nr)
 best=None
 for ll,FL in REF:
  for rr,FR in REF:
   RL=frame(RL0@FL);RR=frame(RR0@FR)
   A=RL@np.diag([1,0,0,0])@RR.T;B=RL@np.diag([0,0,0,1])@RR.T
   G=np.array([[np.sum(A*A),np.sum(A*B)],[np.sum(A*B),np.sum(B*B)]])
   y=np.array([np.sum(T*A),np.sum(T*B)]);w=np.linalg.lstsq(G,y,rcond=None)[0]
   res=float(np.linalg.norm(T-w[0]*A-w[1]*B))
   cand=(res,ll,rr,float(w[0]),float(w[1]),float(np.linalg.det(RL[1:,1:])),float(np.linalg.det(RR[1:,1:])))
   if best is None or cand[0]<best[0]:best=cand
 rows.append({"case":k,"stage":stage,"residual":best[0],"left_class":best[1],"right_class":best[2],"lambda0":best[3],"lambda1":best[4],
              "det_left":best[5],"det_right":best[6],"angle_xx":a,"angle_zz":b})
from collections import Counter
summary={"maps":256,"exact":sum(r["residual"]<=1e-9 for r in rows),"median_residual":float(np.median([r["residual"] for r in rows])),
 "max_residual":max(r["residual"] for r in rows),"classes":dict(Counter(r["left_class"]+"|"+r["right_class"] for r in rows)),
 "exact_improper":sum(r["residual"]<=1e-9 and (r["det_left"]<0 or r["det_right"]<0) for r in rows)}
Path("results").mkdir(exist_ok=True);Path("results/qst_orientation_classes.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2));print(json.dumps(summary))
