################################################################################
#                                                                              #
#            psarray.py copyright 2015 Qiqi Wang (qiqi.wang@gmail.com)         #
#                                                                              #
################################################################################

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

    def _preppend_shape(self, shape):
        if isinstance(shape, numbers.Number):
            shape = (shape,)
        else:
            shape = tuple(shape)
        return (self.nx, self.ny) + shape

    # -------------------------------------------------------------------- #
    #                           array constructors                         #
    # -------------------------------------------------------------------- #

    def array(self, data, shape):
        if self._math is np:
            return psarray_numpy(self, data, shape)
        elif self._math is T:
            return psarray_theano(self, data, shape)

    def zeros(self, shape):
        shape = self._preppend_shape(shape)
        return self.array(self._math.zeros(shape), shape[2:])

    def ones(self, shape):
        shape = self._preppend_shape(shape)
        return self.array(self._math.ones(shape), shape[2:])

    def random(self, shape=()):
        shape = self._preppend_shape(shape)
        return self.array(self._math.random.random(shape), shape[2:])

    def load(self, filename):
        assert self._math is np
        return self.array(np.load(filename), a._data.shape[2:])

    @property
    def i(self):
        data = self._math.outer(self._math.arange(self.nx),
                                self._math.ones(self.ny))
        return self.array(data, ())

    @property
    def j(self):
        data = self._math.outer(self._math.ones(self.nx),
                                self._math.arange(self.ny))
        return self.array(data, ())

    # -------------------------------------------------------------------- #
    #                        array transformations                         #
    # -------------------------------------------------------------------- #

    def log(self, x):
        assert x.grid is self
        return self.array(self._math.log(x._data), x.shape)

    def exp(self, x):
        assert x.grid is self
        return self.array(self._math.exp(x._data), x.shape)

    def sin(self, x):
        assert x.grid is self
        return self.array(self._math.sin(x._data), x.shape)

    def cos(self, x):
        assert x.grid is self
        return self.array(self._math.cos(x._data), x.shape)

    def copy(self, x):
        assert x.grid is self
        return self.array(x._data.copy(), x.shape)

    def transpose(self, x, axes=None):
        assert x.grid is self
        if axes is None:
            axes = reversed(tuple(range(x.ndim)))
        axes = (0, 1) + tuple(i+2 for i in axes)
        return self.array(x._data.transpose(axes), (x.shape[i] for i in axes))


    # -------------------------------------------------------------------- #
    #                            global operations                         #
    # -------------------------------------------------------------------- #

    def reduce_sum(self, a):
        assert a.grid == self
        return a._data.sum(axis=(0,1))

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
        data_ind = self._data_index_(ind)
        shape = np.empty(self.shape)[ind].shape
        return self.grid.array(self._data[data_ind], shape)


    # -------------------------------------------------------------------- #
    #                         access spatial neighbors                     #
    # -------------------------------------------------------------------- #

    @property
    def x_p(self):
        data = self.grid._math.roll(self._data, -1, axis=0)
        return self.grid.array(data, self.shape)

    @property
    def x_m(self):
        data = self.grid._math.roll(self._data, +1, axis=0)
        return self.grid.array(data, self.shape)

    @property
    def y_p(self):
        data = self.grid._math.roll(self._data, -1, axis=1)
        return self.grid.array(data, self.shape)

    @property
    def y_m(self):
        data = self.grid._math.roll(self._data, +1, axis=1)
        return self.grid.array(data, self.shape)

    # -------------------------------------------------------------------- #
    #                         algorithmic operations                       #
    # -------------------------------------------------------------------- #

    def __neg__(self):
        return self.grid.array(-self._data, self.shape)

    def __radd__(self, a):
        return self.__add__(a)

    def __add__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            data = self.grid._data_ndim(self, ndim) \
                 + self.grid._data_ndim(a, ndim)
            shape = (np.zeros(self.shape) + np.zeros(a.shape)).shape
            return self.grid.array(data, shape)
        else:
            if hasattr(a, 'ndim'):
                data = self.grid._data_ndim(self, max(a.ndim, self.ndim))
            else:
                data = self._data
            shape = (np.zeros(self.shape) + a).shape
            return self.grid.array(data + a, shape)

    def __rsub__(self, a):
        return a + (-self)

    def __sub__(self, a):
        return self + (-a)

    def __rmul__(self, a):
        return self.__mul__(a)

    def __mul__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            data = self.grid._data_ndim(self, ndim) \
                 * self.grid._data_ndim(a, ndim)
            shape = (np.zeros(self.shape) * np.zeros(a.shape)).shape
            return self.grid.array(data, shape)
        else:
            if hasattr(a, 'ndim'):
                data = self.grid._data_ndim(self, max(a.ndim, self.ndim))
            else:
                data = self._data
            shape = (np.zeros(self.shape) * a).shape
            return self.grid.array(data * a, shape)

    def __div__(self, a):
        return self.__truediv__(a)

    def __truediv__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            data = self.grid._data_ndim(self, ndim) \
                 / self.grid._data_ndim(a, ndim)
            shape = (np.zeros(self.shape) / np.ones(a.shape)).shape
            return self.grid.array(data, shape)
        else:
            if hasattr(a, 'ndim'):
                data = self.grid._data_ndim(self, max(a.ndim, self.ndim))
            else:
                data = self._data
            shape = (np.zeros(self.shape) / a).shape
            return self.grid.array(data / a, shape)

    def __rdiv__(self, a):
        return self.__rtruediv__(a)

    def __rtruediv__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            data = self.grid._data_ndim(a, ndim) \
                 / self.grid._data_ndim(self, ndim)
            shape = (np.ones(a.shape) / np.zeros(self.shape)).shape
            return self.grid.array(data, shape)
        else:
            if hasattr(a, 'ndim'):
                data = self.grid._data_ndim(self, max(a.ndim, self.ndim))
            else:
                data = self._data
            shape = (a / np.zeros(self.shape)).shape
            return self.grid.array(a / data, shape)

    def __pow__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            data = self.grid._data_ndim(self, ndim) \
                 ** self.grid._data_ndim(a, ndim)
            shape = (np.ones(self.shape) ** np.ones(a.shape)).shape
            return self.grid.array(data, shape)
        else:
            if hasattr(a, 'ndim'):
                data = self.grid._data_ndim(self, max(a.ndim, self.ndim))
            else:
                data = self._data
            shape = (np.ones(self.shape) ** a).shape
            return self.grid.array(data ** a, shape)

    def sum(self, axis=None):
        if axis is None:
            data = self._data.reshape((self.grid.nx, self.grid.ny, -1)).sum(2)
            return self.grid.array(data, ())
        else:
            shape = np.ones(self.shape).sum(axis).shape
            return self.grid.array(self._data.sum(axis + 2), shape)


#==============================================================================#
#                           replace numpy operations                           #
#==============================================================================#

if np.set_numeric_ops()['add'] == np.add:
    def _add(x1, x2, out=None):
        if isinstance(x2, psarray_base):
            return x2.__add__(x1)
        else:
            return np.add(x1, x2, out)
    np.set_numeric_ops(add=_add)

if np.set_numeric_ops()['subtract'] == np.subtract:
    def _sub(x1, x2, out=None):
        if isinstance(x2, psarray_base):
            return (-x2).__add__(x1)
        else:
            return np.subtract(x1, x2, out)
    np.set_numeric_ops(subtract=_sub)

if np.set_numeric_ops()['multiply'] == np.multiply:
    def _mul(x1, x2, out=None):
        if isinstance(x2, psarray_base):
            return x2.__mul__(x1)
        else:
            return np.multiply(x1, x2, out)
    np.set_numeric_ops(multiply=_mul)

if np.set_numeric_ops()['true_divide'] == np.true_divide:
    def _div(x1, x2, out=None):
        if isinstance(x2, psarray_base):
            return (x2**(-1)).__mul__(x1)
        else:
            return np.true_divide(x1, x2, out)
    np.set_numeric_ops(divide=_div)
    np.set_numeric_ops(true_divide=_div)

#==============================================================================#
#                        psarray class with numpy backend                      #
#==============================================================================#

class psarray_numpy(psarray_base):
    # -------------------------------------------------------------------- #
    #                               indexing                               #
    # -------------------------------------------------------------------- #

    def __setitem__(self, ind, a):
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
    # -------------------------------------------------------------------- #
    #                               indexing                               #
    # -------------------------------------------------------------------- #

    def __setitem__(self, ind, a):
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
        return u.grid.array(data, data.shape[2:])

    def adjoint(self, out_adj, u, *args, **kargs):
        assert isinstance(u, psarray_numpy)
        if not self._compiled_adjoint:
            self._compiled_adjoint = self.compile_adjoint(u, *args, **kargs)
        data = self._compiled_adjoint(out_adj._data, u._data)
        return u.grid.array(data, data.shape[2:])

    def compile(self, u_np, *args, **kargs):
        grid = u_np.grid
        grid_math = grid._math
        grid._math = T

        tensor_dim = u_np.ndim + 2
        input_data = T.TensorType('float64', (False,) * tensor_dim)()

        u_theano = grid.array(input_data.copy(), u_np.shape)
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
        input_data = T.TensorType('float64', (False,) * tensor_dim)()

        u_theano = grid.array(input_data.copy(), u_np.shape)
        ret = self._function(u_theano, *args, **kargs)

        tensor_dim = ret.ndim + 2
        ret_adjoint = T.TensorType('float64', (False,) * tensor_dim)()
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
        self._testOp(lambda x : 1 + x, 3)
        self._testOp(lambda x : x + 1, 3)

        self._testOp(lambda x : x + np.ones(3), 3)
        self._testOp(lambda x : np.ones(3) + x, 3)
        self._testOp(lambda x : np.ones([4,2,3]) + x + np.ones([3]), [2,3])

        G = self.G
        self._testOp(lambda x : x + G.ones(3), 3)
        self._testOp(lambda x : G.ones(3) + x, 3)
        self._testOp(lambda x : G.ones([4,2,3]) + x + G.ones([3]), [2,3])

    def testSub(self):
        self._testOp(lambda x : 1 - x, 3)
        self._testOp(lambda x : x - 1, 3)

        self._testOp(lambda x : x - np.ones(3), 3)
        self._testOp(lambda x : np.ones(3) - x, 3)
        self._testOp(lambda x : np.ones([4,2,3]) - x - np.ones([3]), [2,3])

        G = self.G
        self._testOp(lambda x : x - G.ones(3), 3)
        self._testOp(lambda x : G.ones(3) - x, 3)
        self._testOp(lambda x : G.ones([4,2,3]) - x - G.ones([3]), [2,3])

    def testMul(self):
        self._testOp(lambda x : 1 * x, 3)
        self._testOp(lambda x : x * 1, 3)

        self._testOp(lambda x : x * np.ones(3), 3)
        self._testOp(lambda x : np.ones(3) * x, 3)
        self._testOp(lambda x : np.ones([4,2,3]) * x * np.ones([3]), [2,3])

        G = self.G
        self._testOp(lambda x : x * G.ones(3), 3)
        self._testOp(lambda x : G.ones(3) * x, 3)
        self._testOp(lambda x : G.ones([4,2,3]) * x * G.ones([3]), [2,3])

    def testDiv(self):
        self._testOp(lambda x : 1 / x, 3)
        self._testOp(lambda x : x / 1, 3)

        self._testOp(lambda x : x / np.ones(3), 3)
        self._testOp(lambda x : np.ones(3) / x, 3)
        self._testOp(lambda x : np.ones([4,2,3]) / x / np.ones([3]), [2,3])

        G = self.G
        self._testOp(lambda x : x / G.ones(3), 3)
        self._testOp(lambda x : G.ones(3) / x, 3)
        self._testOp(lambda x : G.ones([4,2,3]) / x / G.ones([3]), [2,3])

    def testUnivariate(self):
        def test01(x):
            x += 1
            return x
        self._testOp(test01, 3)

    def testSum(self):
        self._testOp(lambda x : x.sum(), 3)
        self._testOp(lambda x : x.sum(), (3, 4))
        self._testOp(lambda x : x.sum(axis=0), (3, 4))
        self._testOp(lambda x : x.sum(axis=1), (3, 4))


class _Indexing(_OpTest):
    def testGet(self):
        self._testOp(lambda x : x[2], (3,))
        self._testOp(lambda x : x[:], (3,))
        self._testOp(lambda x : x[:,0], (3, 4))
        self._testOp(lambda x : x[:,:2], (3, 4))
        self._testOp(lambda x : x[:-2,2:2:2], (3, 4))
        self._testOp(lambda x : x[:,np.newaxis] * x[np.newaxis,:], (4,))
        self._testOp(lambda x : x[np.newaxis,:-2,2:2:2], (3, 4))
        self._testOp(lambda x : x[:-2,np.newaxis,2:2:2], (3, 4))


class _Adjoint(_OpTest):
    def testSimple(self):
        x = self.G.ones(3) * 2
        a = self.G.ones(3) * 5

        f = psc_compile(lambda x : x * x)
        g = f.adjoint(a, x)
        self.assertAlmostEqual(0, np.linalg.norm((g - a * x * 2)._data))

        f = psc_compile(lambda x : self.G.exp(x))
        g = f.adjoint(a, x)
        self.assertAlmostEqual(0, np.linalg.norm((g - a * self.G.exp(x))._data))

# ---------------------------------------------------------------------------- #

if __name__ == '__main__':
    # _VERBOSE_ = True
    unittest.main()


################################################################################
################################################################################
################################################################################
