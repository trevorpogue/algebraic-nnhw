from typing import Any

from ..types import AnyDict
from ..types import SectionNone


def is_list_or_tuple(x: Any) -> bool:
    return isinstance(x, list) or isinstance(x, tuple)


def dict_haskey(d: AnyDict, key: Any) -> bool:
    """
    Return True if dict contains user-provided value for key, else False.
    """
    return d.get(key, SectionNone) is not SectionNone


def get_dictval_i(d: AnyDict, i: int) -> Any:
    """Get value in iterator position i from dict as if its a list."""
    ret = None
    for ii, value in enumerate(d.values()):
        if ii == i:
            ret = value
            break
    return ret


def len_(x: Any) -> int:
    """Return len of x if it is iterable, else 0."""
    return max(1, len(x)) if is_list_or_tuple(x) else 0
