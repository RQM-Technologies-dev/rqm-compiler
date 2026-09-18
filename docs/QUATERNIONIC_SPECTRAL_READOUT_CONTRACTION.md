# Quaternionic-spectral Cartan contraction law

## Motivation from QSG

The QSG repository deliberately uses the standard embedding H -> M2(C), separates a nonzero quaternionic coordinate as Q = rho q with q in SU(2), and treats spectral/operator information separately from orientation. That suggests the boundary object in recursive readout should not be forced to remain a single rotor. The experiments confirm this: scalar x rotor is algebraically closed in the tested cases but loses correlation information.

## Exact boundary law

Let an edge unitary U act on a leaf/subtree boundary l and parent p. Let rho_l be the incoming leaf boundary state/weight and O_l the observable accumulated from the eliminated subtree. Define the boundary transfer map

T[U,rho_l,O_l](O_p)
  = Tr_l[(rho_l tensor I_p) U^dagger (O_l tensor O_p) U].

This is the exact object that must be composed. It preserves both the operator and the correlation weighting that the earlier rotor-only and one-relation experiments discarded.

For a chain l--p--r, elimination is therefore

O_p^(1) = T[U_lp,rho_l,O_l](O_p)

followed by

O_r^(2) = T[U_pr,rho_p,O_p^(1)](O_r).

Associativity follows from ordinary tensor contraction / partial trace, so recursive elimination is exact when the complete transfer map is retained.

## Quaternionic-spectral coordinates

Use sigma_0=I, sigma_1=X, sigma_2=Y, sigma_3=Z. Represent the transfer map by real/complex coefficients

T_{mu,nu} = (1/2) Tr[sigma_mu T(sigma_nu)].

The key point is semantic: this is not introduced as a generic dense 4x4 fallback. For an RQM edge, U is first kept in its least-general exact form:

local quaternion rotors
  + AxisHinge / Cartan kernel
  + local quaternion rotors.

The local rotors act as SO(3) frame changes on the vector part. The Cartan kernel

A(c)=exp[-i/2(c_x XX+c_y YY+c_z ZZ)]

contains the nonlocal spectral weights. Thus the transfer can be stored/factored as

T = R_L(q_L) * Lambda(c_x,c_y,c_z,rho_l,O_l) * R_R(q_R),

where R_L and R_R are quaternion-induced frame maps and Lambda is the small Cartan/spectral core. This mirrors QSG's separation of normalized SU(2) orientation from magnitude/spectral data.

The previous experiments show why Lambda cannot in general be collapsed to one scalar: doing so preserves conformal/rotor closure but loses query information.

## Composition law

For two eliminated subtrees whose exact boundary transfers are T1 and T2, the correct recursive law is simply

T_parent = T2 o T1.

In factored quaternionic-spectral coordinates:

R_L2 Lambda2 R_R2 R_L1 Lambda1 R_R1

= R_L2 [Lambda2 R(q_mid) Lambda1] R_R1,

where q_mid is the quaternion product corresponding to the adjacent frame rotations R_R2 R_L1.

The bracketed object is then minimized:

1. if proportional to a quaternion/SO(3) frame map, demote to rotor;
2. if it matches an AxisHinge spectral core, retain AxisHinge;
3. if diagonalizable in the commuting XX/YY/ZZ Cartan frame, retain Cartan spectral coordinates;
4. otherwise promote to the complete boundary transfer representation.

This gives readout its own closure-driven promotion/demotion rule.

## Why the earlier full-Cartan test failed

That test projected one two-qubit Heisenberg operator into {II,XX,YY,ZZ}; the projection was exact to machine precision. But it then contracted that operator as though its Cartan coefficients alone were the recursive message. The exact recursive object is a map O_p -> T(O_p), not one fixed operator T(Z). Knowing one image of the map does not determine how a later hinge acts on arbitrary boundary components.

Therefore the observed combination

Cartan projection residual ~ 1e-16
but readout error ~ 1

is expected: representation of the single operator was exact, while the correlation-preserving transfer law was incomplete.

## Next validity gate

Implement the factored transfer for the existing randomized 3-qubit chain and require:

- 128/128 exact global-parity values with abs error <= 1e-9;
- no Pauli-sum fallback;
- no global statevector in the candidate path;
- record quaternion frame coordinates, Cartan/spectral core rank, promotion level, and contraction count.

Only after that gate passes should chain/tree scaling be rerun.
