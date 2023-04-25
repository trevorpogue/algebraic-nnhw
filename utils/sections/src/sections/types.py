from typing import Any
from typing import Dict
from typing import List
from typing import NewType
from typing import Set
from typing import Union

# SectionAttrs: dict containing user-defined attributes to set for Section
# object nodes. It may also contain a few internally-provided attributes such
# as `parent`, and `name`.
SectionAttr = NewType('SectionAttr', Any)
SectionAttrs = NewType('SectionAttrs', Dict[Any, SectionAttr])

# Represents sections.Section type since sometimes cannot import Section yet
# without circular imports.
SectionType = NewType('Section', object)

# SectionKeysOrObjects: A List that contains either a Section key, a Section
# object, a set of one of those, or an arbitrarily deep nested list of the
# previously mentioned items
SectionKeysOrObjects = NewType(
    'SectionKeysOrObjects', List[Union[Any, Set[Any], SectionType, List[Any]]]
)

# Contains either a Section key, or an arbitrarily deep nested list of them
SectionKeys = NewType('SectionKeys', Union[Any, List[Any]])

# parent can be either another Section object or None (if node is root)
SectionParent = NewType('SectionParent', Union[SectionType, None])

# A shorthand form for an arbitrary dict
AnyDict = NewType('AnyDict', Dict[Any, Any])

# Valid values for the gettype arg used in Section.__call__:
# to denote use self.default_gettype
use_default_gettype = NewType('use_default_gettype', 'default')
# use hybrid getattr method (see Section.__call__ docstring for more info
hybrid = NewType('hybrid', 'hybrid')
GetType = NewType('GetType', Union[
    use_default_gettype, hybrid, list, iter, dict
])


class SectionNoneType:
    """
    Indicates the absence of a value as opposed to any possible user-defined
    value that can be given to an attribute. Using this instead of None allows
    users to still set attribute values to None without unexpected behaviour.
    """

    def __bool__(self) -> bool:
        return False

    def __str__(self) -> str:
        """
        Return `"section"` because a SectionNoneType object is used for the
        keys/names of unnamed nodes, and printing 'section' as the node's name
        makes its printed representation look more sensical.
        """
        return 'sections'


# SectionNoneType instantiation, like how None is an instantiation of NoneType
SectionNone = SectionNoneType()
