"""Map-valued boundary-message validation on 128 randomized 3Q chains.

The candidate path carries the complete boundary transfer as its action on the
four-dimensional one-qubit operator basis. It never constructs a global
statevector and never expands into n-qubit Pauli strings. Dense 3Q evolution is
used only as the independent reference judge.
"""
import json,math,random
from pathlib import Path
import numpy as np
from rqm_compiler import Circuit
from rqm_compiler.verification import _apply_gate_to_state
from rqm_compiler.su4_blocks import _operation_matrix

I=np.eye(2,dtype=complex);X=np.array([[0,1],[1,0]],complex);Y=np.array([[0,-1j],[1j,0]],complex);Z=np.array([[1,0],[0,-1]],complex)
BASIS=(I,X,Y,Z); ZERO=np.array([[1,0],[0,0]],complex)

def block(a,b):
 c=Circuit(2);c.rxx(0,1,a);c.rzz(0,1,b);c.cx(0,1);U=np.eye(4,dtype=complex)
 for op in c.operations:U=_operation_matrix(op,(0,1))@U
 return U

def transfer(U,rho_leaf,O_leaf):
 # columns are coordinates of T(sigma_nu)
 T=np.zeros((4,4),complex)
 for nu,Op in enumerate(BASIS):
  A=U.conj().T@np.kron(O_leaf,Op)@U
  C=np.kron(rho_leaf,I)@A;x=C.reshape(2,2,2,2)
  M=np.einsum("abad->bd",x)
  for mu,S in enumerate(BASIS):T[mu,nu]=np.trace(S@M)/2
 return T

def apply(T,O):
 v=np.array([np.trace(S@O)/2 for S in BASIS],complex)
 w=T@v
 return sum(w[i]*BASIS[i] for i in range(4))

def dense(a01,b01,a12,b12):
 c=Circuit(3);c.rxx(0,1,a01);c.rzz(0,1,b01);c.cx(0,1);c.rxx(1,2,a12);c.rzz(1,2,b12);c.cx(1,2)
 s=[0j]*8;s[0]=1+0j
 for op in c.operations:s=_apply_gate_to_state(s,op,3)
 return float(sum(abs(x)**2*((-1)**i.bit_count()) for i,x in enumerate(s)))

rng=random.Random(43);rows=[]
for k in range(128):
 a01,b01,a12,b12=[rng.uniform(-math.pi,math.pi) for _ in range(4)]
 # q2 subtree -> map acting on q1 operator.
 T12=transfer(block(a12,b12),ZERO,Z)
 O1=apply(T12,Z)
 # q1 subtree -> map acting on q0 operator, preserving the full O1 response.
 T01=transfer(block(a01,b01),ZERO,O1)
 O0=apply(T01,Z)
 val=float(O0[0,0].real);ref=dense(a01,b01,a12,b12)
 # rank is a first proxy for spectral-core complexity.
 rows.append({"case":k,"error":abs(val-ref),"value":val,"reference":ref,
              "rank_inner":int(np.linalg.matrix_rank(T12,tol=1e-10)),
              "rank_outer":int(np.linalg.matrix_rank(T01,tol=1e-10))})
summary={"cases":128,"exact_cases":sum(r["error"]<=1e-9 for r in rows),
 "max_error":max(r["error"] for r in rows),"median_error":float(np.median([r["error"] for r in rows])),
 "inner_ranks":sorted(set(r["rank_inner"] for r in rows)),"outer_ranks":sorted(set(r["rank_outer"] for r in rows))}
Path("results").mkdir(exist_ok=True);Path("results/map_boundary.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2));print(json.dumps(summary))
