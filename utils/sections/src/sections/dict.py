from collections import OrderedDict
from typing import Any
from typing import Iterable
from typing import Tuple
from typing import Union

from .types import AnyDict
from .types import SectionType
from . import SectionNone


class SectionDict(OrderedDict):
    """Section dict overrides."""

    def __hash__(self) -> int:
        """
        Allows Section objects to be hashable, used in
        :meth:`get_nearest_attr <Section.get_nearest_attr` to keep a dict of
        which node every attr came from, even if nodes share the same name.
        """
        return hash(id(self))

    def __eq__(self, x: Any) -> bool:
        """For making Section objects hashable."""
        return id(self) == id(x)

    def __ne__(self, x: Any) -> bool:
        """For making Section objects hashable."""
        return id(self) != id(x)

    def __bool__(self) -> bool:
        """
        For convenience when checking if a node reference is valid or None.
        """
        return True

    def items(self) -> Tuple[Iterable[Any], Iterable[Any]]:
        """Return iterator over child names and children."""
        return super().items()

    def keys(self) -> Iterable[Any]:
        """Return iterator over child names."""
        return super().keys()

    def values(self) -> Iterable[Any]:
        """Return iterator over children."""
        return super().values()

    def update(self, other: SectionType) -> None:
        """Add all children from `other` to self."""
        for name, child in other.items():
            self[name] = child

    def move_to_end(self, name: Any, last: bool = True) -> None:
        """Move an existing child to either end of ordered children dict."""
        self._SectionAttrParser__invalidate_caches()
        super().move_to_end(name, last)

    def insertitem(
            self,
            i: int,
            name: Any,
            child: SectionType,
    ) -> None:
        """
        Insert `child' at index `i` of dict. The key for `child` will be taken
        from child's `name` attribute. If `i` is negative, insert at end of
        dict.
        """
        items = list(self.items())
        if i < 0:
            i = len(items)
        items.insert(i, (name, child))
        super().clear()
        self.update(dict(items))

    def append(self, child: SectionType) -> None:
        """
        append `child' to end of values(), using child's name as its name/key.
        """
        # TODO: insert to any index
        self.insert(-1, child)

    def insert(
            self,
            i: int,
            child: SectionType,
    ) -> None:
        """
        Insert `child' at index `i` of dict. The key for `child` will be taken
        from child's `name` attribute. If `i` is negative, insert at end of
        dict.
        """
        # TODO: insert to any index
        name = child._SectionStringParser__name
        self.insertitem(i, name, child)

    def get(self, name: Any, default: Any = None) -> None:
        try:
            return self[name]
        except KeyError:
            return default

    def clear(self) -> None:
        for name in self.copy().keys():
            super().__delitem__(name)
        self._SectionAttrParser__invalidate_caches()

    def fromkeys(self, *args: Any, **kwds: Any) -> None:
        """Not supported."""
        raise NotImplementedError(
            'Section.fromkeys() is not supported.'
        )

    # def copy(self) -> None:
    #     """Not supported."""
    #     raise NotImplementedError(
    #         'Section.copy() is not supported.'
    #     )

    def setdefault(self, name: Any, default: SectionType) -> Any:
        """
        If self has a child `name`, return it. If not, set child `default` with
        name `name` default and return `default`.
        """
        try:
            return super().__getitem__(name)
        except KeyError:
            self[name] = default
            return self[name]

    def pop(self, name_or_i: Union[Any, int], default: Any = SectionNone
            ) -> Any:
        """
        Remove child `name_or_i` from self. If there is no child with that
        name and `name_or_i` is int, remove child in position `name_or_i`.
        """
        self._SectionAttrParser__invalidate_caches()
        try:
            return super().pop(name_or_i)
        except KeyError:
            child = self.__getitem_from_index(name_or_i)
            if child is None:
                if default is not SectionNone:
                    return default
                else:
                    raise IndexError
            name = child._SectionStringParser__name
            return super().pop(name)

    def popitem(self, last=True) -> Tuple[Any, Any]:
        """Remove last added child from self."""
        self._SectionAttrParser__invalidate_caches()
        return super().popitem(last)

    def __iter__(self) -> Iterable[SectionType]:
        """
        By default iterate over child nodes instead of their names/keys.
        """
        for v in self.values():
            yield v

    def __delitem__(self, name: Any) -> SectionType:
        """Delete child `name`."""
        super().__delitem__(name)
        self._SectionAttrParser__invalidate_caches()

    def __getitem__(self, names: Any) -> SectionType:
        if isinstance(names, tuple):
            items = list(map(self.__getitem, names))
            return self.node_withchildren_fromiter(items)
        else:
            return self.__getitem(names)

    def __getitem(self, name: Any) -> SectionType:
        """Return child node `name` of self."""
        child = super().get(name)
        if child is None:
            if self.__dict__.get('_SectionDict__children_by_name'):
                child = self.__children_by_name.get(name)
        if child is None and isinstance(name, int):
            child = self.__getitem_from_index(name)
        if child is None:
            raise KeyError
        return child

    def __getitem_from_index(self, i: int) -> SectionType:
        matching_child = None
        for ii, child in enumerate(self.values()):
            if ii == i:
                matching_child = child
                break
        return matching_child

    def __setitem__(
            self, name: Any, value: Union[SectionType, AnyDict]
    ) -> None:
        """
        Add a child `name` to self. Ensure added children are converted to the
        same unique Section type as the rest of the nodes in the structure, and
        update its name to `name`, and its parent to self.
        """
        from . import Section
        if isinstance(value, Section):
            child = self.__convert_to_self_cls(name, value)
        elif isinstance(value, dict):
            child = self.cls(name, **{**value, 'parent': self})
        else:
            raise ValueError
        super().__setitem__(name, child)
        child._SectionAttrParser__invalidate_caches()

    def __convert_to_self_cls(
            self, name: Any, value: SectionType
    ) -> None:
        """Ensure output is of self's unique Section class instance type."""
        if isinstance(value, self.cls):
            child = value
            child.__setattr__('parent', self, _invalidate_cache=False)
            child.__setattr__(child._Section__keyname, name,
                              _invalidate_cache=False)
        else:
            attrs = {k: v for k, v in value.__dict__.items()
                     if not k.startswith(self.cls._Section__private_prefix)}
            attrs.pop(value._Section__keyname, None)
            child = self.cls(
                name, **{**attrs, 'parent': self})
            for grandchild in value.children:
                grandchild_name = grandchild._SectionStringParser__name
                child[grandchild_name] = (
                    self.__convert_to_self_cls(grandchild_name, grandchild))
        return child
