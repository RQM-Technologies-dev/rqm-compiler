"""Tests for descriptor utilities and the canonical gate registry."""

import pytest

from rqm_compiler.descriptors import (
    SUPPORTED_GATES,
    SINGLE_QUBIT_GATES,
    PARAMETRIC_SINGLE_QUBIT_GATES,
    TWO_QUBIT_GATES,
    OTHER_GATES,
    make_descriptor,
    is_supported_gate,
)
from rqm_compiler.ops import Operation


# ---------------------------------------------------------------------------
# make_descriptor
# ---------------------------------------------------------------------------

def test_make_descriptor_basic():
    d = make_descriptor("rx", [0], params={"angle": 1.0})
    assert d == {"gate": "rx", "targets": [0], "controls": [], "params": {"angle": 1.0}}


def test_make_descriptor_lowercase():
    d = make_descriptor("RX", [0], params={"angle": 1.0})
    assert d["gate"] == "rx"


def test_make_descriptor_controls():
    d = make_descriptor("cx", [1], controls=[0])
    assert d["controls"] == [0]
    assert d["targets"] == [1]


def test_make_descriptor_defaults():
    d = make_descriptor("h", [0])
    assert d["controls"] == []
    assert d["params"] == {}


# ---------------------------------------------------------------------------
# is_supported_gate
# ---------------------------------------------------------------------------

def test_is_supported_gate_valid():
    for gate in SUPPORTED_GATES:
        assert is_supported_gate(gate)


def test_is_supported_gate_case_insensitive():
    assert is_supported_gate("H")
    assert is_supported_gate("RX")
    assert is_supported_gate("CX")


def test_is_supported_gate_unknown():
    assert not is_supported_gate("toffoli")
    assert not is_supported_gate("ccx")
    assert not is_supported_gate("")


# ---------------------------------------------------------------------------
# Gate set membership
# ---------------------------------------------------------------------------

def test_single_qubit_gates_subset_of_supported():
    assert SINGLE_QUBIT_GATES <= SUPPORTED_GATES


def test_parametric_single_qubit_gates_subset_of_supported():
    assert frozenset(PARAMETRIC_SINGLE_QUBIT_GATES) <= SUPPORTED_GATES


def test_two_qubit_gates_subset_of_supported():
    assert TWO_QUBIT_GATES <= SUPPORTED_GATES


def test_other_gates_subset_of_supported():
    assert OTHER_GATES <= SUPPORTED_GATES


def test_rx_ry_rz_phaseshift_in_parametric():
    for gate in ("rx", "ry", "rz", "phaseshift"):
        assert gate in PARAMETRIC_SINGLE_QUBIT_GATES


def test_u1q_in_parametric():
    assert "u1q" in PARAMETRIC_SINGLE_QUBIT_GATES


def test_u1q_required_params():
    assert set(PARAMETRIC_SINGLE_QUBIT_GATES["u1q"]) == {"w", "x", "y", "z"}


def test_u1q_in_supported_gates():
    assert "u1q" in SUPPORTED_GATES


def test_u1q_is_supported_gate():
    assert is_supported_gate("u1q")
    assert is_supported_gate("U1Q")


def test_cx_cy_cz_swap_iswap_in_two_qubit():
    for gate in ("cx", "cy", "cz", "swap", "iswap"):
        assert gate in TWO_QUBIT_GATES


# ---------------------------------------------------------------------------
# Operation ↔ descriptor roundtrip
# ---------------------------------------------------------------------------

def test_operation_to_descriptor():
    op = Operation(gate="h", targets=[0])
    d = op.to_descriptor()
    assert d["gate"] == "h"
    assert d["targets"] == [0]
    assert d["controls"] == []
    assert d["params"] == {}


def test_operation_from_descriptor_roundtrip():
    original = {"gate": "rx", "targets": [1], "controls": [], "params": {"angle": 0.5}}
    op = Operation.from_descriptor(original)
    assert op.to_descriptor() == original


def test_operation_gate_name_lowercased():
    op = Operation(gate="H", targets=[0])
    assert op.gate == "h"
