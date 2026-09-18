from rqm_compiler import Circuit
from rqm_compiler.stable_prototype import expectation_stable

def _chain(n):
 c=Circuit(n);c.h(0)
 for i in range(n-1):
  c.rxx(i,i+1,.11+.002*i);c.rzz(i,i+1,-.067-.001*i);c.cx(i,i+1)
 return c

def test_validated_chain_selects_boundary_transfer():
 for n in (4,8,12):
  r=expectation_stable(_chain(n),"Z"*n)
  assert r.available
  assert r.method=="chain_boundary_transfer"
  assert r.work_units==n-1
