"""
Test a more in-depth usage of making and modifying a deeper structure and make
sure the attribute searches return the correct results after each change. This
is especially to confirm that the attribute cache feature is working.
"""

from typing import Any

import pytest

import sections
from sections import Section


def test_indepth_usage() -> None:
    """Make sure cache feature works correctly as structure is modified."""
    s = sections(
        y=[['0', '1'], ['2', '3']],
        z=[['0', '1'], ['2', '3']],
    )
    assert_leaf_var(s, 'y')
    assert_leaf_var(s, 'z')
    s.x = [['0', '1'], ['2', '3']]
    assert_no_mod(s, 'x')
    s[0].x = [0, 1]
    assert_L01_mod(s, 'x')
    s[1].x = [2, 3]
    assert_L0123_mod(s, 'x')
    s[1].x = ['2', '3']
    assert_L01_mod(s, 'x')
    s[0].x = ['0', '1']
    assert_no_mod(s, 'x')


def assert_leaf_var(s: Section, attr: Any) -> None:
    """Modify node attrs then set them back, check correctness at each step."""
    # Start modifying node attributes
    setattr(s[0][0], attr, 0)
    assert_L0_mod(s, attr)
    setattr(s[0], attr, 10)
    assert_c0_L0_mod(s, attr)
    setattr(s[1][1], attr, 3)
    assert_c0_L03_mod(s, attr)
    setattr(s[1], attr, 20)
    assert_c01_L03_mod(s, attr)

    # Start setting the structure back to its original state
    delattr(s[1], attr)
    assert_c0_L03_mod(s, attr)
    setattr(s[1][1], attr, '3')
    assert_c0_L0_mod(s, attr)
    delattr(s[0], attr)
    assert_L0_mod(s, attr)
    setattr(s[0][0], attr, '0')
    assert_no_mod(s, attr)


def assert_no_mod(s: Section, attr: Any) -> None:
    """Assert original structure state."""
    assert s(attr) == ['0', '1', '2', '3']
    assert s.leaves(attr) == ['0', '1', '2', '3']
    assert s.children(attr) == ['0', '1', '2', '3']


def assert_L0_mod(s: Section, attr: Any) -> None:
    """Assert after only leaf0 has a modification."""
    assert s(attr) == [0, '1', '2', '3']
    assert s.children(attr) == [0, '1', '2', '3']
    assert s.leaves(attr) == [0, '1', '2', '3']
    assert s[0](attr) == [0, '1']
    assert s[0].children(attr) == [0, '1']
    assert s[0].leaves(attr) == [0, '1']
    assert s[0][0](attr) == 0
    with pytest.raises(AttributeError):
        s[0][0].children(attr)


def assert_L01_mod(s: Section, attr: Any) -> None:
    """Assert after only leaf0 has a modification."""
    assert s(attr) == [0, 1, '2', '3']
    assert s.children(attr) == [0, 1, '2', '3']
    assert s.leaves(attr) == [0, 1, '2', '3']
    assert s[0](attr) == [0, 1]
    assert s[0].children(attr) == [0, 1]
    assert s[0].leaves(attr) == [0, 1]
    assert s[0][0](attr) == 0
    with pytest.raises(AttributeError):
        s[0][0].children(attr)


def assert_L0123_mod(s: Section, attr: Any) -> None:
    """Assert after only leaf0 has a modification."""
    assert s(attr) == [0, 1, 2, 3]
    assert s.children(attr) == [0, 1, 2, 3]
    assert s.leaves(attr) == [0, 1, 2, 3]
    assert s[0](attr) == [0, 1]
    assert s[0].children(attr) == [0, 1]
    assert s[0].leaves(attr) == [0, 1]
    assert s[0][0](attr) == 0
    assert s[1](attr) == [2, 3]
    assert s[1].children(attr) == [2, 3]
    assert s[1].leaves(attr) == [2, 3]
    assert s[1][1](attr) == 3
    with pytest.raises(AttributeError):
        s[0][0].children(attr)
    with pytest.raises(AttributeError):
        s[1][1].children(attr)


def assert_c0_L0_mod(s: Section, attr: Any) -> None:
    """Assert after child0, leaf0 have a modification."""
    assert s(attr) == [10, '2', '3']
    assert s.children(attr) == [10, '2', '3']
    assert s.leaves(attr) == [0, '1', '2', '3']
    assert s[0](attr) == 10
    assert s[0].leaves(attr) == [0, '1']
    assert s[0][0](attr) == 0


def assert_c0_L03_mod(s: Section, attr: Any) -> None:
    """Assert after child0, leaf0, leaf3 have a modification."""
    assert s(attr) == [10, '2', 3]
    assert s.children(attr) == [10, '2', 3]
    assert s.leaves(attr) == [0, '1', '2', 3]
    assert s[1](attr) == ['2', 3]
    assert s[1].children(attr) == ['2', 3]
    assert s[1].leaves(attr) == ['2', 3]
    assert s[1][1](attr) == 3
    with pytest.raises(AttributeError):
        s[1][1].children(attr)


def assert_c01_L03_mod(s: Section, attr: Any) -> None:
    """Assert after child0, child1, leaf0, leaf3 have a modification."""
    assert s(attr) == [10, 20]
    assert s.children(attr) == [10, 20]
    assert s.leaves(attr) == [0, '1', '2', 3]
    assert s[1](attr) == 20
    assert s[1].leaves(attr) == ['2', 3]
    assert s[1][1](attr) == 3
