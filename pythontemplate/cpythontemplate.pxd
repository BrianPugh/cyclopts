"""Primary cimport.

This file acts as an interface between cython and C header files.

Other pyx files will be able to "cimport cpythontemplate" to gain
access to functions and structures defined here.

This file should be a simple translation from existing c header file(s).
Multiple header files may be translated here.
"""

from libcpp cimport bool
from libc.stdint cimport uint8_t, uint32_t

cdef extern from "foo.h":
    # Translate typedef'd structs:
    ctypedef struct foo_t:
        int counter

    # Translate enums:
    ctypedef enum foo_res_t:
        FOO_OK = 0,

    # Typical function declaration
    void foo_init(foo_t * foo);
    void foo_increment(foo_t * foo);
