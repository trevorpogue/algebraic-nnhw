"""Test node related methods and properties."""

import pytest

import sections


def test_descendants() -> None:
    s = sections(0, (), [1, (), 2, 3], [4, (), 5, 6])
    assert s[0].ischild
    assert s.descendants.names == list(range(7))
    assert s.flat.names == list(range(7))


def test_get_self_attr() -> None:
    sect = sections(0, (), 1, 2, x=[0, 1])
    assert sect.node('name') == 0
    assert sect.node.names == 0
    with pytest.raises(AttributeError):
        assert sect.node.x


def test_root() -> None:
    s = sections('r', (), 0, 1, [2, 3])
    assert s[0].root is s
    assert s[2][3].root is s
