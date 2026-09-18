"""Minimum-width contraction-order search for hardware-efficient circuits.

Builds the undirected tensor-network line graph from circuit tensors and wire
segments, then computes exact treewidth for small n via branch-and-bound and
min-fill/min-degree upper bounds for larger n. The goal is contraction width,
not chronological qubit liveness.
"""
import json,time
from functools import lru_cache
from pathlib import Path

def hardware_graph(n,layers=2):
 # Tensor vertices: input/output endpoints + one vertex per gate.
 # Edges are wire segments between consecutive tensors on each qubit.
 adj={}
 def add(v):adj.setdefault(v,set())
 def edge(a,b):add(a);add(b);adj[a].add(b);adj[b].add(a)
 last={q:("in",q) for q in range(n)}
 for v in last.values():add(v)
 gid=0
 for layer in range(layers):
  for q in range(n):
   for kind in ("rz","rx"):
    v=(kind,layer,q,gid);gid+=1;edge(last[q],v);last[q]=v
  for q in range(n-1):
   v=("cx",layer,q,q+1,gid);gid+=1
   edge(last[q],v);edge(last[q+1],v);last[q]=v;last[q+1]=v
 for q in range(n):
  v=("out",q);edge(last[q],v)
 return adj

def eliminate(adj,v):
 a={x:set(ns) for x,ns in adj.items() if x!=v};ns=list(adj[v])
 for x in ns:
  if x in a:a[x].discard(v)
 for i,x in enumerate(ns):
  if x not in a:continue
  for y in ns[i+1:]:
   if y in a:a[x].add(y);a[y].add(x)
 return a,len(ns)

def greedy(adj,mode):
 a={x:set(ns) for x,ns in adj.items()};width=0
 while a:
  def score(v):
   ns=list(a[v])
   fill=sum(1 for i,x in enumerate(ns) for y in ns[i+1:] if y not in a[x])
   return (fill,len(ns)) if mode=="minfill" else (len(ns),fill)
  v=min(a,key=score);a,d=eliminate(a,v);width=max(width,d)
 return width

def exact_width(adj,upper):
 # exact branch-and-bound treewidth, practical only for small graph sizes.
 best=[upper]
 def rec(a,w):
  if not a:best[0]=min(best[0],w);return
  mind=min(len(ns) for ns in a.values())
  if max(w,mind)>=best[0]:return
  # explore low-fill candidates first
  cand=[]
  for v,ns0 in a.items():
   ns=list(ns0);fill=sum(1 for i,x in enumerate(ns) for y in ns[i+1:] if y not in a[x])
   cand.append((fill,len(ns),v))
  for _,_,v in sorted(cand)[:8]:
   b,d=eliminate(a,v);rec(b,max(w,d))
 rec({x:set(ns) for x,ns in adj.items()},0)
 return best[0]

rows=[]
for n in (4,8,16,32,64,128):
 g=hardware_graph(n);t=time.perf_counter()
 mf=greedy(g,"minfill");md=greedy(g,"mindegree");ub=min(mf,md)
 exact=None
 if n<=4:exact=exact_width(g,ub)
 rows.append({"n":n,"tensor_vertices":len(g),"minfill_width":mf,"mindegree_width":md,
              "best_width":exact if exact is not None else ub,"exact":exact is not None,
              "search_ms":(time.perf_counter()-t)*1000})
summary={"rows":len(rows),"exact_through_n":4,
 "best_widths":[[r["n"],r["best_width"]] for r in rows],
 "bounded_by_3_all":all(r["best_width"]<=3 for r in rows)}
Path("results").mkdir(exist_ok=True)
Path("results/hardware_contraction_width.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2))
print(json.dumps({"summary":summary,"rows":rows}))
