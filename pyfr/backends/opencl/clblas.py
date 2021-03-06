# -*- coding: utf-8 -*-

from ctypes import (CDLL, POINTER, c_int, c_double, c_float, c_size_t,
                    c_uint, c_void_p)

import numpy as np

from pyfr.backends.base import ComputeKernel, traits
from pyfr.ctypesutil import platform_libname


class ClBLASWrappers(object):
    def __init__(self, libname=None):
        libname = libname or platform_libname('clBLAS')

        try:
            lib = CDLL(libname)
        except OSError:
            raise RuntimeError('Unable to load clBLAS')

        # clblasSetup
        self.clblasSetup = lib.clblasSetup
        self.clblasSetup.argtypes = []
        self.clblasSetup.errcheck = self._errcheck

        # clblasTeardown
        self.clblasTeardown = lib.clblasTeardown
        self.clblasTeardown.argtypes = []
        self.clblasTeardown.restype = None

        # clblasSgemm
        self.clblasSgemm = lib.clblasSgemm
        self.clblasSgemm.argtypes = [
            c_int, c_int, c_int,  c_size_t, c_size_t, c_size_t,
            c_float, c_void_p, c_size_t, c_size_t,
            c_void_p, c_size_t, c_size_t, c_float,
            c_void_p, c_size_t, c_size_t,
            c_uint, POINTER(c_void_p),
            c_uint, POINTER(c_void_p), POINTER(c_void_p)
        ]
        self.clblasSgemm.errcheck = self._errcheck

        # clblasDgemm
        self.clblasDgemm = lib.clblasDgemm
        self.clblasDgemm.argtypes = [
            c_int, c_int, c_int, c_size_t, c_size_t, c_size_t,
            c_double, c_void_p, c_size_t, c_size_t,
            c_void_p, c_size_t, c_size_t, c_double,
            c_void_p, c_size_t, c_size_t,
            c_uint, POINTER(c_void_p),
            c_uint, POINTER(c_void_p), POINTER(c_void_p)
        ]
        self.clblasDgemm.errcheck = self._errcheck

    def _errcheck(self, status, fn, args):
        if status != 0:
            raise RuntimeError('clBLAS')


class OpenCLClBLASKernels(object):
    def __init__(self, backend):
        # Load and wrap clBLAS
        self._wrappers = ClBLASWrappers()

        # Init
        self._wrappers.clblasSetup()

    def __del__(self):
        self._wrappers.clblasTeardown()

    @traits(a={'dense'})
    def mul(self, a, b, out, alpha=1.0, beta=0.0):
        # Ensure the matrices are compatible
        if a.nrow != out.nrow or a.ncol != b.nrow or b.ncol != out.ncol:
            raise ValueError('Incompatible matrices for out = a*b')

        m, n, k = a.nrow, b.ncol, a.ncol

        if a.dtype == np.float64:
            clblasgemm = self._wrappers.clblasDgemm
        else:
            clblasgemm = self._wrappers.clblasSgemm

        class MulKernel(ComputeKernel):
            def run(self, qcomp, qcopy):
                clblasgemm(0, 0, 0, m, n, k, alpha,
                           a, 0, a.leaddim,
                           b, 0, b.leaddim, beta,
                           out, 0, out.leaddim,
                           1, c_void_p(qcomp.int_ptr), 0, None, None)

        return MulKernel()
