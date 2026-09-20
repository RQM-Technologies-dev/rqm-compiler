"""Optional dependency detection is cached; composition semantics are not."""
import builtins
import importlib
from types import SimpleNamespace

import pytest

module = importlib.import_module('rqm_compiler.passes.cancel_2q')


@pytest.fixture(autouse=True)
def clear_api_cache():
    module._relational_api.cache_clear()
    yield
    module._relational_api.cache_clear()


def install_import(monkeypatch, result):
    original = builtins.__import__
    calls = []

    def importing(name, *args, **kwargs):
        if name == 'rqm_entanglement':
            calls.append(name)
            if isinstance(result, Exception):
                raise result
            return result
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', importing)
    return calls


@pytest.mark.parametrize('missing', [ImportError('missing'), AttributeError('missing'), SimpleNamespace()])
def test_missing_api_resolved_once_with_coordinate_fallback(monkeypatch, missing):
    calls = install_import(monkeypatch, missing)
    for _ in range(3):
        assert module._compose_coordinates((1., 2., 3.), 'rxx', .5) == (1.5, 2., 3.)
        assert module._compose_coordinates((1., 2., 3.), 'ryy', -.5) == (1., 1.5, 3.)
        assert module._compose_coordinates((1., 2., 3.), 'rzz', -3.) == (1., 2., 0.)
    assert len(calls) == 1


class Cartan:
    def __init__(self, c1, c2, c3):
        self.c1, self.c2, self.c3 = c1, c2, c3


class Axis:
    def __init__(self, axis, angle):
        self.axis, self.angle = axis, angle

    def promote(self):
        values = [0., 0., 0.]
        values[{'xx': 0, 'yy': 1, 'zz': 2}[self.axis]] = self.angle
        return Cartan(*values)


@pytest.mark.parametrize('promote', [False, True])
def test_available_api_resolved_once_but_composed_each_time(monkeypatch, promote):
    compositions = []

    def compose(relation, hinge):
        compositions.append((relation, hinge))
        return hinge if promote else Cartan(4., 5., 6.)

    calls = install_import(monkeypatch, SimpleNamespace(
        AxisHinge=Axis, CartanRelation=Cartan, compose_relations=compose))
    for angle in (.25, .75):
        expected = (0., angle, 0.) if promote else (4., 5., 6.)
        assert module._compose_coordinates((1., 2., 3.), 'ryy', angle) == expected
    assert len(calls) == 1
    assert len(compositions) == 2


@pytest.mark.parametrize('failure', [ImportError, AttributeError, None])
def test_composition_failure_keeps_fallback_and_cached_api(monkeypatch, failure):
    compositions = []

    def compose(*args):
        compositions.append(args)
        if failure:
            raise failure('optional runtime failure')
        return object()

    calls = install_import(monkeypatch, SimpleNamespace(
        AxisHinge=Axis, CartanRelation=Cartan, compose_relations=compose))
    for _ in range(2):
        assert module._compose_coordinates((1., 2., 3.), 'rxx', .5) == (1.5, 2., 3.)
    assert len(calls) == 1
    assert len(compositions) == 2


def test_unexpected_composition_error_is_not_hidden(monkeypatch):
    def compose(*args):
        raise ValueError('unexpected')

    install_import(monkeypatch, SimpleNamespace(
        AxisHinge=Axis, CartanRelation=Cartan, compose_relations=compose))
    with pytest.raises(ValueError, match='unexpected'):
        module._compose_coordinates((0., 0., 0.), 'rxx', .5)
