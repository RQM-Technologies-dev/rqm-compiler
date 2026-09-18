from rqm_compiler import (
 Circuit, QueryResult, RepresentationCompileResult,
 compile_representation_aware, evaluate_observable,
)

def chain(n=4):
 c=Circuit(n);c.h(0)
 for i in range(n-1):
  c.rxx(i,i+1,.11+.002*i);c.rzz(i,i+1,-.067-.001*i);c.cx(i,i+1)
 return c

def test_public_representation_compile_api():
 r=compile_representation_aware(chain())
 assert isinstance(r,RepresentationCompileResult)
 assert r.closure.minimum_closed_representation_size>0

def test_public_query_planner_api_selects_validated_route():
 r=evaluate_observable(chain(),"ZZZZ")
 assert isinstance(r,QueryResult)
 assert r.available and r.exact
 assert r.method=="chain_boundary_transfer"

def test_public_api_general_fallback_remains_available():
 c=Circuit(2);c.h(0);c.cx(0,1)
 r=evaluate_observable(c,"ZI")
 assert r.available and r.exact
