from typing import Any
from typing import Iterable
from typing import List
from typing import Optional
from typing import Union

from .pluralizer import Pluralizer
from .types import AnyDict
from .types import GetType
from .types import SectionNone


class SectionAttrParser:
    """Logic for setting and getting attrs from self or descendant nodes."""

    ##########################################################################
    #              tree-structure-wide attributes for every node             #
    __pluralizer = Pluralizer()

    _setattr_invalidate_cache_excludes = [
        'default_gettype',
        'use_cache',
    ]
    # default value for __use_nearest until it can be set __init__. Causes
    # issue when using deepcopy with Section otherwise, has to do with this
    # attributes use in SectionAttrParser.__getattr__
    __getattr_enable = False
    ##########################################################################

    def __init__(self) -> None:
        self.__getattr_enable = True

    def __invalidate_caches(self, name: Optional[str] = None) -> None:
        """
        Empty self and all ancestor attribute caches entirely or just for
        attribute `name`. This should be done every time a node is added or
        removed from the tree, or when a node attribute is changed.
        """
        node = self
        while node:
            # in some cases, node might not have parent assigned yet here
            # also, use parent in case node gets deleted during
            # structure_change()
            parent = node.__dict__.get('parent', None)
            if node.use_cache and not node.isleaf:
                node.__invalidate_node_cache(name)
            if name is None:
                node.structure_change()
            node = parent

    def __invalidate_node_cache(self, name: Optional[str] = None) -> None:
        """Invalidate cache for only self node."""
        if name:
            plural, singular = self.__pluralizer(name)
            self.__cache.pop(name, None)
            self.__cache.pop(plural, None)
            self.__cache.pop(singular, None)
        else:
            self.__setattr__('_SectionAttrParser__cache',
                             {}, _invalidate_cache=False)

    def __setattr__(
            self, name: str, value: Any, _invalidate_cache=True
    ) -> None:
        """
        If value is a list, recursively setattr for each child node with the
        corresponding value element from the value list.
        """
        if isinstance(value, list) and not name.startswith(
                self.list_attr_prefix):
            for child, v in zip(self.values(), value):
                setattr(child, name, v)
        else:
            self.__set_node_attr(name, value, _invalidate_cache)

    def __set_node_attr(
            self, name: str, value: Any, _invalidate_cache=True
    ) -> None:
        """Set attr for only the self node."""
        super().__setattr__(name, value)
        if (_invalidate_cache and not name.startswith(
                self.cls._Section__private_prefix)
                and not self.cls._setattr_invalidate_cache_excludes.count(
                    name)):
            self.__invalidate_caches(name)

    def __getattr__(self, name: str) -> Any:
        """
        Called if self node does not have attribute `name`, in which case try
        finding attribute `name` from :meth:`__call__ <Section.__call__>`.
        """
        if self.__getattr_enable:
            return self.__call__(name)
        else:
            return SectionNone

    def __get_nearest_attr(
            self, name: str,
    ) -> Union[List[Any], Iterable[Any], AnyDict]:
        """
        Default method called by :meth:`__call__ <Section.__call__>`. See
        the docstring of :meth:`__call__ <Section.__call__>` for the full
        details of what this method does.
        """
        attrs = SectionNone
        if self.use_cache and not self.isleaf:
            attrs = self.__cache.get(name, SectionNone)
        if attrs is SectionNone:
            attrs = self.__get_node_attrs(name)
        if attrs is SectionNone:
            attrs = {}
            for child in self.values():
                attrs.update(child.__get_nearest_attr(name))
            self.__update_cache(name, attrs)
        return attrs

    def __update_cache(self, name: str, attrs: Any) -> None:
        if self.use_cache and not self.isleaf:
            self.__cache[name] = attrs
            if self.use_pluralsingular:
                plural, singular = self.__pluralizer(name)
                self.__cache[plural] = attrs
                self.__cache[singular] = attrs

    def __get_node_attrs(self, name: str) -> AnyDict:
        """
        Differs from :meth:`get_node_attrs <Section.get_node_attrs>`
        in that this method will always return found attributes in a dict form
        so that the source node is tracked.
        """
        self.__getattr_enable = False
        attr = getattr(self, name, SectionNone)
        if attr is SectionNone:
            attr = self.__get_pluralsingular_node_attr(name, attr)
        self.__getattr_enable = True
        if attr is not SectionNone:
            attr = {self: attr}
        # elif self.use_cache and not self.isleaf:
            # attr = self.__cache.get(name, SectionNone)
        return attr

    def __get_pluralsingular_node_attr(self, name: str, attr: Any) -> AnyDict:
        """Try getting the plural/singular forms of the attribute name."""
        if self.use_pluralsingular:
            plural, singular = self.__pluralizer(name)
        else:
            return SectionNone
        attr = getattr(self, plural, SectionNone)
        if attr is SectionNone:
            attr = getattr(self, singular, SectionNone)
        return attr

    def __parse_top_getattr(
            self,
            name: str,
            attrs: Any,
            gettype: GetType = 'default',
            default: Any = SectionNone
    ) -> Union[Any, List[Any], Iterable[Any], AnyDict]:
        """
        Return an iterable of a type depending on argument
        `gettype` if values from multiple nodes are returned from
        :meth:`_get_nearest_attr <Section._get_nearest_attr>`, else if one
        value is found (from the root caller node) then the raw value is
        returned (not in an iterable), else raise AttributeError if no values
        are found.
        """
        attrs = self.__check_for_attribute_error(name, attrs, gettype=gettype,
                                                 default=default)
        if gettype == 'default':
            gettype = self.default_gettype
        if gettype == 'hybrid':
            return (list(attrs.values()) if len(attrs) > 1
                    else next(iter(attrs.values())))  # return dict value[0]
        else:
            return _get_iterable_attrs(attrs, gettype=gettype)

    def __delattr__(self, name: str) -> None:
        """Delete attribute `name`."""
        # TODO: maybe this should delete all children attrs if not in self like
        # in get_nearest_attr()
        if self.__dict__.get(name, SectionNone) is not SectionNone:
            super().__delattr__(name)
        if self.use_pluralsingular:
            plural, singular = self.__pluralizer(name)
            if self.__dict__.get(plural, SectionNone) is not SectionNone:
                super().__delattr__(plural)
            if self.__dict__.get(singular, SectionNone) is not SectionNone:
                super().__delattr__(singular)
        self.__invalidate_caches(name)

    def __check_for_attribute_error(
        self, name: str, attrs: AnyDict, gettype: GetType = 'default',
        default: Any = SectionNone
    ) -> None:
        """
        Raise attribute error if none were found.
        """
        if attrs is SectionNone or not len(attrs):
            if default is not SectionNone:
                return {self: default}
            else:
                raise AttributeError(name)
        else:
            return attrs


def _get_iterable_attrs(
        attrs: AnyDict, gettype: GetType = 'default',
) -> AnyDict:
    """
    Convert attrs from a dict to possibly a different requested iterable.
    """
    if gettype is list:
        attrs = list(attrs.values())
    elif gettype is dict:
        attrs = {section.name: attrvalue for section, attrvalue
                 in attrs.items()}
    else:  # elif gettype is iter
        attrs = attrs.values()
    return attrs
