################################################################################
#                                                                              #
#     sa2d_single_thread.py copyright 2015 Qiqi Wang (qiqi.wang@gmail.com)     #
#                                                                              #
################################################################################

from __future__ import division
import sys
import numbers
import unittest

import numpy as np
import theano
import theano.tensor as T

_VERBOSE_ = False

#==============================================================================#
#                                 grid2d class                                 #
#==============================================================================#

class grid2d(object):
    '''
    Provide "global" utility function for stencil_array family of classes
    '''
    def __init__(self, nx, ny):
        assert nx > 0
        assert ny > 0
        self._nx = int(nx)
        self._ny = int(ny)
        # switches between numpy and theano.tensor as needed
        self._math = np

    @property
    def nx(self):
        return self._nx

    @property
    def ny(self):
        return self._ny

    # -------------------------------------------------------------------- #
    #                             array utilities                          #
    # -------------------------------------------------------------------- #

    def _data_ndim(self, a, ndim):
        assert self is a.grid
        ndim_insert = ndim - a.ndim
        assert ndim_insert >= 0
        data_shape = (self.nx, self.ny) + (1,) * ndim_insert + a.shape
        return a._data.reshape(data_shape)

    def _preppend_shape(self, shape, a=None):
        if isinstance(shape, numbers.Number):
            shape = (shape,)
        else:
            shape = tuple(shape)
        return (self.nx, self.ny) + shape

    # -------------------------------------------------------------------- #
    #                           array constructors                         #
    # -------------------------------------------------------------------- #

    def _array(self, data, shape):
        if self._math is np:
            return psarray_numpy(self, data, shape)
        elif self._math is T:
            return psarray_theano(self, data, shape)

    def zeros(self, shape=()):
        shape = self._preppend_shape(shape)
        return self._array(self._math.zeros(shape), shape[2:])

    def ones(self, shape=()):
        shape = self._preppend_shape(shape)
        return self._array(self._math.ones(shape), shape[2:])

    def random(self, shape=()):
        shape = self._preppend_shape(shape)
        return self._array(self._math.random.random(shape), shape[2:])

    def load(self, filename):
        assert self._math is np
        data = np.load(filename)
        return self._array(data, data.shape[2:])

    @property
    def i(self):
        data = self._math.outer(self._math.arange(self.nx),
                                self._math.ones(self.ny))
        return self._array(data, ())

    @property
    def j(self):
        data = self._math.outer(self._math.ones(self.nx),
                                self._math.arange(self.ny))
        return self._array(data, ())

    # -------------------------------------------------------------------- #
    #                        array transformations                         #
    # -------------------------------------------------------------------- #

    def log(self, x):
        assert x.grid is self
        return self._array(self._math.log(x._data), x.shape)

    def exp(self, x):
        assert x.grid is self
        return self._array(self._math.exp(x._data), x.shape)

    def sin(self, x):
        assert x.grid is self
        return self._array(self._math.sin(x._data), x.shape)

    def cos(self, x):
        assert x.grid is self
        return self._array(self._math.cos(x._data), x.shape)

    def sum(self, x, axis=None):
        assert x.grid is self
        return x.sum(axis)

    def mean(self, x, axis=None):
        assert x.grid is self
        return x.mean(axis)

    def copy(self, x):
        assert x.grid is self
        return self._array(x._data.copy(), x.shape)

    def transpose(self, x, axes=None):
        assert x.grid is self
        if axes is None:
            axes = tuple(reversed(range(x.ndim)))
        data_axes = (0, 1) + tuple(i+2 for i in axes)
        data = x._data.transpose(data_axes)
        shape = tuple(x.shape[i] for i in axes)
        return self._array(data, shape)

    def roll(self, x, shift, axis=None):
        if axis is None:
            data = x._data.reshape((self.nx, self.ny, -1))
            data = self._math.roll(data, shift)
            data_shape = self._preppend_shape(x.shape, x)
            data = data.reshape(data_shape)
        else:
            data = self._math.roll(x._data, shift, axis+2)
        return self._array(data, x.shape)

    def reshape(self, x, shape):
        if isinstance(shape, int):
            shape = (shape,)
        data = x._data.reshape((self.nx, self.ny) + tuple(shape))
        return self._array(data, data.shape[2:])

    # -------------------------------------------------------------------- #
    #                            global operations                         #
    # -------------------------------------------------------------------- #

    def reduce_sum(self, a):
        assert a.grid == self
        return a._data.sum(axis=(0,1))

    def reduce_mean(self, a):
        assert a.grid == self
        return a._data.mean(axis=(0,1))

#==============================================================================#
#                               psarray base class                             #
#==============================================================================#

class psarray_base(object):
    def __init__(self, grid, data, shape):
        self.grid = grid
        assert grid.nx > 0
        assert grid.ny > 0
        self._data = data
        self._shape = shape
        self.__context__ = grid

    def copy(self):
        return self.grid.copy(self)

    # -------------------------------------------------------------------- #
    #                           size information                           #
    # -------------------------------------------------------------------- #

    def __len__(self):
        shape = self.shape
        return shape[0] if len(shape) else 1

    @property
    def shape(self):
        return self._shape

    @property
    def size(self):
        return np.prod(self.shape)

    @property
    def ndim(self):
        return len(self.shape)

    # -------------------------------------------------------------------- #
    #                               indexing                               #
    # -------------------------------------------------------------------- #

    def _data_index_(self, ind):
        if not isinstance(ind, tuple):
            ind = (ind,)
        ind = (slice(None),) * 2 + ind
        return ind

    def __getitem__(self, ind):
        shape = np.empty(self.shape)[ind].shape
        data_ind = self._data_index_(ind)
        return self.grid._array(self._data[data_ind], shape)


    # -------------------------------------------------------------------- #
    #                         access spatial neighbors                     #
    # -------------------------------------------------------------------- #

    @property
    def x_p(self):
        data = self.grid._math.roll(self._data, -1, axis=0)
        return self.grid._array(data, self.shape)

    @property
    def x_m(self):
        data = self.grid._math.roll(self._data, +1, axis=0)
        return self.grid._array(data, self.shape)

    @property
    def y_p(self):
        data = self.grid._math.roll(self._data, -1, axis=1)
        return self.grid._array(data, self.shape)

    @property
    def y_m(self):
        data = self.grid._math.roll(self._data, +1, axis=1)
        return self.grid._array(data, self.shape)

    # -------------------------------------------------------------------- #
    #                         algorithmic operations                       #
    # -------------------------------------------------------------------- #

    # asks ndarray to use the __rops__ defined in this class
    __array_priority__ = 2000

    def __neg__(self):
        return self.grid._array(-self._data, self.shape)

    def __radd__(self, a):
        return self.__add__(a)

    def __add__(self, a):
        if hasattr(a, '__array_priority__'):
            if a.__array_priority__ > self.__array_priority__:
                return a.__add__(self)
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            self_data = self.grid._data_ndim(self, ndim)
            a_data = self.grid._data_ndim(a, ndim)
            data = self_data + a_data

            shape = (np.zeros(self.shape) + np.zeros(a.shape)).shape
            return self.grid._array(data, shape)
        else:
            if hasattr(a, 'ndim'):
                data = self.grid._data_ndim(self, max(a.ndim, self.ndim))
            else:
                data = self._data
            shape = (np.zeros(self.shape) + a).shape
            return self.grid._array(data + a, shape)

    def __rsub__(self, a):
        return a + (-self)

    def __sub__(self, a):
        return self + (-a)

    def __rmul__(self, a):
        return self.__mul__(a)

    def __mul__(self, a):
        if hasattr(a, '__array_priority__'):
            if a.__array_priority__ > self.__array_priority__:
                return a.__rmul__(self)

        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            self_data = self.grid._data_ndim(self, ndim)
            a_data = self.grid._data_ndim(a, ndim)
            data = self_data * a_data

            shape = (np.zeros(self.shape) * np.zeros(a.shape)).shape
            return self.grid._array(data, shape)
        else:
            if hasattr(a, 'ndim'):
                data = self.grid._data_ndim(self, max(a.ndim, self.ndim))
            else:
                data = self._data
            shape = (np.zeros(self.shape) * a).shape
            return self.grid._array(data * a, shape)

    def __truediv__(self, a):
        if hasattr(a, '__array_priority__'):
            if a.__array_priority__ > self.__array_priority__:
                return a.__rtruediv__(self)

        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            self_data = self.grid._data_ndim(self, ndim)
            a_data = self.grid._data_ndim(a, ndim)
            data = self_data / a_data

            shape = (np.zeros(self.shape) / np.ones(a.shape)).shape
            return self.grid._array(data, shape)
        else:
            if hasattr(a, 'ndim'):
                data = self.grid._data_ndim(self, max(a.ndim, self.ndim))
            else:
                data = self._data
            shape = (np.zeros(self.shape) / a).shape
            return self.grid._array(data / a, shape)

    def __rtruediv__(self, a):
        if hasattr(a, 'ndim'):
            data = self.grid._data_ndim(self, max(a.ndim, self.ndim))
        else:
            data = self._data
        shape = (a / np.zeros(self.shape)).shape
        return self.grid._array(a / data, shape)

    def __pow__(self, a):
        if hasattr(a, '__array_priority__'):
            if a.__array_priority__ > self.__array_priority__:
                return a.__rpow__(self)

        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            self_data = self.grid._data_ndim(self, ndim)
            a_data = self.grid._data_ndim(a, ndim)
            data = self_data ** a_data

            shape = (np.ones(self.shape) ** np.ones(a.shape)).shape
            return self.grid._array(data, shape)
        else:
            if hasattr(a, 'ndim'):
                data = self.grid._data_ndim(self, max(a.ndim, self.ndim))
            else:
                data = self._data
            shape = (np.ones(self.shape) ** a).shape
            return self.grid._array(data ** a, shape)

    def __rpow__(self, a):
        if hasattr(a, 'ndim'):
            data = self.grid._data_ndim(self, max(a.ndim, self.ndim))
        else:
            data = self._data
        shape = (a ** np.ones(self.shape)).shape
        return self.grid._array(a ** data, shape)

    def sum(self, axis=None):
        if axis is None:
            axis = tuple(range(self.ndim))
        elif isinstance(axis, int):
            axis = (axis,)
        else:
            axis = tuple(axis)
        shape = np.ones(self.shape).sum(axis).shape
        axis = tuple(a + 2 for a in axis)
        return self.grid._array(self._data.sum(axis), shape)

    def mean(self, axis=None):
        if axis is None:
            axis = tuple(range(self.ndim))
        elif isinstance(axis, int):
            axis = (axis,)
        else:
            axis = tuple(axis)
        shape = np.ones(self.shape).sum(axis).shape
        axis = tuple(a + 2 for a in axis)
        return self.grid._array(self._data.mean(axis), shape)

    def transpose(self, axis=None):
        return self.grid.transpose(self, axis)

    @property
    def T(self):
        return self.grid.transpose(self)

    def reshape(self, shape):
        return self.grid.reshape(self, shape)


#==============================================================================#
#                        psarray class with numpy backend                      #
#==============================================================================#

class psarray_numpy(psarray_base):
    def __init__(self, grid, data, shape):
        assert isinstance(data, np.ndarray)
        psarray_base.__init__(self, grid, data, shape)

    # -------------------------------------------------------------------- #
    #                               indexing                               #
    # -------------------------------------------------------------------- #

    def __setitem__(self, ind, a):
        if hasattr(a, '__array_priority__'):
            assert a.__array_priority__ <= self.__array_priority__
        ind = self._data_index_(ind)
        if isinstance(a, psarray_numpy):
            assert a.grid is self.grid
            self._data[ind] = a._data
        else:
            self._data[ind] = a

    # -------------------------------------------------------------------- #
    #                           input / output                             #
    # -------------------------------------------------------------------- #

    def save(self, filename):
        np.save(filename, self._data)


#==============================================================================#
#                        psarray class with theano backend                     #
#==============================================================================#

class psarray_theano(psarray_base):
    def __init__(self, grid, data, shape):
        assert isinstance(data, (T.TensorVariable, np.ndarray))
        psarray_base.__init__(self, grid, data, shape)

    # -------------------------------------------------------------------- #
    #                               indexing                               #
    # -------------------------------------------------------------------- #

    def __setitem__(self, ind, a):
        if hasattr(a, '__array_priority__'):
            assert a.__array_priority__ <= self.__array_priority__
        ind = self._data_index_(ind)
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            self._data = T.set_subtensor(self._data[ind], a._data)
        else:
            self._data = T.set_subtensor(self._data[ind], a)


#==============================================================================#
#                             theano compilation                               #
#==============================================================================#

class psc_compile(object):
    def __init__(self, function):
        self._function = function
        self._compiled_function = None
        self._compiled_adjoint = None

    def __call__(self, u, *args, **kargs):
        if isinstance(u, psarray_theano):
            return self._function(u, *args, **kargs)
        assert isinstance(u, psarray_numpy)
        if not self._compiled_function:
            self._compiled_function = self.compile(u, *args, **kargs)
        data = self._compiled_function(u._data)
        return u.grid._array(data, data.shape[2:])

    def adjoint(self, out_adj, u, *args, **kargs):
        assert isinstance(u, psarray_numpy)
        if not self._compiled_adjoint:
            self._compiled_adjoint = self.compile_adjoint(u, *args, **kargs)
        data = self._compiled_adjoint(out_adj._data, u._data)
        return u.grid._array(data, data.shape[2:])

    def compile(self, u_np, *args, **kargs):
        grid = u_np.grid
        grid_math = grid._math
        grid._math = T

        tensor_dim = u_np.ndim + 2
        input_data = T.tensor('float64', (False,) * tensor_dim)

        u_theano = grid._array(input_data.copy(), u_np.shape)
        ret = self._function(u_theano, *args, **kargs)

        if _VERBOSE_: print('function evaluated in theano mode, compiling')
        f = theano.function([input_data], ret._data)
        if _VERBOSE_: print('function sucessfully compiled')

        grid._math = grid_math
        return f

    def compile_adjoint(self, u_np, *args, **kargs):
        grid = u_np.grid
        grid_math = grid._math
        grid._math = T

        tensor_dim = u_np.ndim + 2
        input_data = T.tensor('float64', (False,) * tensor_dim)

        u_theano = grid._array(input_data.copy(), u_np.shape)
        ret = self._function(u_theano, *args, **kargs)

        tensor_dim = ret.ndim + 2
        ret_adjoint = T.tensor('float64', (False,) * tensor_dim)
        J = (ret._data * ret_adjoint).sum()
        input_adjoint = T.grad(J, input_data)

        if _VERBOSE_: print('adjoint derived in theano mode, compiling')
        f = theano.function([ret_adjoint, input_data], input_adjoint)
        if _VERBOSE_: print('adjoint sucessfully compiled')

        grid._math = grid_math
        return f

################################################################################
################################################################################
################################################################################
