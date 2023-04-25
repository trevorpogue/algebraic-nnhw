"""
Flexible tree data structures for organizing lists and dicts into sections.

https://github.com/trevorpogue/sections
"""

from typing import Any
from typing import List
from typing import Type
from typing import Union

from . import MetaSection
from .attr_parser import SectionAttrParser
from .dict import SectionDict
from .node import SectionNode
from .string_parser import SectionStringParser
from .types import GetType
from .types import SectionAttrs
from .types import SectionNone
from .types import SectionType


class Section(SectionNode, SectionDict, SectionAttrParser, SectionStringParser,
              metaclass=MetaSection):
    """
    Objects instantiated by :class:`Section <Section>` are nodes in a sections
    tree structure. Each node has useful methods and properties for organizing
    lists/dicts into sections and for conveniently accessing/modifying the
    sub-list/dicts from each section/subsection.
    """

    ##########################################################################
    #              tree-structure-wide attributes for every node             #

    # class attributes act as tree-structure-wide attributes across all nodes.
    # This is possible because each sections() module call returns a unique
    # copy of the Section class, giving each individual structure its own class

    # Choose whether to use a cache in each node. The cache contains
    # quickly-readable references to attribute iterables parsed from manually
    # traversing through descendant nodes in a previous read. The caches are
    # invalidated when the tree structure or node attribute values change.
    # Using the cache can often make structure attribute reading faster by 5x
    # and even much more. The downside is that it also increases memory used by
    # roughly 5x as well. This is not a concern on a general-purpose computer
    # for structures containing less than 1000 nodes or 10,000 nodes, although
    # further testing is required to confirm this. After 10,000 nodes, it may
    # be recommended to turn the structure class attribute `use_cache` to
    # False.
    use_cache = True

    # See method Section.get_nearest_attr's doctring for a full description of
    # gettype and their default value. 'hybrid' returns a list if more
    # than 1 element is found, else return the non-iterable raw form of the
    # element
    default_gettype = 'hybrid'

    default_attr = 'names'
    list_attr_prefix = '_'
    # See https://sections.readthedocs.io/ for usage:
    use_pluralsingular = True
    ##########################################################################
    __private_prefix = '_Section'
    __getattribute_enable = False

    def __init__(self, **kwds: SectionAttrs) -> None:
        """Set object attr for every attr in kwds and init attr cache."""
        SectionAttrParser.__init__(self)
        self._SectionAttrParser__cache = {}
        for name, value in kwds.items():
            self.__setattr__(name, value, _invalidate_cache=False)
        self.cls.__getattribute_enable = True

    # def __getattribute__(self, name: str) -> Any:
    #     if ((name.startswith('_Section') or name.startswith('__')
    #             or ['cls'].count(name))):
    #         return object.__getattribute__(self, name)
    #     cls = object.__getattribute__(self, 'cls')
    #     cls_attr = getattr(cls, name, SectionNone)
    #     if (cls_attr is not SectionNone):
    #         return object.__getattribute__(self, name)
    #     # if cls._SectionAttrParser__user_attrs.get(name) is None:
    #         # return object.__getattribute__(self, name)
    #     # else:
    #     enable = cls.__getattribute_enable
    #     if enable:
    #         cls.__getattribute_enable = False
    #         try:
    #             value = cls.__call__(self, name)
    #             cls.__getattribute_enable = True
    #             return value
    #         except AttributeError:
    #             cls.__getattribute_enable = True
    #             raise AttributeError
    #     # elif enable == 'meta':
    #     else:
    #         return object.__getattribute__(self, name)
    #         # return SectionNone

    # def post_init(self) -> None:
        # """Called after nodes children (if any) have been constructed."""
        # pass

    @ property
    def cls(self) -> Type[SectionType]:
        """The unique structure-wide class of each node."""
        return self.__class__

    @ property
    def sections(self) -> SectionType:
        """A synonym for property :meth:`children <Section.children>`."""
        return self.children

    @ property
    def entries(self) -> SectionType:
        """A synonym for property :meth:`leaves <Section.leaves>`."""
        return self.leaves

    def structure_change(self):
        """
        Will be called every time there is a change in structure, i.e. whenever
        a node is added or removed or rearranged in child order. Meant for use
        when overriding.
        """
        pass

    def __call__(
            self,
            name: str = SectionNone,
            gettype: GetType = 'default',
            default: Any = SectionNone,
    ) -> Union[Any, List[Any]]:
        """
        Run :meth:`get_nearest_attr <Section.get_nearest_attr>`. This
        returns attribute `name` from self if self contains the attribute in
        either the singular or plural form for `name`. Else, try the same
        pattern for each of self's children, putting the returned results from
        each child into a list. Else, raise AttributeError.


        :param name: The name of the attribute to find in self or self's
                     descendants.

        :param gettype: Valid values are `'default'`, `'hybrid'` `list`,
                        `iter`, `dict`, `'self'`.
                        Setting to `'default'` uses the value of
                        self.default_gettype for gettype
                        (its default is 'hybrid'). Setting to
                        `'hybrid'` returns a list if more
                        than 1 element is found, else returns
                        the non-iterable raw form of
                        the element. Setting to `list` returns a
                        list containing the attribute values.
                        Setting to `iter` returns an
                        iterable iterating through the
                        attribute values. Setting to `dict`
                        returns a dict containing pairs of
                        the containing node's name with the
                        attribute value. Setting to `'self'` will only search
                        for attrs in self, and will never wrap the attr
                        in an iterable form like the dict/list/iter options.

        searches for attributes only in self. Setting to `'nearest'` also
        searches through

        :param default: If not provided, AttributeError will be raised if attr
                        `name` not found. If given, return default if attr
                        `name` not found.

        :return: An iterable or non-iterable form of the attribute `name`
                 formed from self or descendant nodes. Depends on the value
                 given to `gettype`.
        """
        if name is SectionNone:
            name = self.default_attr
        attrs = self._SectionAttrParser__get_nearest_attr(name)
        return self._SectionAttrParser__parse_top_getattr(
            name, attrs, gettype=gettype, default=default)
