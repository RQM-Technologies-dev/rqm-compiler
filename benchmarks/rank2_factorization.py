"""Factor rank-2 recursive boundary maps into spectral modes.

Recreates the 128 randomized map-valued cases, computes SVD/eigensystem,
principal subspace stability, and tests whether left/right active frames have
SO(3)/quaternion-compatible vector blocks. <10 min.
"""
import json,math,random
from pathlib import Path
import numpy as np
from rqm_compiler import Circuit
from rqm_compiler.su4_blocks import _operation_matrix

I=np.eye(2,dtype=complex);X=np.array([[0,1],[1,0]],complex);Y=np.array([[0,-1j],[1j,0]],complex);Z=np.array([[1,0],[0,-1]],complex)
B=(I,X,Y,Z);ZERO=np.array([[1,0],[0,0]],complex)

def block(a,b):
 c=Circuit(2);c.rxx(0,1,a);c.rzz(0,1,b);c.cx(0,1);U=np.eye(4,dtype=complex)
 for op in c.operations:U=_operation_matrix(op,(0,1))@U
 return U
def transfer(U,rho,O):
 T=np.zeros((4,4),complex)
 for nu,Op in enumerate(B):
  A=U.conj().T@np.kron(O,Op)@U;C=np.kron(rho,I)@A;x=C.reshape(2,2,2,2);M=np.einsum("abad->bd",x)
  for mu,S in enumerate(B):T[mu,nu]=np.trace(S@M)/2
 return T
def apply(T,O):
 v=np.array([np.trace(S@O)/2 for S in B],complex);w=T@v
 return sum(w[i]*B[i] for i in range(4))
def analyze(T):
 u,s,vh=np.linalg.svd(T)
 energy=(s[:2]@s[:2])/(s@s) if s@s else 1
 # rank-2 reconstruction is the proposed two-mode spectral core.
 R=(u[:,:2]*s[:2])@vh[:2,:]
 resid=float(np.linalg.norm(T-R))
 # how much active singular vectors mix scalar I coordinate with XYZ sector
 scalar_left=float(np.sum(np.abs(u[0,:2])**2));scalar_right=float(np.sum(np.abs(vh[:2,0])**2))
 return s,resid,float(energy),scalar_left,scalar_right,u[:,:2],vh.conj().T[:,:2]
rng=random.Random(43);rows=[];left_projectors=[];right_projectors=[]
for k in range(128):
 a01,b01,a12,b12=[rng.uniform(-math.pi,math.pi) for _ in range(4)]
 T12=transfer(block(a12,b12),ZERO,Z);O1=apply(T12,Z);T01=transfer(block(a01,b01),ZERO,O1)
 for stage,T in (("inner",T12),("outer",T01)):
  s,resid,energy,sl,sr,U,V=analyze(T);left_projectors.append(U@U.conj().T);right_projectors.append(V@V.conj().T)
  rows.append({"case":k,"stage":stage,"singular_values":[float(x) for x in s],"rank2_residual":resid,"rank2_energy":energy,
               "scalar_left_weight":sl,"scalar_right_weight":sr})
# Projector spread tests whether the same fixed 2D modes work for all cases.
LP=sum(left_projectors)/len(left_projectors);RP=sum(right_projectors)/len(right_projectors)
summary={"maps":len(rows),"max_rank2_residual":max(r["rank2_residual"] for r in rows),
 "min_rank2_energy":min(r["rank2_energy"] for r in rows),
 "median_s1":float(np.median([r["singular_values"][0] for r in rows])),
 "median_s2":float(np.median([r["singular_values"][1] for r in rows])),
 "max_s3":max(r["singular_values"][2] for r in rows),
 "left_mean_projector_eigenvalues":[float(x.real) for x in np.linalg.eigvalsh(LP)[::-1]],
 "right_mean_projector_eigenvalues":[float(x.real) for x in np.linalg.eigvalsh(RP)[::-1]],
 "scalar_left_weight_range":[min(r["scalar_left_weight"] for r in rows),max(r["scalar_left_weight"] for r in rows)],
 "scalar_right_weight_range":[min(r["scalar_right_weight"] for r in rows),max(r["scalar_right_weight"] for r in rows)]}
Path("results").mkdir(exist_ok=True);Path("results/rank2_factorization.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2));print(json.dumps(summary))
