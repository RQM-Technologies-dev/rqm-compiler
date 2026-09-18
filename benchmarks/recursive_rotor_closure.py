"""Three-qubit recursive rotor-closure diagnostic. No Pauli expansion."""
import json,math,random
from pathlib import Path
import numpy as np
from rqm_compiler import Circuit
from rqm_compiler.verification import _apply_gate_to_state
from rqm_compiler.su4_blocks import _operation_matrix
from rqm_compiler.ops import Operation
ZERO=np.array([[1,0],[0,0]],complex);Z=np.array([[1,0],[0,-1]],complex);I=np.eye(2,dtype=complex)

def Ublock(a,b):
 c=Circuit(2);c.rxx(0,1,a);c.rzz(0,1,b);c.cx(0,1);U=np.eye(4,dtype=complex)
 for op in c.operations:U=_operation_matrix(op,(0,1))@U
 return U
def eliminate(U,O):
 A=U.conj().T@np.kron(O,I)@U;B=np.kron(ZERO,I)@A;x=B.reshape(2,2,2,2)
 return np.einsum("abad->bd",x)
def defect(M):
 G=M.conj().T@M;s=float(np.trace(G).real/2);return float(np.linalg.norm(G-s*I))
def dense(a01,b01,a12,b12):
 c=Circuit(3)
 c.rxx(0,1,a01);c.rzz(0,1,b01);c.cx(0,1)
 c.rxx(1,2,a12);c.rzz(1,2,b12);c.cx(1,2)
 s=[0j]*8;s[0]=1+0j
 for op in c.operations:s=_apply_gate_to_state(s,op,3)
 return float(sum(abs(x)**2*((-1)**i.bit_count()) for i,x in enumerate(s)))
rng=random.Random(31);rows=[]
for k in range(128):
 a01,b01,a12,b12=[rng.uniform(-math.pi,math.pi) for _ in range(4)]
 # eliminate q2 into q1, then q1 into q0. Pair convention: eliminated leaf is
 # MSB in eliminate(), so transpose pair ordering by SWAP where needed.
 M1=eliminate(Ublock(a12,b12),Z)
 M0=eliminate(Ublock(a01,b01),Z@M1)
 val=float(M0[0,0].real);ref=dense(a01,b01,a12,b12)
 rows.append({"case":k,"inner_defect":defect(M1),"outer_defect":defect(M0),"value":val,"reference":ref,"error":abs(val-ref)})
summary={"cases":len(rows),"inner_closed":sum(r["inner_defect"]<=1e-9 for r in rows),"outer_closed":sum(r["outer_defect"]<=1e-9 for r in rows),
"exact_cases":sum(r["error"]<=1e-9 for r in rows),"max_inner_defect":max(r["inner_defect"] for r in rows),"max_outer_defect":max(r["outer_defect"] for r in rows),"max_error":max(r["error"] for r in rows)}
Path("results").mkdir(exist_ok=True);Path("results/recursive_rotor.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2));print(json.dumps(summary))
