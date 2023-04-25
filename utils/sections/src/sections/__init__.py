"""
Flexible tree data structures for organizing lists and dicts into sections.

https://github.com/trevorpogue/sections
"""

__version__ = '0.0.3'
__all__ = ['MetaSection', 'Section', 'SectionNone']

import sys

from .types import SectionNone
from .meta.meta import MetaSection
from .section import Section


class Module:

    from typing import Type

    from .types import SectionAttrs
    from .types import SectionKeysOrObjects

    """Class form of sections module to make the module callable."""

    @property
    def Section_factory(self) -> Type[Section]:
        """
        Return a unique class that inherits Section but can have its own
        unique properties and methods defined based on args/kwds, but will not
        influence these attributes in other classes returned from this method.
        """
        from .section import Section as _Section

        class Section(_Section):

            """Unique Section class creation."""

        return Section

    def __call__(
            self, *args: SectionKeysOrObjects, **kwds: SectionAttrs,
    ) -> Section:
        """
        Return a structure containing nodes all of the same unique Class
        instance type. And each structure returned will contain nodes with
        types of a different unique class instance than other structures.
        """
        return self.Section_factory(*args, **kwds)


sections = Module()

sys.modules['sections'] = sections  # make the module callable

# Add all the attributes to the 'module' so things can be imported normally
for key, value in list(globals().items()):
    if key in 'collections sys __VersionInfo key value config':
        # Avoid polluting the namespace
        continue

    setattr(sections, key, value)
