# RQM Compiler 0.3.7 candidate benchmark

Exactness gate: abs(error) <= 1e-9.

| Family | Coverage | Median end-to-end ratio | Max ratio | Route(s) |
| --- | ---: | ---: | ---: | --- |
| local | 3/3 | 1.970x | 3.828x | general_pauli_promoted |
| clifford | 3/3 | 1.318x | 1.814x | general_pauli_promoted |
| star | 3/3 | 1.589x | 1.728x | direct_star_relational |
| chain | 3/3 | 2.330x | 3.069x | chain_boundary_transfer |
| clifford_t | 3/3 | 1.544x | 2.471x | general_pauli_promoted |
| hardware_efficient | 3/3 | 0.607x | 0.996x | topology_hardware_1d |
| random_sparse | 3/3 | 0.606x | 1.382x | general_pauli_promoted |
