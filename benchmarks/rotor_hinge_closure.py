"""Closure diagnostic for RQM-native rotor+hinge boundary messages.

Question: after eliminating one qubit from a 2Q AxisHinge/Cartan block, is the
induced boundary object representable as a unitary quaternion rotor (possibly
times a scalar), or does it require a non-unitary channel degree of freedom?
No Pauli expansion is used. Dense matrices are only the n=2/3 exact judge.
"""
import json,math,random
from pathlib import Path
import numpy as np
from rqm_compiler import Circuit
from rqm_compiler.su4_blocks import _operation_matrix
from rqm_compiler.ops import Operation

ZERO=np.array([[1,0],[0,0]],complex); Z=np.array([[1,0],[0,-1]],complex)

def block(theta,phi):
 c=Circuit(2);c.rxx(0,1,theta);c.rzz(0,1,phi);c.cx(0,1)
 U=np.eye(4,dtype=complex)
 for op in c.operations:U=_operation_matrix(op,(0,1))@U
 return U

def boundary(U,O=Z):
 # exact Heisenberg boundary operator after contracting leaf input |0>
 A=U.conj().T@np.kron(O,np.eye(2))@U
 B=np.kron(ZERO,np.eye(2))@A
 x=B.reshape(2,2,2,2)
 return np.einsum("abad->bd",x)

def rotor_fit(M):
 # A scalar times a unitary quaternion/SU2 object must satisfy M†M=s²I.
 G=M.conj().T@M;s2=float(np.trace(G).real/2)
 defect=float(np.linalg.norm(G-s2*np.eye(2)))
 det=complex(np.linalg.det(M))
 return defect,s2,det

rows=[]
rng=random.Random(29)
for i in range(64):
 th=rng.uniform(-math.pi,math.pi);ph=rng.uniform(-math.pi,math.pi)
 M=boundary(block(th,ph));defect,s2,det=rotor_fit(M)
 rows.append({"case":i,"theta":th,"phi":ph,"rotor_defect":defect,"norm2":s2,"det_real":det.real,"det_imag":det.imag})
summary={"cases":len(rows),"max_rotor_defect":max(r["rotor_defect"] for r in rows),
"median_rotor_defect":float(np.median([r["rotor_defect"] for r in rows])),
"rotor_closed_cases":sum(r["rotor_defect"]<=1e-9 for r in rows)}
Path("results").mkdir(exist_ok=True);Path("results/rotor_hinge_closure.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2));print(json.dumps(summary))
