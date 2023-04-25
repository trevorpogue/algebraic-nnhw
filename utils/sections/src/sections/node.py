from collections import OrderedDict
from itertools import chain
from itertools import repeat

from .types import SectionType


class SectionNode:
    """Generic tree-structure node-related logic."""

    @ property
    def nofchildren(self) -> int:
        """Nunber of children Sections/nodes."""
        return len(self)

    @ property
    def isroot(self, ) -> bool:
        """True iff self node has no parent."""
        return self.parent is None

    @ property
    def ischild(self, ) -> bool:
        """True iff self node has a parent."""
        return self.parent is not None

    @ property
    def isparent(self, ) -> bool:
        """True iff self node has any children."""
        return self.nofchildren > 0

    @ property
    def isleaf(self, ) -> bool:
        """True iff self node has no children."""
        return self.nofchildren == 0

    @ property
    def root(self) -> SectionType:
        """Return root of self."""
        node = self
        while node.parent:
            node = node.parent
        return node

    @ property
    def children(self) -> SectionType:
        """
        Get self nodes's children. Returns a Section node that has no public
        attrs and has shallow copies of self node's children as its children.
        This can be useful if self has an attr `attr` but you want to access a
        list of the childrens' attr `attr`, then write section.children.attr to
        access the attr list.
        """
        return self.node_withchildren_fromiter(self.values())

    def node_withchildren_fromiter(
            self, itr: iter
    ) -> SectionType:
        """
        Perform a general form of the task performed in
        :meth:`leaves <Section.leaves>`. Return a Section node with any
        children referenced in the iterable from the `itr` argument.
        """
        root = self.cls()
        root._SectionDict__children_by_name = {}
        for node in itr:
            OrderedDict.__setitem__(root, node, node)
            name = node._SectionStringParser__name
            root._SectionDict__children_by_name[name] = node
        delattr(root, 'name')
        return root

    @ property
    def node(self) -> SectionType:
        """
        Return a shallow copy of self with no children. Useful for searching
        for attributes only in self.
        """
        import sections
        node = sections()
        node.__dict__ = self.__dict__
        for attr in self._setattr_invalidate_cache_excludes:
            setattr(node, attr, getattr(self, attr))
        return node

    @ property
    def leaves_iter(self) -> iter:
        """
        Return iterator that iterates through all self's leaf node descendants.
        """
        return (chain(*(child.leaves_iter for child in self.values()))
                if self.isparent else repeat(self, 1))

    @ property
    def descendants_iter(self) -> iter:
        """
        Return iterator that iterates through self and all self's descendants.
        """
        return (
            chain(repeat(self, 1),
                  *(child.descendants_iter for child in self.values()))
            if self.isparent else repeat(self, 1))

    @ property
    def descendants(self) -> SectionType:
        """
        Similar to :meth:`leaves <Section.leaves>` except all nodes in
        structure are returned.
        """
        return self.node_withchildren_fromiter(
            self.descendants_iter)

    @ property
    def flat(self) -> SectionType:
        """
        Synonym for :meth:`descendants <Section.descendants>`.
        """
        return self.node_withchildren_fromiter(
            self.descendants_iter)

    @ property
    def leaves(self) -> SectionType:
        """
        Get all leaf node descendants of self. Returns a Section node that has
        no public attrs and has shallow copies of self node's leaves as its
        children. This can be useful if self has an attr `attr` but you want to
        access a list of the leaves' attr `attr`, then write
        section.leaves.attr to access the leaf attr list.
        """
        return self.node_withchildren_fromiter(self.leaves_iter)
