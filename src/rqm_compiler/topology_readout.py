"""Validated topology-aware exact readout for fixed-depth 1D hardware-efficient circuits."""
from __future__ import annotations
import numpy as np
from .circuit import Circuit
from .ops import Operation
from .su4_blocks import _operation_matrix,_single_qubit_matrix

Z=np.array([[1,0],[0,-1]],complex);ZERO=np.array([1,0],complex)

def recognize(c:Circuit)->int|None:
 n=c.num_qubits;ops=c.operations;idx=0;layers=0
 while idx<len(ops):
  # each validated layer: rz,rx on every q in order; then cx sweep 0->1...n-2->n-1
  for q in range(n):
   if idx+2>len(ops):return None
   a,b=ops[idx],ops[idx+1]
   if a.gate!="rz" or b.gate!="rx" or a.targets!=[q] or b.targets!=[q]:return None
   idx+=2
  for q in range(n-1):
   if idx>=len(ops):return None
   x=ops[idx]
   if x.gate!="cx" or x.controls!=[q] or x.targets!=[q+1]:return None
   idx+=1
  layers+=1
  if layers>4:return None
 return layers if 2<=layers<=4 else None

def global_z_hardware(c:Circuit):
 import opt_einsum as oe
 layers=recognize(c)
 if layers is None:return None
 n=c.num_qubits;tensors=[];inds=[];label=0;ket=[None]*n;bra=[None]*n
 for q in range(n):
  ket[q]=label;label+=1;tensors.append(ZERO);inds.append([ket[q]])
  bra[q]=label;label+=1;tensors.append(ZERO.conj());inds.append([bra[q]])
 for op in c.operations:
  touched=sorted(set(op.targets)|set(op.controls))
  if len(touched)==1:
   q=touched[0];U=_single_qubit_matrix(op);ko=label;label+=1;tensors.append(U);inds.append([ko,ket[q]]);ket[q]=ko
   bo=label;label+=1;tensors.append(U.conj());inds.append([bo,bra[q]]);bra[q]=bo
  else:
   a,b=touched;mp={a:0,b:1};loc=Operation(op.gate,[mp[x] for x in op.targets],[mp[x] for x in op.controls],op.params)
   U=_operation_matrix(loc,(0,1)).reshape(2,2,2,2).transpose(1,0,3,2)
   ka,kb=label,label+1;label+=2;tensors.append(U);inds.append([ka,kb,ket[a],ket[b]]);ket[a],ket[b]=ka,kb
   ba,bb=label,label+1;label+=2;tensors.append(U.conj());inds.append([ba,bb,bra[a],bra[b]]);bra[a],bra[b]=ba,bb
 for q in range(n):tensors.append(Z);inds.append([bra[q],ket[q]])
 args=[]
 for T,Ix in zip(tensors,inds):args.extend([T,Ix])
 args.append([])
 path,info=oe.contract_path(*args,optimize="greedy");v=oe.contract(*args,optimize=path)
 return complex(v),int(info.largest_intermediate),layers
