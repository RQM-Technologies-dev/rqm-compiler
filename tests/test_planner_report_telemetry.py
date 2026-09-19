from rqm_compiler import Circuit,compile_representation_aware,plan_and_evaluate

def chain(n=4):
 c=Circuit(n);c.h(0)
 for i in range(n-1):
  c.rxx(i,i+1,.11);c.rzz(i,i+1,-.067);c.cx(i,i+1)
 return c

def hw(n=4):
 c=Circuit(n)
 for layer in range(2):
  for q in range(n):c.rz(q,.021*(q+1)*(layer+1));c.rx(q,.017*(q+2)*(layer+1))
  for i in range(n-1):c.cx(i,i+1)
 return c

def test_report_contains_representation_and_chain_query_telemetry():
 x=compile_representation_aware(chain());r=plan_and_evaluate(x,"Z"*4);d=x.report.to_dict()
 assert r.available
 assert d["representation_complexity"]==x.closure.minimum_closed_representation_size
 assert d["query_complexity"]==3
 assert d["recognized_topology"]=="chain"
 assert d["selected_query_route"]=="chain_boundary_transfer"
 assert d["contraction_width"]==1
 assert d["query_fallback_used"] is False
 assert isinstance(d["promotion_count"],int)

def test_report_contains_hardware_contraction_metrics():
 x=compile_representation_aware(hw());r=plan_and_evaluate(x,"ZZZZ");d=x.report.to_dict()
 assert r.method=="topology_hardware_1d"
 assert d["recognized_topology"]=="hardware_efficient_1d"
 assert d["contraction_width"] is None
 assert d["query_complexity_unit"]=="complex_tensor_entries"
 assert d["largest_intermediate"]==16
