=========
Changelog
=========

------------------
0.0.0 (2021-06-23)
------------------

* First release on PyPI

------------------
0.0.1 (2021-06-25)
------------------

* Refactor code into smaller classes and files
* Update Section.deep_string()
* Update readme/docs

------------------
0.0.2 (2021-06-26)
------------------

* Fix bug when using Section.leaves or Section.children
* Add tests/test_indepth_usage.py
* Update readme/docs

------------------
0.0.3
------------------

* improve __str__ to be visually intuitive
* add descendants, flat properties
* add insert methods
* add feature for default attr to search for in __call__
* can add lists as node attrs if attr name starts with '_'
* make plural_singular work for properties/methods also
* add structure_change() function for use when subclassing
* add testcases
* safer internal attrs prefix/rename classes with Section prefix
