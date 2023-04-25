========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - |
        |
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|
.. |docs| image:: https://readthedocs.org/projects/debug/badge/?style=flat
    :target: https://debug.readthedocs.io/
    :alt: Documentation Status

.. |version| image:: https://img.shields.io/pypi/v/debug.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/debug

.. |wheel| image:: https://img.shields.io/pypi/wheel/debug.svg
    :alt: PyPI Wheel
    :target: https://pypi.org/project/debug

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/debug.svg
    :alt: Supported versions
    :target: https://pypi.org/project/debug

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/debug.svg
    :alt: Supported implementations
    :target: https://pypi.org/project/debug

.. |commits-since| image:: https://img.shields.io/github/commits-since/trevorpogue/debug/v0.0.0.svg
    :alt: Commits since latest release
    :target: https://github.com/trevorpogue/debug/compare/v0.0.0...master



.. end-badges

Debugging and logging tools that automatically print variable values and source code context around Exceptions or
log/print statements.

Installation
============

::

    pip install debug

You can also install the in-development version with::

    pip install https://github.com/trevorpogue/debug/archive/master.zip


Documentation
=============


https://debug.readthedocs.io/


Development
===========

To run all the tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
