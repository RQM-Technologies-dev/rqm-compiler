"""Tests for circuit normalization."""

import pytest

from rqm_compiler import Circuit, Operation
from rqm_compiler.normalize import normalize_circuit, normalize_operation, normalize_descriptor


# ---------------------------------------------------------------------------
# normalize_operation
# ---------------------------------------------------------------------------

def test_normalize_gate_name_lowercased():
    op = Operation(gate="H", targets=[0])
    # Operation.__post_init__ already lowercases, but we test normalize_operation too
    norm = normalize_operation(op)
    assert norm.gate == "h"


def test_normalize_uppercase_gate_via_raw_dict():
    """Verify normalize_descriptor lowercases the gate."""
    raw = {"gate": "RX", "targets": [0], "controls": [], "params": {"angle": 1.0}}
    norm = normalize_descriptor(raw)
    assert norm["gate"] == "rx"


def test_normalize_operation_returns_new_object():
    op = Operation(gate="x", targets=[0])
    norm = normalize_operation(op)
    assert norm is not op


def test_normalize_operation_copies_lists():
    op = Operation(gate="cx", targets=[1], controls=[0])
    norm = normalize_operation(op)
    norm.targets.append(99)
    assert op.targets == [1]  # original unchanged


def test_normalize_operation_copies_params():
    op = Operation(gate="rx", targets=[0], params={"angle": 1.0})
    norm = normalize_operation(op)
    norm.params["angle"] = 99.0
    assert op.params["angle"] == 1.0  # original unchanged


# ---------------------------------------------------------------------------
# normalize_circuit
# ---------------------------------------------------------------------------

def test_normalize_circuit_returns_new_circuit():
    c = Circuit(2)
    c.h(0)
    normed = normalize_circuit(c)
    assert normed is not c


def test_normalize_circuit_preserves_ops():
    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    normed = normalize_circuit(c)
    assert len(normed) == 2
    assert normed.operations[0].gate == "h"
    assert normed.operations[1].gate == "cx"


def test_normalize_circuit_does_not_mutate_original():
    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    original_len = len(c)
    normalize_circuit(c)
    assert len(c) == original_len


# ---------------------------------------------------------------------------
# normalize_descriptor
# ---------------------------------------------------------------------------

def test_normalize_descriptor_fills_missing_fields():
    raw = {"gate": "H"}  # missing targets, controls, params
    norm = normalize_descriptor(raw)
    assert norm["gate"] == "h"
    assert norm["targets"] == []
    assert norm["controls"] == []
    assert norm["params"] == {}


def test_normalize_descriptor_is_copy():
    raw = {"gate": "x", "targets": [0], "controls": [], "params": {}}
    norm = normalize_descriptor(raw)
    norm["targets"].append(1)
    assert raw["targets"] == [0]
