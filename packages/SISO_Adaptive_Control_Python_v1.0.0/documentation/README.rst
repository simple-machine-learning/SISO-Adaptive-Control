Sphinx documentation
====================

Build on Windows from the project root::

   python -m pip install -r documentation\requirements.txt
   python -m sphinx -b html documentation documentation\_build\html

Build on Linux from the project root::

   python -m pip install -r documentation/requirements.txt
   python -m sphinx -b html documentation documentation/_build/html

Generated entry point
---------------------

Windows::

   documentation\_build\html\index.html

Linux::

   documentation/_build/html/index.html
