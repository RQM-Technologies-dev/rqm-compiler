# CompilerReport 0.4

The report explains what the compiler did and why.

| Field | Meaning |
| --- | --- |
| `representation_complexity` | C_R, representation-owned complexity |
| `query_complexity` | C_Q/work units for selected query route |
| `maximum_representation_level` | highest representation level required |
| `representation_histogram` | representation ownership counts |
| `recognized_topology` | strict topology recognizer result |
| `selected_query_route` | exact readout/query algorithm selected |
| `contraction_width` | recorded boundary/contraction width when meaningful |
| `largest_intermediate` | largest recorded contraction intermediate |
| `promotion_count` | upward representation transitions |
| `query_fallback_used` | whether general exact query fallback was selected |
| `query_fallback_reason` | reason when available |
| `backend_capability_model` | target capability record selected |
| `backend_modality` | target computational modality |
| `backend_framework` | bridge/framework family |
| `backend_lowering_profile` | materialization profile |
| `backend_materializations` | RQM internal operations materialized |
| `backend_unsupported_operations` | unsupported operations found before lowering |

Null does not mean zero. It normally means that stage/measurement was not
requested or is not meaningful for the selected route.

Compiler semantic-equivalence evidence remains separate from query-route
telemetry.
