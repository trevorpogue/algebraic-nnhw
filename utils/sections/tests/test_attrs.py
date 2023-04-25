"""Test structure attribute searching, getting, and setting."""

import pytest

import sections

from .utils import assert_menu
from .utils import assert_tree


def func_for_property_test() -> str:
    return 'name'


def test_name_abuse() -> None:
    # test name overloading
    menu = sections(
        'skipped name 1', 'skipped name 2',
        # test that names kwd will take priority for names over the args
        name=['priority name 1', 'priority name 2'],
    )
    assert menu.names == ['priority name 1', 'priority name 2']
    menu = sections(
        'skipped name 1', 'skipped name 2',
        # test that names kwd will take priority for names over the args
        main=['Bacon&Eggs', 'Burger'],
        sides=['HashBrown', 'Fries'],
        names=['Breakfast', 'Dinner'],
    )
    assert_menu(menu)
    # test corner case setting names to property or callable (invalid values)
    menu = sections(
        name=property(func_for_property_test),
        mains=['Bacon&Eggs', 'Burger'],
        sides=['HashBrown', 'Fries'],
    )
    assert func_for_property_test() == 'name'
    assert menu.names == [0, 1]


def test_attr_abuse() -> None:
    # test setting uneven attrs
    menu = sections(
        'Breakfast', 'Dinner',
        mains=['Bacon&Eggs', 'Burger'],
        sides=['HashBrown'],
    )
    assert menu.mains == ['Bacon&Eggs', 'Burger']
    assert menu.sides == 'HashBrown'
    # test getting non-existent attribute
    with pytest.raises(AttributeError):
        menu.non_existent_attr


def test_cls_attrs() -> None:
    # test that updating a class attr will been seen in all nodes
    s = sections()
    s[0] = sections()
    s[0].cls.default_gettype = dict
    assert s.default_gettype == dict
    s[0] = s.cls()
    s[0].cls.default_gettype = dict
    assert s.default_gettype == dict
    s[0].default_gettype = dict
    assert s.default_gettype == dict
    s = sections()
    s[0] = sections()
    s.cls.default_gettype = dict
    assert s[0].default_gettype == dict
    sections.Section.default_gettype = dict
    s = sections([0, 1])
    assert s.cls.default_gettype == dict
    sections.Section.default_gettype = list
    s = sections([0, 1], x=[0, (), 1, 2])
    assert s.x == 0
    s1 = sections()
    s[0].cls.default_gettype = dict
    assert s.default_gettype == dict
    assert s1.default_gettype == list
    sections.Section.default_gettype = 'hybrid'  # set back to default value


def test_gettypes() -> None:
    names = [
        'root', (),
        ['child0', (), 'leaf0', 'leaf1'],
        ['child1', (), 'leaf2', 'leaf3'],
    ]
    attrs = dict(nodename=['root', (),
                           ['child0', (), 'leaf0', 'leaf1'],
                           ['child1', (), 'leaf2', 'leaf3']])
    tree = sections(*names, **attrs)
    assert tree['child0'].node.name == 'child0'
    assert_tree(tree)
    tree = sections(
        *names,
        nodenames=['root', (),
                   ['child0', (), 'leaf0', 'leaf1'],
                   ['child1', (), 'leaf2', 'leaf3']]
    )
    assert_tree(tree)
    tree = sections(
        *names,
        x=[[0, 1], [2, 3]],
        y=[0, 1]
    )
    assert tree('x', gettype=dict) == {
        'leaf0': 0, 'leaf1': 1, 'leaf2': 2, 'leaf3': 3
    }
    assert tree('y', gettype=dict) == {'child0': 0, 'child1': 1}
    assert tree('name', gettype=dict) == {'root': 'root'}
    for yvalue, yiter in zip([tree.name], tree('name', gettype=iter)):
        assert yvalue == yiter
    for value, iter_ in zip(tree.y, tree('y', gettype=iter)):
        assert value == iter_
    for value, iter_ in zip(tree.x, tree('x', gettype=iter)):
        assert value == iter_


def test_getattr_delattr() -> None:
    x = list(range(4))
    # test getitem from _SectionDict__children_by_name
    s = sections(*x, x=x)
    assert s.leaves[0].x == 0
    # test use_nearest
    s = sections(x=x, zs=x)
    # coverage for checking cache plural singular
    s = sections(x=x, zs=x)
    assert s.xs == x
    assert s.xs == x
    assert s.z == x
    assert s.z == x
    # test getattr
    sections.Section.use_pluralsingular = False
    x = [1]
    s = sections(x=x)
    assert getattr(s, 'x') == 1
    delattr(s[0], 'x')
    delattr(s[0], 'y')
    assert getattr(s, 'x', 0) == 0
    sections.Section.use_pluralsingular = True
    s = sections(cat=x, dogs=x)
    assert getattr(s, 'cat') == 1
    assert getattr(s, 'cats') == 1
    assert getattr(s, 'dog') == 1
    assert getattr(s, 'dogs') == 1
    delattr(s[0], 'cats')
    delattr(s[0], 'dog')
    assert getattr(s, 'cats', 0) == 0
    assert getattr(s, 'dog', 0) == 0
    assert s('turtle', default=0) == 0
    assert getattr(s, 'turtle', 0) == 0


def test_use_pluralsingular() -> None:
    s = sections(0, 1)
    s.cls.use_pluralsingular = False
    with pytest.raises(AttributeError):
        s[0].names
    sect = sections(0, (), 1, 2, x=[0, 1])
    assert sect.name == 0
    assert sect.names == 0
    assert sect[1].name == 1
    assert sect[1].names == 1
    assert sect.node('name') == 0
    assert sect.node('names') == 0

    sections.Section.use_pluralsingular = False  # turn off for all structures
    sect = sections(0, (), 1, 2)
    assert sect.name == 0
    with pytest.raises(AttributeError):
        sect.names
    assert sect[1].name == 1
    with pytest.raises(AttributeError):
        sect[1].names
    sections.Section.use_pluralsingular = True  # set back


def test_hasattr() -> None:
    s = sections(x=[1, 2])
    assert hasattr(s, 'x')
    assert hasattr(s[0], 'x')
    assert hasattr(s[1], 'x')
    assert not hasattr(s, 'y')
    assert not hasattr(s[0], 'y')
    assert not hasattr(s[1], 'y')
