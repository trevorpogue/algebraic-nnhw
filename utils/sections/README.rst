
[ s e | c t | i o | n s ]
*************************

`https://coveralls.io/github/trevorpogue/sections <https://coveralls.io/github/trevorpogue/sections>`_ `https://www.codacy.com/gh/trevorpogue/sections/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=trevorpogue/sections&amp;utm_campaign=Badge_Grade <https://www.codacy.com/gh/trevorpogue/sections/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=trevorpogue/sections&amp;utm_campaign=Badge_Grade>`_ `https://codeclimate.com/github/trevorpogue/sections <https://codeclimate.com/github/trevorpogue/sections>`_ `https://requires.io/github/trevorpogue/sections/requirements/?branch=main <https://requires.io/github/trevorpogue/sections/requirements/?branch=main>`_

`https://pypi.org/project/sections <https://pypi.org/project/sections>`_ `https://pypi.org/project/sections <https://pypi.org/project/sections>`_ `https://pypi.org/project/sections <https://pypi.org/project/sections>`_ `https://pypi.org/project/sections <https://pypi.org/project/sections>`_

`https://sections.readthedocs.io/ <https://sections.readthedocs.io/>`_ `https://github.com/trevorpogue/sections/compare/v0.0.3...main <https://github.com/trevorpogue/sections/compare/v0.0.3...main>`_ `https://pepy.tech/project/sections <https://pepy.tech/project/sections>`_ `https://pepy.tech/project/sections <https://pepy.tech/project/sections>`_

Python package providing flexible tree data structures for organizing lists and dicts into sections.

* `GitHub <https://github.com/trevorpogue/sections>`_

* `Documentation <https://sections.readthedocs.io>`_

Sections is designed to be:

* **Intuitive**: Start quickly, spend less time reading the docs.

* **Scalable**: Grow arbitrarily complex trees as your problem scales.

* **Flexible**: Rapidly build nodes with custom attributes, properties, and methods on the fly.

* **Fast**: Made with performance in mind - access lists and sub-lists/dicts in Θ(1) time in many cases. See the Performance section for the full details.

* **Reliable**: Contains an exhaustive test suite and 100% code coverage.


Usage
*****

.. code-block:: bash

   $ pip install sections

.. code-block:: python

   import sections

   menu = sections(
       'Breakfast', 'Dinner',
       main=['Bacon&Eggs', 'Burger'],
       side=['HashBrown', 'Fries'],
   )

::

   $ print(menu)
    _________________________
   │  _____________________  │
   │ │ 'Breakfast'         │ │
   │ │ main = 'Bacon&Eggs' │ │
   │ │ side = 'HashBrown'  │ │
   │  ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯  │
   │  _________________      │
   │ │ 'Dinner'        │     │
   │ │ main = 'Burger' │     │
   │ │ side = 'Fries'  │     │
   │  ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      │
    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯

.. code-block:: python

   # menu's API with the expected results:
   assert menu.mains == ['Bacon&Eggs', 'Burger']
   assert menu.sides == ['HashBrown', 'Fries']
   assert menu['Breakfast'].main == 'Bacon&Eggs'
   assert menu['Breakfast'].side == 'HashBrown'
   assert menu['Dinner'].main == 'Burger'
   assert menu['Dinner'].side == 'Fries'
   assert menu('sides', list) == ['HashBrown', 'Fries']
   assert menu('sides', dict) == {'Breakfast': 'HashBrown', 'Dinner': 'Fries'}
   # menu tree has 3 nodes:
   assert menu.isroot and menu.isparent
   assert isinstance(menu, sections.Section)
   assert menu['Breakfast'].ischild and menu['Dinner'].ischild
   assert menu['Breakfast'].isleaf and menu['Dinner'].isleaf
   assert isinstance(menu['Breakfast'], sections.Section)
   assert isinstance(menu['Dinner'], sections.Section)

**Scale in size:**

.. code-block:: python

   library = sections(
       "My Bookshelf",
       sections({'Fiction'},
                'LOTR', 'Harry Potter',
                author=['JRR Tolkien', 'JK Rowling'],
                topic=[{'Fantasy'}, 'Hobbits', 'Wizards'],),
       sections({'Non-Fiction'},
                'General Relativity', 'A Brief History of Time',
                author=['Albert Einstein', 'Steven Hawking'],
                topic=[{'Physics'}, 'Time, Gravity', 'Black Holes'],
                ),
       books=property(lambda self: self.leaves.names),
   )
   assert library.books == [
       'LOTR', 'Harry Potter', 'General Relativity', 'A Brief History of Time'
   ]

::

   $ print(library)
    ________________________________________
   │ 'My Bookshelf'                         │
   │    ______________________________      │
   │   │ 'Fiction'                    │     │
   │   │ topic = 'Fantasy'            │     │
   │   │    ________________________  │     │
   │   │   │ 'LOTR'                 │ │     │
   │   │   │ author = 'JRR Tolkien' │ │     │
   │   │   │ topic  = 'Hobbits'     │ │     │
   │   │    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯  │     │
   │   │    _______________________   │     │
   │   │   │ 'Harry Potter'        │  │     │
   │   │   │ author = 'JK Rowling' │  │     │
   │   │   │ topic  = 'Wizards'    │  │     │
   │   │    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯   │     │
   │    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      │
   │    __________________________________  │
   │   │ 'Non-Fiction'                    │ │
   │   │ topic = 'Physics'                │ │
   │   │    ____________________________  │ │
   │   │   │ 'General Relativity'       │ │ │
   │   │   │ author = 'Albert Einstein' │ │ │
   │   │   │ topic  = 'Time, Gravity'   │ │ │
   │   │    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯  │ │
   │   │    ___________________________   │ │
   │   │   │ 'A Brief History of Time' │  │ │
   │   │   │ author = 'Steven Hawking' │  │ │
   │   │   │ topic  = 'Black Holes'    │  │ │
   │   │    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯   │ │
   │    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯  │
    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯


Attrs: Plural/singular hybrid attributes and more
=================================================

Spend less time deciding between using the singular or plural form for an attribute name:

.. code-block:: python

   tasks = sections('pay bill', 'clean', status=['completed', 'started'])
   assert tasks.statuses == ['completed', 'started']
   assert tasks['pay bill'].status == 'completed'
   assert tasks['clean'].status == 'started'

If you don’t like this feature, simply turn it off as shown in the **Details - Plural/singular attributes** section.


Properties: Easily add on the fly
=================================

Properties and methods are automatically added to all nodes in a structure returned from a ``sections()`` call when passed as keyword arguments:

.. code-block:: python

   schedule = sections(
       'Weekdays', 'Weekend',
       hours_per_day=[[8, 8, 6, 10, 8], [4, 6]],
       hours=property(lambda self: sum(self.hours_per_day)),
   )
   assert schedule['Weekdays'].hours == 40
   assert schedule['Weekend'].hours == 10
   assert schedule.hours == 50

Adding properties and methods this way doesn’t affect the class definitions of Sections/nodes from other structures. See the **Details - Properties/methods** section for how this works.

Construction: Build gradually or all at once

Construct section-by-section, section-wise, attribute-wise, or other ways:

.. code-block:: python

   def demo_different_construction_techniques():
       """Example construction techniques for producing the same structure."""
       # Building section-by-section
       books = sections()
       books['LOTR'] = sections(topic='Hobbits', author='JRR Tolkien')
       books['Harry Potter'] = sections(topic='Wizards', author='JK Rowling')
       demo_resulting_object_api(books)

       # Section-wise construction
       books = sections(
           sections('LOTR', topic='Hobbits', author='JRR Tolkien'),
           sections('Harry Potter', topic='Wizards', author='JK Rowling')
       )
       demo_resulting_object_api(books)

       # Attribute-wise construction
       books = sections(
           'LOTR', 'Harry Potter',
           topics=['Hobbits', 'Wizards'],
           authors=['JRR Tolkien', 'JK Rowling']
       )
       demo_resulting_object_api(books)

       # setattr post-construction
       books = sections(
           'LOTR', 'Harry Potter',
       )
       books.topics = ['Hobbits', 'Wizards']
       books['LOTR'].author = 'JRR Tolkien'
       books['Harry Potter'].author = 'JK Rowling'
       demo_resulting_object_api(books)

   def demo_resulting_object_api(books):
       """Example Section structure API and expected results."""
       assert books.names == ['LOTR', 'Harry Potter']
       assert books.topics == ['Hobbits', 'Wizards']
       assert books.authors == ['JRR Tolkien', 'JK Rowling']
       assert books['LOTR'].topic == 'Hobbits'
       assert books['LOTR'].author == 'JRR Tolkien'
       assert books['Harry Potter'].topic == 'Wizards'
       assert books['Harry Potter'].author == 'JK Rowling'

   demo_different_construction_techniques()


Details
*******


Section names
=============

The non-keyword arguments passed into a ``sections()`` call define the section names and are accessed through the attribute ``name``. The names are used like ``keys`` in a ``dict`` to access each child section of the root section node:

.. code-block:: python

   books = sections(
       'LOTR', 'Harry Potter',
       topic=['Hobbits', 'Wizards'],
       author=['JRR Tolkien', 'JK Rowling']
   )
   assert books.names == ['LOTR', 'Harry Potter']
   assert books['LOTR'].name == 'LOTR'
   assert books['Harry Potter'].name == 'Harry Potter'

Names are optional, and by default, children names are assigned as integer values corresponding to indices in an array, while a root has a default keyvalue of ``sections.SectionNone``:

.. code-block:: python

   sect = sections(x=['a', 'b'])
   assert sect.sections.names == [0, 1]
   assert sect.name is sections.SectionNone

   # the string representation of sections.SectionNone is 'section':
   assert str(sect.name) == 'sections'


Parent names and attributes
===========================

A parent section name can optionally be provided as the first argument in a ``sections()`` call by defining it in a set (surrounding it with curly brackets). This strategy avoids an extra level of braces when instantiating Section objects. This idea applies also for defining parent attributes:

.. code-block:: python

   library = sections(
       {"My Bookshelf"},
       [{'Fantasy'}, 'LOTR', 'Harry Potter'],
       [{'Academic'}, 'Advanced Mathematics', 'Physics for Engineers'],
       topic=[{'All my books'},
              [{'Imaginary things'}, 'Hobbits', 'Wizards'],
              [{'School'}, 'Numbers', 'Forces']],
   )
   assert library.name == "My Bookshelf"
   assert library.sections.names == ['Fantasy', 'Academic']
   assert library['Fantasy'].sections.names == ['LOTR', 'Harry Potter']
   assert library['Academic'].sections.names == [
       'Advanced Mathematics', 'Physics for Engineers'
   ]
   assert library['Fantasy']['Harry Potter'].name == 'Harry Potter'
   assert library.topic == 'All my books'
   assert library['Fantasy'].topic == 'Imaginary things'
   assert library['Academic'].topic == 'School'


Return attributes as a list, dict, or iterable
==============================================

Access the data in different forms with the ``gettype`` argument in `Section.__call__() <https://sections.readthedocs.io/en/latest/reference/#sections.Section.__call__>`_ as follows:

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

See the `Section.__call__() <https://sections.readthedocs.io/en/latest/reference/#sections.Section.__call__>`_ method in the References section of the docs for more options.

Set the default return type when accessing structure attributes by changing ``Section.default_gettype`` as follows:

.. code-block:: python

   menu = sections('Breakfast', 'Dinner', sides=['HashBrown', 'Fries'])

   menu['Breakfast'].default_gettype = dict  # set for only 'Breakfast' node
   assert menu.sides == ['HashBrown', 'Fries']
   assert menu['Breakfast']('side') == {'Breakfast': 'HashBrown'}

   menu.cls.default_gettype = dict           # set for all nodes in `menu`
   assert menu('sides') == {'Breakfast': 'HashBrown', 'Dinner': 'Fries'}
   assert menu['Breakfast']('side') == {'Breakfast': 'HashBrown'}

   sections.Section.default_gettype = dict   # set for all structures
   tasks1 = sections('pay bill', 'clean', status=['completed', 'started'])
   tasks2 = sections('pay bill', 'clean', status=['completed', 'started'])
   assert tasks1('statuses') == {'pay bill': 'completed', 'clean': 'started'}
   assert tasks2('statuses') == {'pay bill': 'completed', 'clean': 'started'}

The above will also work for accessing attributes in the form ``object.attr`` but only if the node does not contain the attribute ``attr``, otherwise it will return the non-iterable raw value for ``attr``. Therefore, for consistency, access attributes using `Section.__call__() <https://sections.readthedocs.io/en/latest/reference/#sections.Section.__call__>`_ like above if you wish to **always receive an iterable** form of the attributes.


Plural/singular attributes
==========================

When an attribute is not found in a Section node, both the plural and singular
forms of the word are then checked to see if the node contains the attribute
under those forms of the word. If they are still not found, the node will
recursively repeat the same search on each of its children, concatenating the
results into a list or dict. The true attribute name in each node supplied a
corresponding value is whatever name was given in the keyword argument’s key
(i.e. ``status`` in the example below).

If you don’t like this feature, simply turn it off using the following:

.. code-block:: python

   import pytest
   tasks = sections('pay bill', 'clean', status=['completed', 'started'])
   assert tasks.statuses == ['completed', 'started']
   # turn off for all future structures:
   sections.Section.use_pluralsingular = False
   tasks = sections('pay bill', 'clean', status=['completed', 'started'])
   with pytest.raises(AttributeError):
       tasks.statuses  # this now raises an AttributeError

Note, however, that this will still traverse descendant nodes to see if they
contain the requested attribute. To stop using this feature also, access
attributes using the `Section.get_node_attr() <https://sections.readthedocs.io/en/latest/reference/#sections.Section.get_node_attr>`_ method instead.


Properties/methods
==================

Each ``sections()`` call returns a structure containing nodes of a unique class created in a class factory function, where the unique class definition contains no logic except that it inherits from the Section class. This allows properties/methods added to one structure’s class definition to not affect the class definitions of nodes from other structures.


Subclassing
===========

Inheriting Section is easy, the only requirement is to call ``super().__init__(**kwds)`` at some point in ``__init__()``  like below if you override that method:

.. code-block:: python

   class Library(sections.Section):
       """My library class."""

       def __init__(self, price="Custom default value", **kwds):
           """Pass **kwds to super."""
           super().__init__(**kwds)
           self.price = price

       @property
       def genres(self):
           """A synonym for sections."""
           if self.isroot:
               return self.sections
           else:
               raise AttributeError('This library has only 1 level of genres')

       @property
       def books(self):
           """A synonym for leaves."""
           return self.leaves

       @property
       def titles(self):
           """A synonym for names."""
           return self.leaves.names

       def critique(self, review="Haven't read it yet", rating=0):
           """Set the book price based on the rating."""
           self.review = review
           self.price = rating * 2

   library = Library(
       [{'Fantasy'}, 'LOTR', 'Harry Potter'],
       [{'Academic'}, 'Advanced Math.', 'Physics for Engineers']
   )
   assert library.genres.names == ['Fantasy', 'Academic']
   assert library.books.titles == [
       'LOTR', 'Harry Potter', 'Advanced Math.', 'Physics for Engineers'
   ]
   library.books['LOTR'].critique(review='Good but too long', rating=7)
   library.books['Harry Potter'].critique(
       review="I don't like owls", rating=4)
   assert library.books['LOTR'].review == 'Good but too long'
   assert library.books['LOTR'].price == 14
   assert library.books['Harry Potter'].review == "I don't like owls"
   assert library.books['Harry Potter'].price == 8
   import pytest
   with pytest.raises(AttributeError):
       library['Fantasy'].genres

``Section.__init__()`` assigns the kwds values passed to it to the object attributes, and the passed kwds are generated during instantiation by a metaclass.


Performance
===========

Each non-leaf Section node keeps a cache containing quickly readable references to attribute dicts previously parsed from manually traversing through descendant nodes in an earlier read. The caches are invalidated accordingly for modified nodes and their ancestors when the tree structure or node attribute values change.

The caches allow instant reading of sub-lists/dicts in Θ(1) time and can often
make structure attribute reading faster by 5x, or even much more when the
structure is rarely being modified.
If preferred, turn this feature off to avoid the extra memory consumption it causes by modifying the node or structure’s class attribute ``use_cache`` to ``False`` as follows:

.. code-block:: python

   sect = sections(*[[[[[42] * 10] * 10] * 10] * 10])
   sect.use_cache = False              # turn off for just the root node
   sect.cls.use_cache = False          # turn off for all nodes in `sect`
   sections.Section.use_cache = False  # turn off for all structures
