============
Known Issues
============
This document intends to record any known long-standing issues/limitations with Cyclopts.
While this document should always be up to date, please also `visit the github-issues page <https://github.com/BrianPugh/cyclopts/issues>`_ for more information & discussion.

``from __future__ import annotations``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Due to quirks in the python-typing system, Cyclopts can only support some scenarios surrounding `PEP-0563`_, the strinigization of type hints via ``from __future__ import annotations``.
Notably, this can also sometimes break ``dataclass`` definitions when inheritance from multiple python modules is involved.
Attempts have been made to improve Cyclopts support, but there are the following blockers:

1. CPython has `some bugs <https://github.com/python/cpython/issues/89687>`_ around :func:`typing.get_type_hints`. It is outside the scope of Cyclopts to compensate for the complex task of type-hint scoping and resolution.

2. Particularly with dataclasses, it looks like they will be fixing these bugs, but it would only be backported to `3.13 and 3.14 <https://github.com/python/cpython/issues/133956#issuecomment-2883646533>`_.
   This limitation to very modern python versions makes a lot of PEP-0563 moot.

3. `PEP-0649`_ and `PEP-0749`_ deprecate the usage of ``from __future__ import annotations``. This suggests that it is not worth the long-term maintenance of supporting the complications of this feature.


`Original discussion on GitHub. <https://github.com/BrianPugh/cyclopts/issues/439>`_



.. _PEP-0563: https://peps.python.org/563
.. _PEP-0649: https://peps.python.org/649
.. _PEP-0749: https://peps.python.org/749
