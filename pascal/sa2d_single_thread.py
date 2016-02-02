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


#==============================================================================#
#                                  unit tests                                  #
#==============================================================================#

class _OpTest(unittest.TestCase):
    def __init__(self, *args, **kargs):
        unittest.TestCase.__init__(self, *args, **kargs)
        self.G = grid2d(8,8)

    def _testOp(self, func, x_shp):
        x = self.G.ones(x_shp)
        y0 = func(x)
        y1 = psc_compile(func)(x)
        self.assertAlmostEqual(0, np.abs((y0 - y1)._data).sum())


class _MathOps(_OpTest):
    def testAdd(self):
        self._testOp(lambda x: 1 + x, 3)
        self._testOp(lambda x: x + 1, 3)

        self._testOp(lambda x: x + np.ones(3), 3)
        self._testOp(lambda x: np.ones(3) + x, 3)
        self._testOp(lambda x: np.ones([4,2,3]) + x + np.ones([3]), [2,3])

        G = self.G
        self._testOp(lambda x: x + G.ones(3), 3)
        self._testOp(lambda x: G.ones(3) + x, 3)
        self._testOp(lambda x: G.ones([4,2,3]) + x + G.ones([3]), [2,3])

    def testSub(self):
        self._testOp(lambda x: 1 - x, 3)
        self._testOp(lambda x: x - 1, 3)

        self._testOp(lambda x: x - np.ones(3), 3)
        self._testOp(lambda x: np.ones(3) - x, 3)
        self._testOp(lambda x: np.ones([4,2,3]) - x - np.ones([3]), [2,3])

        G = self.G
        self._testOp(lambda x: x - G.ones(3), 3)
        self._testOp(lambda x: G.ones(3) - x, 3)
        self._testOp(lambda x: G.ones([4,2,3]) - x - G.ones([3]), [2,3])

    def testMul(self):
        self._testOp(lambda x: 1 * x, 3)
        self._testOp(lambda x: x * 1, 3)

        self._testOp(lambda x: x * np.ones(3), 3)
        self._testOp(lambda x: np.ones(3) * x, 3)
        self._testOp(lambda x: np.ones([4,2,3]) * x * np.ones([3]), [2,3])

        G = self.G
        self._testOp(lambda x: x * G.ones(3), 3)
        self._testOp(lambda x: G.ones(3) * x, 3)
        self._testOp(lambda x: G.ones([4,2,3]) * x * G.ones([3]), [2,3])

    def testDiv(self):
        self._testOp(lambda x: 1 / x, 3)
        self._testOp(lambda x: x / 1, 3)

        self._testOp(lambda x: x / np.ones(3), 3)
        self._testOp(lambda x: np.ones(3) / x, 3)
        self._testOp(lambda x: np.ones([4,2,3]) / x / np.ones([3]), [2,3])

        G = self.G
        self._testOp(lambda x: x / G.ones(3), 3)
        self._testOp(lambda x: G.ones(3) / x, 3)
        self._testOp(lambda x: G.ones([4,2,3]) / x / G.ones([3]), [2,3])

        a = G.ones(())
        self._testOp(lambda x: x / a, 3)
        self._testOp(lambda x: a / x, 3)
        self._testOp(lambda x: (a / x) / x, 3)

    def testPow(self):
        self._testOp(lambda x: x ** x, 3)
        self._testOp(lambda x: 2 ** x, 3)
        self._testOp(lambda x: x ** 2, 3)
        self._testOp(lambda x: np.ones(3) ** x, 3)
        self._testOp(lambda x: x ** np.ones(3), 3)

    def testUnivariate(self):
        G = self.G
        def test01(x):
            x += G.log(x) + G.sin(x) * G.sum(x) - G.mean(x) + G.mean(x,0)
            x[0] = 1
            return x
        self._testOp(test01, 3)

    def testSumMean(self):
        self._testOp(lambda x: x.sum(), 3)
        self._testOp(lambda x: x.sum(), (3, 4))
        self._testOp(lambda x: x.sum(axis=0), (3, 4))
        self._testOp(lambda x: x.sum(axis=1), (3, 4))
        self._testOp(lambda x: x.sum(axis=[0,1]), (3, 4))
        self._testOp(lambda x: x.mean(), 3)
        self._testOp(lambda x: x.mean(), (3, 4))
        self._testOp(lambda x: x.mean(axis=0), (3, 4))
        self._testOp(lambda x: x.mean(axis=1), (3, 4))
        self._testOp(lambda x: x.mean(axis=[0,1]), (3, 4))

    def testReshapeReduce(self):
        G = self.G
        self._testOp(lambda x: x.reshape(12), (3, 4))
        self._testOp(lambda x: x + G.reduce_sum(x), (3, 4))
        self._testOp(lambda x: x.copy() - G.reduce_mean(x), (3, 4))


class _Indexing(_OpTest):
    def testGet(self):
        self._testOp(lambda x: x[2], (3,))
        self._testOp(lambda x: x[:], (3,))
        self._testOp(lambda x: x[:,0], (3, 4))
        self._testOp(lambda x: x[:,:2], (3, 4))
        self._testOp(lambda x: x[:-2,2:2:2], (3, 4))
        self._testOp(lambda x: x[:,np.newaxis] * x[np.newaxis,:], (4,))
        self._testOp(lambda x: x[np.newaxis,:-2,2:2:2], (3, 4))
        self._testOp(lambda x: x[:-2,np.newaxis,2:2:2], (3, 4))


class _Transforms(_OpTest):
    def testTranspose(self):
        self._testOp(lambda x: x.T, 2)
        self._testOp(lambda x: x.T, (2, 4))
        self._testOp(lambda x: x.T, (2, 3, 4))
        self._testOp(lambda x: x.transpose([2,0,1]), (2, 3, 4))

    def testRoll(self):
        self._testOp(lambda x: self.G.roll(x,1), (3, 4))
        self._testOp(lambda x: self.G.roll(x,-2), (3, 4))
        self._testOp(lambda x: self.G.roll(x,1,0), (3, 4))
        self._testOp(lambda x: self.G.roll(x,-2,1), (3, 4))

class _Misc(_OpTest):
    def testSizes(self):
        G = self.G
        x = G.zeros([3,4])
        self.assertEqual(x.size, 12)
        self.assertEqual(len(x), 3)

    def testRandom(self):
        x = self.G.random((10,2))
        self.assertEqual(x.shape, (10,2))

    def testPowerClass(self):
        class PowerClass(object):
            __array_priority__ = 10000000
            __add__ = lambda self, a: 1
            __rmul__ = lambda self, a: 2
            __truediv__ = lambda self, a: 3
            __rtruediv__ = lambda self, a: 4
            __pow__ = lambda self, a: 5
            __rpow__ = lambda self, a: 6

        a = PowerClass()
        b = self.G.ones(3)
        self.assertEqual(a + b, 1)
        self.assertEqual(b + a, 1)
        self.assertEqual(a - b, 1)
        self.assertEqual(a * b, 2)
        self.assertEqual(b * a, 2)
        self.assertEqual(a / b, 3)
        self.assertEqual(b / a, 4)
        self.assertEqual(a ** b, 5)
        self.assertEqual(b ** a, 6)

class _Adjoint(_OpTest):
    def testSimple(self):
        x = self.G.ones(3) * 2
        a = self.G.ones(3) * 5

        f = psc_compile(lambda x: x * x)
        g = f.adjoint(a, x)
        self.assertAlmostEqual(0, np.linalg.norm((g - a * x * 2)._data))

        f = psc_compile(lambda x: self.G.exp(x))
        g = f.adjoint(a, x)
        self.assertAlmostEqual(0, np.linalg.norm((g - a * self.G.exp(x))._data))


class _DoubleCompile(_OpTest):
    def testDC(self):
        f = psc_compile(lambda x: x * x)
        g = psc_compile(lambda x: f(x * x) ** 2)
        x = g(self.G.ones(3))
        self.assertEqual(x.shape, (3,))


class _SaveLoad(_OpTest):
    def testSL(self):
        x = self.G.ones(3)
        x.save('test')
        y = self.G.load('test.npy')
        self.assertAlmostEqual(self.G.reduce_sum((x - y)**2).sum(), 0)


class _Euler(_OpTest):
    def testTunnel(self):
        # ------------------------------------------------------------ #
        #                        PROBLEM SET UP                        #
        # ------------------------------------------------------------ #

        DISS_COEFF = 0.0025
        gamma, R = 1.4, 287.
        T0, p0, M0 = 300., 101325., 0.25

        rho0 = p0 / (R * T0)
        c0 = np.sqrt(gamma * R * T0)
        u0 = c0 * M0
        w0 = np.array([np.sqrt(rho0), np.sqrt(rho0) * u0, 0., p0])

        Lx, Ly = 40., 10.
        dx = dy = 0.05
        dt = dx / c0 * 0.5

        grid = grid2d(int(Lx / dx), int(Ly / dy))

        x = (grid.i + 0.5) * dx - 0.2 * Lx
        y = (grid.j + 0.5) * dy - 0.5 * Ly

        obstacle = grid.exp(-((x**2 + y**2) / 1)**64)

        fan = 2 * grid.cos((x / Lx + 0.2) * np.pi)**64

        nPrintsPerPlot, nStepPerPrint = 400, 5

        # ------------------------------------------------------------ #
        #                FINITE DIFFERENCE DISCRETIZATION              #
        # ------------------------------------------------------------ #

        def diffx(w):
            return (w.x_p - w.x_m) / (2 * dx)

        def diffy(w):
            return (w.y_p - w.y_m) / (2 * dy)

        def dissipation(r, u, dc):
            # conservative, negative definite dissipation applied to r*d(ru)/dt
            laplace = lambda u: (u.x_p + u.x_m + u.y_p + u.y_m) * 0.25 - u
            return laplace(dc * r * r * laplace(u))

        def rhs(w):
            r, ru, rv, p = w
            u, v = ru / r, rv / r

            mass = diffx(r * ru) + diffy(r * rv)
            momentum_x = (
                    (diffx(ru*ru) + (r*ru) * diffx(u)) / 2.0 +
                    (diffy(rv*ru) + (r*rv) * diffy(u)) / 2.0
                    ) + diffx(p)
            momentum_y = (
                    (diffx(ru*rv) + (r*ru) * diffx(v)) / 2.0 +
                    (diffy(rv*rv) + (r*rv) * diffy(v)) / 2.0
                    ) + diffy(p)
            energy = (
                    gamma * (diffx(p * u) + diffy(p * v)) -
                    (gamma - 1) * (u * diffx(p) + v * diffy(p))
                    )

            one = grid.ones(r.shape)
            dissipation_x = dissipation(r, u, DISS_COEFF) * c0 / dx
            dissipation_y = dissipation(r, v, DISS_COEFF) * c0 / dy
            dissipation_p = dissipation(one, p, DISS_COEFF) * c0 / dx

            momentum_x += dissipation_x
            momentum_y += dissipation_y
            energy += (
                    dissipation_p -
                    (gamma - 1) * (u * dissipation_x + v * dissipation_y)
                    )

            rhs_w = grid.zeros(w.shape)
            rhs_w[0] = 0.5 * mass / r
            rhs_w[1] = momentum_x / r
            rhs_w[2] = momentum_y / r
            rhs_w[-1] = energy

            rhs_w[1:3] += 0.1 * c0 * obstacle * w[1:3]
            rhs_w += 0.1 * c0 * (w - w0) * fan

            return rhs_w

        def step(w):
            dw0 = -dt * rhs(w)
            dw1 = -dt * rhs(w + 0.5 * dw0)
            dw2 = -dt * rhs(w + 0.5 * dw1)
            dw3 = -dt * rhs(w + dw2)
            return w + (dw0 + dw3) / 6 + (dw1 + dw2) / 3

        w0 = grid.ones(4)
        w1 = step(w0)
        w1_theano = psc_compile(step)(w0)
        self.assertAlmostEqual(0, np.abs((w1 - w1_theano)._data).sum())


################################################################################
################################################################################
################################################################################
