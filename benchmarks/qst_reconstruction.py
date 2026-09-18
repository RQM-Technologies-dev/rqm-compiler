"""Constrained Quaternionic Spectral Transfer (QST) reconstruction test.

Fits exact rank-2 boundary maps to lambda R_L P2 R_R where R_L/R_R are
adjoint SO(3) actions of unit quaternions embedded as diag(1,SO3), and P2 is
the fixed projector onto span{I,Z}. Uses numerical Procrustes extraction of
the active Bloch axes; no arbitrary SVD matrices are retained in QST.
"""
import json,math,random
from pathlib import Path
import numpy as np
from rqm_compiler import Circuit
from rqm_compiler.su4_blocks import _operation_matrix

I=np.eye(2,dtype=complex);X=np.array([[0,1],[1,0]],complex);Y=np.array([[0,-1j],[1j,0]],complex);Z=np.array([[1,0],[0,-1]],complex)
B=(I,X,Y,Z);ZERO=np.array([[1,0],[0,0]],complex);P2=np.diag([1.,0.,0.,1.])

def block(a,b):
 c=Circuit(2);c.rxx(0,1,a);c.rzz(0,1,b);c.cx(0,1);U=np.eye(4,dtype=complex)
 for op in c.operations:U=_operation_matrix(op,(0,1))@U
 return U
def transfer(U,rho,O):
 T=np.zeros((4,4),float)
 for nu,Op in enumerate(B):
  A=U.conj().T@np.kron(O,Op)@U;C=np.kron(rho,I)@A;x=C.reshape(2,2,2,2);M=np.einsum("abad->bd",x)
  for mu,S in enumerate(B):T[mu,nu]=float((np.trace(S@M)/2).real)
 return T
def apply(T,O):
 v=np.array([float((np.trace(S@O)/2).real) for S in B]);w=T@v
 return sum(w[i]*B[i] for i in range(4))
def rot_to_z(n):
 n=np.asarray(n,float);n/=np.linalg.norm(n)
 z=np.array([0.,0.,1.]);v=np.cross(z,n);c=float(z@n)
 if np.linalg.norm(v)<1e-14:return np.eye(3) if c>0 else np.diag([1,-1,-1])
 vx=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
 return np.eye(3)+vx+vx@vx/(1+c)
def frame(R3):
 R=np.eye(4);R[1:,1:]=R3;return R
def qst_fit(T):
 # active input Bloch axis from rank-2 right singular space; output likewise.
 u,s,vh=np.linalg.svd(T);U=u[:,:2];V=vh.T[:,:2]
 def axis(S):
  # remove scalar projection, principal XYZ direction
  W=S[1:,:];uu,ss,vv=np.linalg.svd(W,full_matrices=False);return uu[:,0]
 nl=axis(U);nr=axis(V)
 RL=frame(rot_to_z(nl));RR=frame(rot_to_z(nr))
 # Our rotations map canonical z -> n. Fixed P2 between them.
 core=RL@P2@RR.T
 lam=float(np.sum(T*core)/np.sum(core*core))
 Q=lam*core
 return Q,lam,nl,nr,float(np.linalg.norm(T-Q))
rng=random.Random(43);rows=[];maps=[]
for k in range(128):
 a01,b01,a12,b12=[rng.uniform(-math.pi,math.pi) for _ in range(4)]
 T12=transfer(block(a12,b12),ZERO,Z);O1=apply(T12,Z);T01=transfer(block(a01,b01),ZERO,O1)
 maps.append((k,"inner",T12));maps.append((k,"outer",T01))
for k,stage,T in maps:
 Q,lam,nl,nr,res=qst_fit(T);rows.append({"case":k,"stage":stage,"lambda":lam,"residual":res,"left_axis":nl.tolist(),"right_axis":nr.tolist()})
summary={"maps":len(rows),"qst_exact_maps":sum(r["residual"]<=1e-9 for r in rows),"median_residual":float(np.median([r["residual"] for r in rows])),"max_residual":max(r["residual"] for r in rows)}
Path("results").mkdir(exist_ok=True);Path("results/qst_fit.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2));print(json.dumps(summary))
