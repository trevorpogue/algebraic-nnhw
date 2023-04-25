from copy import deepcopy

import pytest

import sections
from sections import Section

from .test_doc_examples import test_docs_examples_details
from .test_doc_examples import test_docs_examples_usage
from .test_indepth_usage import test_indepth_usage
from .utils import assert_tree
from .utils import get_tree


def test_options_variations() -> None:
    Section.use_cache = False
    test_docs_examples_usage()
    test_docs_examples_details()
    test_indepth_usage()
    Section.use_cache = True
    test_docs_examples_usage()
    test_docs_examples_details()
    test_indepth_usage()


def test_speed() -> None:
    for i in range(250):
        test_docs_examples_usage()
        test_docs_examples_details()
    tree = sections(x=[4] * 20)
    for i in range(250000):
        # for i in tree('x', gettype=list):
        # for i in tree('x', gettype=dict):
        for i in tree('x', gettype='duplicates_'):
            # for i in tree('x', gettype=iter):
            # for i in x:
            i = 1
    c = 10
    x = [[[[4] * c]*c]*c]*c
    tree = sections(x=x, y=x)
    tree.x
    tree.xs
    tree.y
    tree.ys
    for i in range(1000):
        # for i in tree('x', gettype=iter):
        for i in tree('x', gettype=list):
            # for i in tree('x', gettype='s'):
            # for i in tree('x', gettype=dict):
            # for i in x:
            1


def test_SectionNoneType() -> None:
    from sections import SectionNone
    assert str(SectionNone) == 'sections'


def test_deep_leaf_instantiation() -> None:
    s = sections(x=[[[1], [2]]])
    assert s.x == [1, 2]
    assert s.nofchildren == 1
    assert s[0].nofchildren == 2
    assert s[0][0].nofchildren == 1
    assert s[0][0][0].nofchildren == 0
    assert s[0][1].nofchildren == 1
    assert s[0][1][0].nofchildren == 0


def test_instantiation_abuse() -> None:
    import sections as sect
    s = sect(
        'root',
        sect('child0'),
        sect('child1'),
        attr=(0, 1)
    )
    assert s.name == 'root'
    assert s.children.names == ['child0', 'child1']
    assert s['child0'].node.attr == 0
    assert s.attrs == [0, 1]
    s = sect(
        'root', (),
        sect('child0'),
        sect('child1'),
        attr=[0, 1]
    )
    assert s.name == 'root'
    assert s.children.names == ['child0', 'child1']
    assert s['child0'].node.attr == 0
    assert s.attrs == [0, 1]
    s = sect(
        'root',
        sect('child0'),
        attr=[0]
    )
    assert s.name == 'root'
    assert s.children.names == 'child0'
    assert s['child0'].node.attr == 0
    assert s.attrs == 0
    s = sect(
        'root',
        sect(sect('L0', L=0), sect('L1', L=1)),
        sect(sect('L2', L=2), sect('L3', L=3)),
        attr=[[0, 1], [2]]
    )
    assert s.name == 'root'
    assert s.leaves.names == ['L0', 'L1', 'L2', 'L3', ]
    assert s[0]['L0'].node.attr == 0
    assert s[0]['L1'].node.attr == 1
    assert s[1]['L2'].node.attr
    with pytest.raises(AttributeError):
        assert s[1]['L3'].node.attr
    assert s.attrs == list(range(3))
    s = sect(['r'])
    assert s[0]['r'].node.name == 'r'
    s = sect(
        'root', (), ['L0'], ['L1'], attrs=[[0], [1]]
    )
    assert s.name == 'root'
    assert s.leaves.names == ['L0', 'L1']
    assert s[0]['L0'].node.attr == 0
    assert s[1]['L1'].node.attr == 1
    assert s.attrs == list(range(2))
    s = sect(['leaf'], x=1, y=2)
    assert s[0]['leaf'].name == 'leaf'
    s = sect('arg name', name='attr name')
    assert s.name == 'attr name'
    s = sect('arg name', names='attr name')
    assert s.name == 'attr name'
    s = sections(sections('L'))
    assert s.name is sections.SectionNone
    assert s['L'].name == 'L'
    # INVALID: mixing section-wise with child names:
    # s = sect(
    #     'root', (), 'childx',
    #     sect(sect('L0', L=0), sect('L1', L=1)),
    #     sect(sect('L2', L=2), sect('L3', L=3)),
    #     attr=[[0, 1], [2, 3]]
    # )
    #
    # # TODO: maybe? but probably not necessary to support:
    # s = sect(
    #     'root', (),
    #     [sect('L0', L=0), sect('L1', L=1)],
    #     [sect('L2', L=2), sect('L3', L=3)],
    #     attr=[[0, 1], [2, 3]]
    # )
    # assert s.name == 'root'
    # assert s.leaves.names == ['L0', 'L1', 'L2', 'L3', ]
    # assert s[0]['L0'].node.attr == 0
    # assert s.attrs == list(range(4))
    # s = sect(
    #     'root',
    #     [sect('L0', L=0), sect('L1', L=1)],
    #     [sect('L2', L=2), sect('L3', L=3)],
    # )


def test_str() -> None:
    s1 = sections('a', 'b', attr=[0, 1])
    s2 = sections(sections('a', attr=0), sections('b', attr=1))
    assert s1.node_str() == s2.node_str()


def test_deepcopy() -> None:
    tree = get_tree()
    tree_copy = deepcopy(tree)
    tree = get_tree()
    assert str(tree) == str(tree_copy)
    assert_tree(tree)
    assert_tree(tree_copy)
