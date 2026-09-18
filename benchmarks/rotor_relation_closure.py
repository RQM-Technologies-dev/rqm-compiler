"""Three-qubit rotor + one-relation closure experiment.

Retains a scalar/quaternion boundary object plus one exact two-axis relation
descriptor instead of collapsing the eliminated subtree to the rotor alone.
No Pauli-sum fallback. Dense 3Q evolution is only the independent judge.
"""
import json,math,random
from pathlib import Path
import numpy as np
from rqm_compiler import Circuit
from rqm_compiler.verification import _apply_gate_to_state
from rqm_compiler.su4_blocks import _operation_matrix

ZERO=np.array([[1,0],[0,0]],complex)
Z=np.array([[1,0],[0,-1]],complex)
I=np.eye(2,dtype=complex)

def block(a,b):
 c=Circuit(2);c.rxx(0,1,a);c.rzz(0,1,b);c.cx(0,1)
 U=np.eye(4,dtype=complex)
 for op in c.operations:U=_operation_matrix(op,(0,1))@U
 return U

def eliminate_with_relation(U,O):
 # Exact boundary contraction plus one retained relation tensor R capturing
 # the leaf-conditioned difference between Z=+1 and Z=-1 sectors.
 A=U.conj().T@np.kron(O,I)@U
 # scalar/quaternion-like boundary message for |0><0| leaf input
 B0=np.kron(ZERO,I)@A
 x0=B0.reshape(2,2,2,2)
 M=np.einsum("abad->bd",x0)
 # one retained relation: difference of leaf projectors, equivalent to a
 # conditioned hinge/Cartan correction carried alongside M
 PLUS=np.array([[1,0],[0,0]],complex)
 MINUS=np.array([[0,0],[0,1]],complex)
 xp=(np.kron(PLUS,I)@A).reshape(2,2,2,2)
 xm=(np.kron(MINUS,I)@A).reshape(2,2,2,2)
 R=np.einsum("abad->bd",xp)-np.einsum("abad->bd",xm)
 return M,R

def defect(M):
 G=M.conj().T@M;s=float(np.trace(G).real/2)
 return float(np.linalg.norm(G-s*I))

def dense(a01,b01,a12,b12):
 c=Circuit(3)
 c.rxx(0,1,a01);c.rzz(0,1,b01);c.cx(0,1)
 c.rxx(1,2,a12);c.rzz(1,2,b12);c.cx(1,2)
 s=[0j]*8;s[0]=1+0j
 for op in c.operations:s=_apply_gate_to_state(s,op,3)
 return float(sum(abs(x)**2*((-1)**i.bit_count()) for i,x in enumerate(s)))

def recurse(a01,b01,a12,b12):
 U12=block(a12,b12)
 M1,R1=eliminate_with_relation(U12,Z)
 # Preserve the relation by lifting the effective q1 observable to M1+R1.
 # This is the candidate single-relation closure rule under test.
 O1=M1+R1
 U01=block(a01,b01)
 M0,R0=eliminate_with_relation(U01,Z@O1)
 return M1,R1,M0,R0,float(M0[0,0].real)

rng=random.Random(37);rows=[]
for k in range(128):
 a01,b01,a12,b12=[rng.uniform(-math.pi,math.pi) for _ in range(4)]
 M1,R1,M0,R0,val=recurse(a01,b01,a12,b12);ref=dense(a01,b01,a12,b12)
 rows.append({"case":k,"inner_rotor_defect":defect(M1),"outer_rotor_defect":defect(M0),
              "relation_norm_inner":float(np.linalg.norm(R1)),"relation_norm_outer":float(np.linalg.norm(R0)),
              "value":val,"reference":ref,"error":abs(val-ref)})
summary={"cases":128,
 "inner_closed":sum(r["inner_rotor_defect"]<=1e-9 for r in rows),
 "outer_closed":sum(r["outer_rotor_defect"]<=1e-9 for r in rows),
 "exact_cases":sum(r["error"]<=1e-9 for r in rows),
 "max_error":max(r["error"] for r in rows),
 "median_error":float(np.median([r["error"] for r in rows])),
 "nonzero_relation_cases":sum(r["relation_norm_inner"]>1e-12 for r in rows)}
Path("results").mkdir(exist_ok=True)
Path("results/rotor_relation_closure.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2))
print(json.dumps(summary))
