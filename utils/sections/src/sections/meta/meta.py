from copy import copy
from types import FunctionType
from typing import Any
from typing import Tuple

from ..types import SectionAttr
from ..types import SectionAttrs
from ..types import SectionKeys
from ..types import SectionKeysOrObjects
from ..types import SectionNone
from ..types import SectionParent
from ..types import SectionType
from .child import ChildConstructor
from .utils import dict_haskey
from .utils import is_list_or_tuple


class MetaSection(type):
    """
    Parses args and kwds passed to a sections() call or :class:`Section
    <Section>` instantiation and returns a Section tree structure. Parses
    node names/keys, separate attrs intended for current node vs child nodes,
    constructs current node, then recursively repeats for all child nodes.
    """

    singular_keyname = 'name'
    plural_keyname = 'names'
    default_keyvalue = SectionNone
    list_attr_prefix = '_'
    # _SectionAttrParser__getattr_enable = 'meta'

    ##########################################################################
    #                   Tree structure node construction                     #
    def __init__(self, name, bases, namespace, *args, **kwds):
        self.child_constructor = ChildConstructor()
        super().__init__(name, bases, namespace, *args, **kwds)

    def __call__(
            self,
            *args: SectionKeysOrObjects,
            parent: SectionParent = None,
            **kwds: SectionAttr
    ) -> SectionType:
        """
        Construct a tree structure of Section nodes based on the args and kwds
        provided by user in a sections() call or a Section() instantiation.
        """
        node_attrs, children_attrs, keyname = self.__parse_attrs(
            args, kwds, parent)
        node = self.__construct_node(parent, node_attrs)
        self.child_constructor(node, args, children_attrs, keyname)
        return node

    def __parse_attrs(
            self,
            args: SectionKeysOrObjects,
            kwds: SectionAttr,
            parent: SectionParent
    ) -> Tuple[SectionAttrs, SectionAttrs, str]:
        """
        From user-provided args and kwds in a sections() or Section() call,
        parse node names/keys, separate attrs intended for current node vs
        child nodes, construct current node, then recursively repeat for all
        child nodes.
        """
        node_attrs, children_attrs = {}, {}
        keyname = self.singular_keyname
        keys = self.__parse_keys(args, kwds, keyname)
        for k, v in {**kwds, **keys}.items():
            self.__parse_node_attrs(k, v, node_attrs, children_attrs,
                                    keys.get(keyname))
        node_attrs.pop(self.plural_keyname, None)
        children_attrs.pop(self.plural_keyname, None)
        self.__fix_node_key_if_invalid(node_attrs, parent, keyname)
        if children_attrs.get(keyname):
            self.child_constructor.fix_children_keys_if_invalid(
                children_attrs, keyname)
        node_attrs['_Section__keyname'] = keyname
        return node_attrs, children_attrs, keyname

    def __parse_node_attrs(
        self, name: str, value: Any, node_attrs: SectionAttrs,
            children_attrs: SectionAttrs, keys: Any
    ) -> None:
        """
        Extract attrs intended for current node from user-provided args/kwds.
        """
        if (not is_list_or_tuple(value)
                or name.startswith(self.list_attr_prefix)):
            node_attrs[name] = value
        else:
            values = value
            if len(values) > 1 and values[1] == ():
                values = copy(values)
                node_attrs[name] = values.pop(0)
                values.pop(0)
            if len(values):
                children_attrs[name] = values

    def __parse_keys(
            self,
            args: SectionKeysOrObjects,
            kwds: SectionAttr,
            keyname: str
    ) -> None:
        keys = {}
        if dict_haskey(kwds, keyname):
            keys[keyname] = kwds.get(keyname)
        if (not dict_haskey(kwds, keyname)
                and dict_haskey(kwds, self.plural_keyname)):
            keys[keyname] = kwds.get(self.plural_keyname)
        if not dict_haskey(keys, keyname):
            keys[keyname] = self.__getkeys_from_argskwds(args, kwds)
        return keys

    def __getkeys_from_argskwds(
            self,
            args: SectionKeysOrObjects,
            kwds: SectionAttrs
    ) -> SectionKeys:
        """
        Parse keys from args or kwds if it wasn't explicitly provided in kwds.
        """
        if _args_is_str_and_sections(*args):
            args = (args[0], (), *args[1:])
        from sections import Section
        if (len(args) == 1 and not is_list_or_tuple(args[0])
                and not isinstance(args[0], Section)):
            # if given a single non-list argument it will be used only as
            # current node's name/key
            return list(args)[0]
        elif len(args) >= 1:
            # otherwise if any arguments were given, they are for at least
            # one child's' names/keys, and possibly the current node's also
            return list(args)
        else:
            # otherwise, use the default for the current node
            return self.default_keyvalue

    def __fix_node_key_if_invalid(
            self, attrs: SectionAttrs, parent: SectionParent, keyname: str
    ) -> None:
        """
        Enforce that node must have a keyname attr, and disallow key values
        from properties and FunctionTypes.
        """
        default_keyvalue = (self.default_keyvalue if parent is None
                            else parent.nofchildren)
        keyvalue = attrs.get(keyname, default_keyvalue)
        if (isinstance(keyvalue, FunctionType)
                or isinstance(keyvalue, property)):
            keyvalue = default_keyvalue
        attrs[keyname] = keyvalue

    def __construct_node(
            self, parent: SectionParent, attrs: SectionAttrs
    ) -> SectionType:
        """
        Construct current node by providing node all its attrs, then update
        tree structure's class with any provided propertied or methods.
        """
        class_attrs, node_attrs = {}, {}
        for k, v in attrs.items():
            if isinstance(v, FunctionType) or isinstance(v, property):
                class_attrs[k] = v
            else:
                node_attrs[k] = v
        node = super().__call__(parent=parent, **node_attrs)
        for k, v in class_attrs.items():
            setattr(node.__class__, k, v)
        return node


def _args_is_str_and_sections(*args: Any):
    if len(args) <= 1:
        args_is_str_and_sections = False
    else:
        args_is_str_and_sections = isinstance(args[0], str)
        from sections import Section
        for arg in args[1:]:
            if not isinstance(arg, Section):
                args_is_str_and_sections = False
                break
    return args_is_str_and_sections
