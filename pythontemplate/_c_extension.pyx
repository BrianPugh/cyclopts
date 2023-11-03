cimport cpythontemplate
# Invoke PyErr_CheckSignals occasionally if your C code runs long.
# This allows your code to be interrupted via ctrl+c.
from cpython.exc cimport PyErr_CheckSignals
from cpython.mem cimport PyMem_Malloc, PyMem_Free
from libc.stddef cimport size_t


cdef class Foo:
    cdef cpythontemplate.foo_t * _object

    def __cinit__(self):
        # Allocate objects here
        self._object = <cpythontemplate.foo_t *>PyMem_Malloc(sizeof(cpythontemplate.foo_t))
        if self._object is NULL:
            raise MemoryError

    def __dealloc__(self):
        PyMem_Free(self._object)

    def __init__(self):
        cpythontemplate.foo_init(self._object)

    def __call__(self):
        # invoke increment
        cpythontemplate.foo_increment(self._object)
