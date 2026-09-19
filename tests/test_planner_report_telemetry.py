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


def test_unavailable_query_retains_observed_expansion_and_resets_next_query():
 c=Circuit(4)
 for q in range(4): c.ry(q, .3)
 x=compile_representation_aware(c)
 result=plan_and_evaluate(x, "ZZZZ", max_terms=1, max_frontier_qubits=0)
 assert not result.available
 assert result.largest_intermediate > 1
 assert x.report.largest_intermediate == result.largest_intermediate
 assert x.report.largest_intermediate_unit == "pauli_terms"
 assert "max_terms=1" in x.report.query_fallback_reason
 result=plan_and_evaluate(x, "IIII", max_terms=1, max_frontier_qubits=0)
 assert result.available
 assert x.report.largest_intermediate == 1
 assert not x.report.query_fallback_reason
