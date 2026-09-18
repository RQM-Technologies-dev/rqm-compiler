"""Classify the discrete obstruction in constrained QST reconstruction.

Compare the fixed-projector quaternionic fit against a small signed/permuted
spectral-core family. This determines whether the 193 failures need extra
continuous dimensions or only a discrete Cartan/parity label plus independent
mode weights.
"""
import json,runpy
from pathlib import Path
import numpy as np
# Recreate helper definitions without relying on artifact state.
ns=runpy.run_path("benchmarks/qst_reconstruction.py",run_name="qst_helpers")
# The script above executes; rebuild its exact maps from exposed globals.
rng=__import__("random").Random(43);maps=[]
for k in range(128):
 vals=[rng.uniform(-np.pi,np.pi) for _ in range(4)]
 a01,b01,a12,b12=vals
 T12=ns["transfer"](ns["block"](a12,b12),ns["ZERO"],ns["Z"])
 O1=ns["apply"](T12,ns["Z"]);T01=ns["transfer"](ns["block"](a01,b01),ns["ZERO"],O1)
 maps.extend([(k,"inner",T12),(k,"outer",T01)])
# Candidate cores: independent weights on canonical I/Z modes plus discrete
# sign/parity choices. Quaternion frames are extracted as in prior QST test.
cores=[]
for si in (-1,1):
 for sz in (-1,1):
  cores.append((f"sign_{si}_{sz}",np.diag([si,0,0,sz]).astype(float)))
rows=[]
for k,stage,T in maps:
 u,s,vh=np.linalg.svd(T);U=u[:,:2];V=vh.T[:,:2]
 axis=ns["qst_fit"] # reuse frame extraction indirectly via original fit axes
 Q0,lam,nl,nr,res0=axis(T)
 RL=ns["frame"](ns["rot_to_z"](nl));RR=ns["frame"](ns["rot_to_z"](nr))
 best=None
 for label,C in cores:
  # solve two independent spectral weights after applying the discrete signs
  A=RL@np.diag([C[0,0],0,0,0])@RR.T
  B=RL@np.diag([0,0,0,C[3,3]])@RR.T
  G=np.array([[np.sum(A*A),np.sum(A*B)],[np.sum(A*B),np.sum(B*B)]])
  y=np.array([np.sum(T*A),np.sum(T*B)])
  w=np.linalg.lstsq(G,y,rcond=None)[0];Q=w[0]*A+w[1]*B;res=float(np.linalg.norm(T-Q))
  cand=(res,label,float(w[0]),float(w[1]))
  if best is None or cand[0]<best[0]:best=cand
 rows.append({"case":k,"stage":stage,"old_pass":res0<=1e-9,"best_residual":best[0],"label":best[1],"lambda0":best[2],"lambda1":best[3]})
from collections import Counter
summary={"maps":256,"old_pass":sum(r["old_pass"] for r in rows),"new_exact":sum(r["best_residual"]<=1e-9 for r in rows),
"median_residual":float(np.median([r["best_residual"] for r in rows])),"max_residual":max(r["best_residual"] for r in rows),
"labels":dict(Counter(r["label"] for r in rows)),"failed_old_now_exact":sum((not r["old_pass"]) and r["best_residual"]<=1e-9 for r in rows)}
Path("results").mkdir(exist_ok=True);Path("results/qst_discrete_classification.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2));print(json.dumps(summary))
