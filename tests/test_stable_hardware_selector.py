from rqm_compiler import Circuit
from rqm_compiler.stable_prototype import expectation_stable

def hw(n,layers=2):
 c=Circuit(n)
 for layer in range(layers):
  for q in range(n):
   c.rz(q,.021*(q+1)*(layer+1));c.rx(q,.017*(q+2)*(layer+1))
  for i in range(n-1):c.cx(i,i+1)
 return c

def test_validated_hardware_selects_topology_path():
 for n in (4,8,12):
  r=expectation_stable(hw(n,2),"Z"*n)
  assert r.available and r.method=="topology_hardware_1d"
def test_validated_depths_2_to_4():
 for d in (2,3,4):
  r=expectation_stable(hw(8,d),"Z"*8)
  assert r.available and r.method=="topology_hardware_1d"
def test_unvalidated_depth_falls_back():
 r=expectation_stable(hw(4,5),"Z"*4)
 assert r.method!="topology_hardware_1d"
