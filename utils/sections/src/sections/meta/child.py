from typing import List
from typing import Tuple
from typing import Union

from ..types import SectionAttrs
from ..types import SectionKeysOrObjects
from ..types import SectionNone
from ..types import SectionType
from .utils import get_dictval_i
from .utils import is_list_or_tuple
from .utils import len_


class ChildConstructor:
    def __call__(
        self,
        node: SectionType,
        args: SectionKeysOrObjects,
        children_attrs: SectionAttrs,
        keyname: str
    ) -> None:
        """
        Recursively repeat construction per child with extracted child attrs.
        """
        nofchildren_from_attrs, children_from_args = (
            _get_children_data(args, children_attrs)
        )
        self.nofchildren = (
            0 if not is_list_or_tuple(children_attrs.get(keyname))
            else len(children_attrs.get(keyname)))
        self.nofchildren = max(len(children_from_args), self.nofchildren)
        for i, child in enumerate(children_from_args):
            key = getattr(child, keyname)
            if key is SectionNone:
                key = i
            node[key] = child
        # for child_i in range(self.nofchildren):
        for child_i in range(nofchildren_from_attrs):
            self.__contruct_child(child_i, children_attrs, node, keyname)

    def fix_children_keys_if_invalid(self, child_attrs, keyname):
        from sections import Section
        keys = child_attrs[keyname]
        newkeys = []
        for key in keys:
            if not isinstance(key, Section):
                newkeys.append(key)
        child_attrs[keyname] = newkeys

    def __contruct_child(
        self,
        child_i: int, children_attrs: SectionAttrs,
        node: SectionType, keyname: str
    ) -> None:
        """Parse attr[i] from each attr and give to child."""
        child_attrs = {}
        for k, v in children_attrs.items():
            if len(v) > child_i:
                child_attrs[k] = v[child_i]
        child = get_dictval_i(node, child_i)
        self.__contruct_child_from_dict_or_cls(
            child, child_attrs, child_i, keyname, node)

    def __contruct_child_from_dict_or_cls(
            self,
            child: Union[SectionType, None],
            child_attrs: SectionAttrs,
            child_i: int,
            keyname: str,
            node: SectionType,
    ) -> None:
        if child:  # if child is Section instance
            for name, value in child_attrs.items():
                setattr(child, name, value)
            return
        child_attrs[keyname] = child_attrs.get(keyname, child_i)
        child = node.cls(parent=node, **child_attrs)
        node[getattr(child, keyname)] = child


def _get_children_data(
    args: SectionKeysOrObjects,
    attrs: SectionAttrs
) -> Tuple[int, List[SectionType]]:
    """
    Return number of children nodes implied by provided self.__call__ kwds,
    and any pre-constructed Section children passed in self.__call__ args.
    """
    nofchildren_from_attrs = (
        max(len_(v) for v in attrs.values()) if attrs else 0)
    children_from_args = []
    for arg in args:
        from sections import Section
        if isinstance(arg, Section):
            children_from_args += [arg]
    return (nofchildren_from_attrs, children_from_args)
