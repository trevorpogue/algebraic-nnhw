import sections
from sections import Section


def get_tree() -> None:
    names = [
        'root', (),
        ['child0', (), 'leaf0', 'leaf1'],
        ['child1', (), 'leaf2', 'leaf3'],
    ]
    attrs = dict(nodename=['root', (),
                           ['child0', (), 'leaf0', 'leaf1'],
                           ['child1', (), 'leaf2', 'leaf3']])
    tree = sections(*names, **attrs)
    return tree


def assert_tree(tree) -> None:
    assert tree.nodename == 'root'
    assert tree['child0'].nodename == 'child0'
    assert tree['child0'].children.nodenames == ['leaf0', 'leaf1']
    assert tree['child1'].children.nodenames == ['leaf2', 'leaf3']


def assert_menu(menu: Section) -> None:
    assert menu.names == ['Breakfast', 'Dinner']
    assert menu.sections.names == ['Breakfast', 'Dinner']
    assert menu.children.names == ['Breakfast', 'Dinner']
    assert menu.leaves.names == ['Breakfast', 'Dinner']
    assert menu.entries.names == ['Breakfast', 'Dinner']
    assert menu.mains == ['Bacon&Eggs', 'Burger']
    assert menu.sides == ['HashBrown', 'Fries']
    assert menu['Breakfast'].main == 'Bacon&Eggs'
    assert menu['Breakfast'].side == 'HashBrown'
    assert menu['Dinner'].main == 'Burger'
    assert menu['Dinner'].side == 'Fries'
    assert isinstance(menu, sections.Section)
    assert isinstance(menu['Breakfast'], sections.Section)
    assert isinstance(menu['Dinner'], sections.Section)


def get_basic_menu() -> Section:
    return sections(
        'Breakfast', 'Dinner',
        mains=['Bacon&Eggs', 'Burger'],
        sides=['HashBrown', 'Fries'],
    )
