from typing import Any

from .types import SectionNone


class SectionStringParser:
    """String parsing methods for visualizing nodes and structures."""

    @property
    def __name(self) -> str:
        """
        Easily get the name/key of self node. This is slightly non-trivial
        because the name of the attribute representing the nodes name/key is
        contained in self._Section__keyname and may be user-customizable in the
        future.
        """
        return getattr(self, self._Section__keyname)

    def __str__(self) -> str:
        """
        Return :meth:`descendants_str <Section.descendants_str>` by default.
        See also
        :meth:`node_str <Section.node_str>` or
        more detailed view of the node or entire structure.
        """
        return self.descendants_str()

    def node_str(self) -> str:
        """
        Neatly print the public attributes of the Section node and its class,
        as well as its types property output.
        """
        return self.__node_str()

    def __node_str(self) -> str:
        section_name = (
            ''
            if self.__name is SectionNone
            else repr(self.__name) + '\n')
        attrs = {k: v for k, v in self.__dict__.items()
                 if not k.startswith(self.cls._Section__private_prefix)}
        attrs.pop(self._Section__keyname, None)
        attrs.pop('parent', None)
        s = ''
        for name in attrs:
            s += f'{name}' + '\n'
        longest_line_len = 0
        for line in s[:-1].split('\n'):
            if len(line) > longest_line_len:
                longest_line_len = len(line)
        prev_s = s
        s = section_name
        attr_strings = prev_s[:-1].split('\n')
        for name, value in zip(attr_strings, attrs.values()):
            s += self.__parse_public_node_attrs(name, value, longest_line_len)
        return s

    def __parse_public_node_attrs(
            self, name: Any, value: Any, longest_line_len: str) -> str:
        value = repr(value)
        pad = ' ' * (longest_line_len - len(name))
        return f'{name}' + pad + ' = ' + value + '\n'

    def descendants_str(self) -> str:
        """
        Print the output of :meth:`node_str <Section.node_str` for self and all
        of its descendants.
        """
        return '\n' + self.__descendants_str()

    def __descendants_str(
            self, depth: int = 0, prev_depths_s: str = '',
            prev_header_len: int = 0,
    ) -> str:
        """
        Private recursive call for
        :meth:`descendants_str <Section.descendants_str`.
        """
        s = ''
        s += self.__node_str()
        lpad = '' if depth == 0 else '  '
        if depth == 1 and prev_depths_s == '':
            lpad = ''
        cur_depths_s = s
        for i, child in enumerate(self.values()):
            s += child.__descendants_str(
                depth + 1, cur_depths_s)
        s = self.__get_box_str(s, lpad)
        return s

    def __get_box_str(self, s: str, lpad: str) -> str:
        header_len = 0
        for line in s[:-1].split('\n'):
            if len(line) > header_len:
                header_len = len(line)
        lpad = lpad + '│ '
        lines = []
        for line in s[:-1].split('\n'):
            rpad_len = header_len - len(line)
            rpad = ' ' * rpad_len + ' '
            rpad += '│'
            lines.append(lpad + line + rpad)
        s = '\n'.join(lines) + '\n'
        header_len += 2
        top_header = lpad[:-2] + ' ' + '_' * header_len + '\n'
        bottom_header = lpad[:-2] + ' ' + '¯' * header_len + '\n'
        s = top_header + s + bottom_header
        return s
