.. start-badges

.. |coveralls| image:: https://coveralls.io/repos/github/trevorpogue/sections/badge.svg
    :alt: Coverage Status
    :target: https://coveralls.io/github/trevorpogue/sections

.. |codacy| image:: https://app.codacy.com/project/badge/Grade/92804e7a0df44f09b42bc6ee1664bc67
    :alt: Codacy Code Quality Status
    :target: https://www.codacy.com/gh/trevorpogue/sections/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=trevorpogue/sections&amp;utm_campaign=Badge_Grade

.. |codeclimate| image:: https://codeclimate.com/github/trevorpogue/sections/badges/gpa.svg
   :alt: CodeClimate Quality Status
   :target: https://codeclimate.com/github/trevorpogue/sections

.. |version| image:: https://img.shields.io/pypi/v/sections.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/sections

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/sections.svg
    :alt: Supported versions
    :target: https://pypi.org/project/sections

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/sections.svg
    :alt: Supported implementations
    :target: https://pypi.org/project/sections

.. |wheel| image:: https://img.shields.io/pypi/wheel/sections.svg
    :alt: PyPI Wheel
    :target: https://pypi.org/project/sections

.. |downloads| image:: https://pepy.tech/badge/sections
    :alt: downloads
    :target: https://pepy.tech/project/sections

.. |downloads-week| image:: https://pepy.tech/badge/sections/week
    :alt: downloads
    :target: https://pepy.tech/project/sections

.. |docs| image:: https://readthedocs.org/projects/sections/badge/?style=flat
    :alt: Documentation Status
    :target: https://sections.readthedocs.io/

.. |requires| image:: https://requires.io/github/trevorpogue/sections/requirements.svg?branch=main
    :alt: Requirements Status
    :target: https://requires.io/github/trevorpogue/sections/requirements/?branch=main

.. |commits-since| image:: https://img.shields.io/github/commits-since/trevorpogue/sections/v0.0.3.svg
    :alt: Commits since latest release
    :target: https://github.com/trevorpogue/sections/compare/v0.0.3...main

.. end-badges

==============================
[ s e | c t | i o | n s ]
==============================

|coveralls| |codacy| |codeclimate| |requires|

|version| |supported-versions| |supported-implementations| |wheel|

|docs| |commits-since| |downloads-week| |downloads|

Python package providing flexible tree data structures for organizing lists and dicts into sections.

Sections is designed to be:

* **Intuitive**: Start quickly, spend less time reading the docs.
* **Scalable**: Grow arbitrarily complex trees as your problem scales.
* **Flexible**: Rapidly build nodes with custom attributes, properties, and methods on the fly.
* **Fast**: Made with performance in mind - access lists and sub-lists/dicts in Θ(1) time in many cases. See the Performance section for the full details.
* **Reliable**: Contains an exhaustive test suite and 100\% code coverage.

----------------------------------------------------------------
Links
----------------------------------------------------------------
* GitHub_
* Documentation_

=========================
Usage
=========================

.. code-block:: bash

    $ pip install sections

.. literalinclude:: ../tests/test_doc_examples.py
                    :start-after: sphinx-start-usage
                    :end-before: sphinx-end-usage
                    :dedent: 4
                    :language: python

.. literalinclude:: ./examples_print_output.txt
                    :start-after: sphinx-start-usage
                    :end-before: sphinx-end-usage

.. literalinclude:: ../tests/test_doc_examples.py
                    :start-after: sphinx-start-usage-assert
                    :end-before: sphinx-end-usage-assert
                    :dedent: 4
                    :language: python

**Scale in size:**

.. literalinclude:: ../tests/test_doc_examples.py
                    :start-after: sphinx-start-complex
                    :end-before: sphinx-end-complex
                    :dedent: 4
                    :language: python

.. literalinclude:: ./examples_print_output.txt
                    :start-after: sphinx-start-complex
                    :end-before: sphinx-end-complex

----------------------------------------------------------------
Attrs: Plural/singular hybrid attributes and more
----------------------------------------------------------------

Spend less time deciding between using the singular or plural form for an attribute name:

.. literalinclude:: ../tests/test_doc_examples.py
                    :start-after: sphinx-start-plural-singular
                    :end-before: sphinx-end-plural-singular
                    :dedent: 4
                    :language: python

If you don't like this feature, simply turn it off as shown in the **Details - Plural/singular attributes** section.

--------------------------------------------------------------------
Properties: Easily add on the fly
--------------------------------------------------------------------

Properties and methods are automatically added to all nodes in a structure returned from a ``sections()`` call when passed as keyword arguments:

.. literalinclude:: ../tests/test_doc_examples.py
                    :start-after: sphinx-start-properties
                    :end-before: sphinx-end-properties
                    :dedent: 4
                    :language: python

Adding properties and methods this way doesn't affect the class definitions of Sections/nodes from other structures. See the **Details - Properties/methods** section for how this works.

--------------------------------------------------------------------
Construction: Build gradually or all at once
--------------------------------------------------------------------

Construct section-by-section, section-wise, attribute-wise, or other ways:

.. literalinclude:: ../tests/test_doc_examples.py
                    :start-after: sphinx-start-books-construction
                    :end-before: sphinx-end-books-construction
                    :dedent: 4
                    :language: python

=============
Details
=============

--------------
Section names
--------------

The non-keyword arguments passed into a ``sections()`` call define the section names and are accessed through the attribute ``name``. The names are used like ``keys`` in a ``dict`` to access each child section of the root section node:

.. literalinclude:: ../tests/test_doc_examples.py
                    :start-after: sphinx-start-names
                    :end-before: sphinx-end-names
                    :dedent: 4
                    :language: python

Names are optional, and by default, children names are assigned as integer values corresponding to indices in an array, while a root has a default keyvalue of ``sections.SectionNone``:

.. literalinclude:: ../tests/test_doc_examples.py
                    :start-after: sphinx-start-names-printing
                    :end-before: sphinx-end-names-printing
                    :dedent: 4
                    :language: python

---------------------------------
Parent names and attributes
---------------------------------

A parent section name can optionally be provided as the first argument in a ``sections()`` call by defining it in a set (surrounding it with curly brackets). This strategy avoids an extra level of braces when instantiating Section objects. This idea applies also for defining parent attributes:

.. literalinclude:: ../tests/test_doc_examples.py
                    :start-after: sphinx-start-parent-names
                    :end-before: sphinx-end-parent-names
                    :dedent: 4
                    :language: python

-----------------------------------------------
Return attributes as a list, dict, or iterable
-----------------------------------------------

Access the data in different forms with the ``gettype`` argument in `Section.__call__()`_ as follows:

.. code-block:: python

    menu = sections('Breakfast', 'Dinner', sides=['HashBrown', 'Fries'])

    # return as list always, even if a single element is returned
    assert menu('sides', list) == ['HashBrown', 'Fries']
    assert menu['Breakfast']('side', list) == ['HashBrown']

    # return as dict
    assert menu('sides', dict) == {'Breakfast': 'HashBrown', 'Dinner': 'Fries'}
    assert menu['Breakfast']('side', dict) == {'Breakfast': 'HashBrown'}

    # return as iterator over elements in list (fastest method, theoretically)
    for i, value in enumerate(menu('sides', iter)):
        assert value == ['HashBrown', 'Fries'][i]
    for i, value in enumerate(menu['Breakfast']('side', iter)):
        assert value == ['HashBrown'][i]

See the `Section.__call__()`_ method in the References section of the docs for more options.

Set the default return type when accessing structure attributes by changing ``Section.default_gettype`` as follows:

.. literalinclude:: ../tests/test_doc_examples.py
                    :start-after: sphinx-start-gettype
                    :end-before: sphinx-end-gettype
                    :dedent: 4
                    :language: python

The above will also work for accessing attributes in the form ``object.attr`` but only if the node does not contain the attribute ``attr``, otherwise it will return the non-iterable raw value for ``attr``. Therefore, for consistency, access attributes using `Section.__call__()`_ like above if you wish to **always receive an iterable** form of the attributes.

----------------------------------------------------------------
Plural/singular attributes
----------------------------------------------------------------

When an attribute is not found in a Section node, both the plural and singular
forms of the word are then checked to see if the node contains the attribute
under those forms of the word. If they are still not found, the node will
recursively repeat the same search on each of its children, concatenating the
results into a list or dict. The true attribute name in each node supplied a
corresponding value is whatever name was given in the keyword argument's key
(i.e. ``status`` in the example below).

If you don't like this feature, simply turn it off using the following:

.. literalinclude:: ../tests/test_doc_examples.py
                    :start-after: sphinx-start-plural-singular-disable
                    :end-before: sphinx-end-plural-singular-disable
                    :dedent: 4
                    :language: python

Note, however, that this will still traverse descendant nodes to see if they
contain the requested attribute. To stop using this feature also, access
attributes using the `Section.get_node_attr()`_ method instead.

----------------------------------------------------------------
Properties/methods
----------------------------------------------------------------

Each ``sections()`` call returns a structure containing nodes of a unique class created in a class factory function, where the unique class definition contains no logic except that it inherits from the Section class. This allows properties/methods added to one structure's class definition to not affect the class definitions of nodes from other structures.

--------------
Subclassing
--------------

Inheriting Section is easy, the only requirement is to call ``super().__init__(**kwds)`` at some point in ``__init__()``  like below if you override that method:

.. literalinclude:: ../tests/test_doc_examples.py
                    :start-after: sphinx-start-subclassing
                    :end-before: sphinx-end-subclassing
                    :dedent: 4
                    :language: python

``Section.__init__()`` assigns the kwds values passed to it to the object attributes, and the passed kwds are generated during instantiation by a metaclass.

--------------
Performance
--------------

Sections is intended for convenience use with small to mid sized datasets. It is not currently recommended to be used for holding large datasets with roughly 100,000 element or more. However, efforts have been made to make performance faster for small to mid sized datasets. If this package were to become popular enough, it would be possible to provide a C or C++ backend to make it suitable for large datasets.

Each non-leaf Section node keeps a cache containing quickly readable references to attribute dicts previously parsed from manually traversing through descendant nodes in an earlier read. The caches are invalidated accordingly for modified nodes and their ancestors when the tree structure or node attribute values change.

The caches allow instant reading of sub-lists/dicts in Θ(1) time and can often
make structure attribute reading faster by 5x, or even much more when the
structure is rarely being modified.
If preferred, turn this feature off to avoid the extra memory consumption it causes by modifying the node or structure's class attribute ``use_cache`` to ``False`` as follows:

..
   For structures representing lists/dicts with more than 1000 - 10,000
   elements, the extra memory consumption that this technique uses may start to
   make it not beneficial to use.


.. code-block:: python

    sect = sections(*[[[[[42] * 10] * 10] * 10] * 10])
    sect.use_cache = False              # turn off for just the root node
    sect.cls.use_cache = False          # turn off for all nodes in `sect`
    sections.Section.use_cache = False  # turn off for all structures

.. _References: https://sections.readthedocs.io/en/latest/reference/index.html
.. _Section.get_node_attr(): https://sections.readthedocs.io/en/latest/reference/#sections.Section.get_node_attr
.. _Section.__call__(): https://sections.readthedocs.io/en/latest/reference/#sections.Section.__call__
.. _Section.deep_str(): https://sections.readthedocs.io/en/latest/reference/#sections.Section.deep_str
.. _GitHub: https://github.com/trevorpogue/sections
.. _Documentation: https://sections.readthedocs.io
