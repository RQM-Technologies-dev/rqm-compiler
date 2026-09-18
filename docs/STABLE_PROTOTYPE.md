# Stable exact prototype

This module is the steady experimental base for RQM compiler benchmarking.

Included only because each mechanism has passed exact-reference validation in
its tested scope:

- verified compiler optimization pipeline;
- quaternion/local and structured two-qubit representation accounting;
- representation-owned C_R;
- exact structured observable propagation for supported operations;
- exact star/global-Z direct relational readout;
- exact map-valued one-qubit boundary transfer primitive.

Intentionally excluded:

- minimal QST parameterizations;
- rotor-only recursive readout;
- rotor + one-relation readout;
- fixed-operator Cartan recursive readout;
- naive 2x2 tree messages;
- any claim of general polynomial simulation.

Use this prototype as the control surface for future experiments. New features
should enter only after passing an independent <=1e-9 exactness gate and a
sub-10-minute acceptance workflow.
