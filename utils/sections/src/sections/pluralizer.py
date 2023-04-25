from typing import Tuple

from pluralizer import Pluralizer as _Pluralizer


class Pluralizer:
    """Extract the singular and plural forms of a word."""

    def __init__(self):
        """Init pluralizer from pluralizer package."""
        self._pluralizer = _Pluralizer()
        self._plurals = {}
        self._singulars = {}

    def __call__(self, name: str) -> Tuple[str, str]:
        """
        Compute the plural and singular forms of `name` and store the
        results in a dict because calculating them repeatedly can be
        computationally expensive. The dicts are structure-wide attributes
        common to all nodes in a structure.
        """
        plural = self._plurals.get(name)
        singular = self._singulars.get(name)
        if not plural:
            plural = self._pluralizer.plural(name)
            self._plurals[singular] = plural
            self._plurals[plural] = plural
            self._plurals[name] = plural
        if not singular:
            singular = self._pluralizer.singular(name)
            self._singulars[singular] = singular
            self._singulars[plural] = singular
            self._singulars[name] = singular
        return plural, singular
