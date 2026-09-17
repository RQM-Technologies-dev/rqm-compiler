from rqm_compiler.adaptive import _classify_stage_exception


def test_unsupported_window_structure():
    assert _classify_stage_exception("window_unitary", ValueError("unsupported two-qubit operation foo")) == "unsupported_window_structure"
    assert _classify_stage_exception("window_unitary", ValueError("operation touches a qubit outside the candidate pair")) == "unsupported_window_structure"


def test_numerical_tolerance_failure():
    assert _classify_stage_exception("decompose", ValueError("reconstruction error exceeds tolerance")) == "numerical_tolerance_failure"
    assert _classify_stage_exception("decompose", ValueError("input is not unitary within tolerance")) == "numerical_tolerance_failure"


def test_decomposition_failure():
    assert _classify_stage_exception("decompose", ValueError("Cartan eigensystem could not be resolved")) == "decomposition_failure"


def test_equivalence_proof_failure():
    assert _classify_stage_exception("final_equivalence", ValueError("proof failed")) == "equivalence_proof_failure"


def test_implementation_defect():
    assert _classify_stage_exception("decompose", TypeError("unexpected API shape")) == "implementation_defect"
    assert _classify_stage_exception("window_unitary", RuntimeError("unexpected invariant")) == "implementation_defect"
