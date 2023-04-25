"""Test Section dict methods."""

import pytest

import sections

from .utils import assert_menu
from .utils import get_basic_menu


def test_setitem() -> None:
    menu = get_basic_menu()
    assert_menu(menu)
    menu['Dinner'] = dict(main='Burger', side='Fries')
    assert_menu(menu)
    menu['Lunch'] = dict(main='BLT', side='LunchFries')
    assert menu['Lunch'].main == 'BLT'
    assert menu['Lunch'].side == 'LunchFries'
    assert menu.mains == ['Bacon&Eggs', 'Burger', 'BLT']
    assert menu.sides == ['HashBrown', 'Fries', 'LunchFries']
    # test setting child to non-Section or dict value
    with pytest.raises(ValueError):
        menu['Lunch'] = 0


def test_iter_methods() -> None:
    menu = get_basic_menu()
    for i, name in enumerate(menu.keys()):
        assert menu.names[i] == name
    for child1, child2 in zip(menu.children, menu.values()):
        assert child1 is child2
    for name, child in menu.items():
        assert child is menu[name]
    # test Sections.__iter__
    menu = get_basic_menu()
    names = menu.names
    for section, name in zip(menu, names):
        assert section.name == name


def test_not_implemented() -> None:
    menu = get_basic_menu()
    with pytest.raises(NotImplementedError):
        menu.fromkeys(1, x=1)


def test_other_overrides() -> None:
    """"""
    s = sections(0, 1, 2)
    s.clear()
    assert s.nofchildren == 0
    s.update(sections(0, 1, 2))
    assert s.children.names == list(range(3))
    del s[1]
    assert s.children.names == [0, 2]
    assert s.get(0).name == 0
    s.setdefault(0, sections('0'))
    assert s.get(0).name == 0
    assert s.setdefault(3, sections(attr='3')).name == 3
    assert s.get(3).attr == '3'
    assert s.get(4, 'invalid key') == 'invalid key'
    s.move_to_end(0)
    s.move_to_end(3, False)
    assert s.children.names == [3, 2, 0]
    s.insertitem(0, 4, sections(attr='4'))
    assert s.children.names == [4, 3, 2, 0]
    s.insertitem(-1, 5, sections())
    assert s.children.names == [4, 3, 2, 0, 5]
    s.insert(0, sections('s'))
    assert s.children.names == ['s', 4, 3, 2, 0, 5]
    s.insert(2, sections('s2'))
    assert s.children.names == ['s', 4, 's2', 3, 2, 0, 5]
    # test __getitem_from_index
    assert s[1].name == 4
    # test default attr names
    assert s.children() == ['s', 4, 's2', 3, 2, 0, 5]
    assert s.pop(1)() == 4
    assert s.pop('s2')() == 's2'
    assert s.children() == ['s', 3, 2, 0, 5]
    with pytest.raises(IndexError):
        s.pop(7)


def test_pop_methods() -> None:
    s0 = sections(x=[0, 1])
    s0.pop(0)
    assert s0.x == 1
    s0 = sections(x=[0, 1])
    s0.popitem()
    assert s0.x == 0


def test_bool_eq_ne() -> None:
    s0 = sections(x=[0, 1])
    s1 = sections(x=[0, 1])
    assert s0
    assert s0 != s1
    assert s0 == s0
    assert s0.x == [0, 1]
    d = {s0: 0}
    for k in d:
        assert k is s0


def test_getitem():
    # test multi-get item
    x = list(range(4))
    s = sections(*x)
    s2 = s[1, 2]
    assert s2.names == [1, 2]
    # test leaves getitem
    s = sections(*x)
    assert s.leaves[0].name == 0
    # test getting non-existent key
    with pytest.raises(KeyError):
        assert s['non-existent-key']
