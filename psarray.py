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

    def array(self, init_func):
        if self._math is np:
            return psarray_numpy(self, init_func)
        elif self._math is T:
            return psarray_theano(self, init_func)

    def zeros(self, shape):
        shape = self._preppend_shape(shape)
        a = self.array(None)
        a.shape = shape[2:]
        a._data = self._math.zeros(shape)
        return a

    def ones(self, shape):
        shape = self._preppend_shape(shape)
        a = self.array(None)
        a.shape = shape[2:]
        a._data = self._math.ones(shape)
        return a

    def random(self, shape=()):
        shape = self._preppend_shape(shape)
        a = self.array(None)
        a.shape = shape[2:]
        a._data = self._math.random.random(shape)
        return a

    def load(self, filename):
        assert self._math is np
        a = self.array(None)
        a._data = np.load(filename)
        a.shape = a._data.shape[2:]
        return a

    # -------------------------------------------------------------------- #
    #                        array transformations                         #
    # -------------------------------------------------------------------- #

    def log(self, x):
        assert x.grid is self
        y = self.array(None)
        y._data = self._math.log(x._data)
        y.shape = x.shape
        return y

    def exp(self, x):
        assert x.grid is self
        y = self.array(None)
        y._data = self._math.exp(x._data)
        y.shape = x.shape
        return y

    def sin(self, x):
        assert x.grid is self
        y = self.array(None)
        y._data = self._math.sin(x._data)
        y.shape = x.shape
        return y

    def cos(self, x):
        assert x.grid is self
        y = self.array(None)
        y._data = self._math.cos(x._data)
        y.shape = x.shape
        return y

    def copy(self, x):
        assert x.grid is self
        y = self.array(None)
        y._data = x._data.copy()
        y.shape = x.shape
        return y

    def ravel(self, x):
        assert x.grid is self
        y = self.array(None)
        y._data = x._data.reshape(y.shape + (y.size,))
        y.shape = (y.size,)
        return y

    def transpose(self, x, axes=None):
        assert x.grid is self
        y = self.array(None)
        if axes is None:
            axes = reversed(tuple(range(x.ndim)))
        axes = (0, 1) + tuple(i+2 for i in axes)
        y._data = x._data.transpose(axes)
        y.shape = (x.shape[i] for i in axes)
        return y


    # -------------------------------------------------------------------- #
    #                            global operations                         #
    # -------------------------------------------------------------------- #

    def sum(self, a):
        assert a.grid == self
        return a._data.sum(axis=(0,1))

#==============================================================================#
#                               psarray base class                             #
#==============================================================================#

class psarray_base(object):
    def __init__(self, grid):
        self.grid = grid
        assert grid.nx > 0
        assert grid.ny > 0

    def copy(self):
        return self.grid.copy(self)

    # -------------------------------------------------------------------- #
    #                           size information                           #
    # -------------------------------------------------------------------- #

    def __len__(self):
        shape = self.shape
        return shape[0] if len(shape) else 1

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
        a = self.grid.array(None)
        a.shape = np.empty(self.shape)[ind].shape
        ind = self._data_index_(ind)
        a._data = self._data[ind]
        return a


    # -------------------------------------------------------------------- #
    #                         access spatial neighbors                     #
    # -------------------------------------------------------------------- #

    @property
    def x_p(self):
        y = self.grid.array(None)
        y._data = self.grid._math.roll(self._data, -1, axis=0)
        y.shape = self.shape
        return y

    @property
    def x_m(self):
        y = self.grid.array(None)
        y._data = self.grid._math.roll(self._data, +1, axis=0)
        y.shape = self.shape
        return y

    @property
    def y_p(self):
        y = self.grid.array(None)
        y._data = self.grid._math.roll(self._data, -1, axis=1)
        y.shape = self.shape
        return y

    @property
    def y_m(self):
        y = self.grid.array(None)
        y._data = self.grid._math.roll(self._data, +1, axis=1)
        y.shape = self.shape
        return y

    # -------------------------------------------------------------------- #
    #                         algorithmic operations                       #
    # -------------------------------------------------------------------- #

    def __neg__(self):
        y = self.grid.array(None)
        y._data = -self._data
        y.shape = self.shape
        return y

    def __radd__(self, a):
        return self.__add__(a)

    def __add__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            y = self.grid.array(None)
            y._data = self.grid._data_ndim(self, ndim) \
                    + self.grid._data_ndim(a, ndim)
            y.shape = (np.zeros(self.shape) + np.zeros(a.shape)).shape
        else:
            if hasattr(a, 'ndim'):
                data = self.grid._data_ndim(self, max(a.ndim, self.ndim))
            else:
                data = self._data
            y = self.grid.array(None)
            y._data = data + a
            y.shape = (np.zeros(self.shape) + a).shape
        return y

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

            y = self.grid.array(None)
            y._data = self.grid._data_ndim(self, ndim) \
                    * self.grid._data_ndim(a, ndim)
            y.shape = (np.zeros(self.shape) * np.zeros(a.shape)).shape
        else:
            if hasattr(a, 'ndim'):
                data = self.grid._data_ndim(self, max(a.ndim, self.ndim))
            else:
                data = self._data
            y = self.grid.array(None)
            y._data = data * a
            y.shape = (np.zeros(self.shape) * a).shape
        return y

    def __div__(self, a):
        return self.__truediv__(a)

    def __truediv__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            y = self.grid.array(None)
            y._data = self.grid._data_ndim(self, ndim) \
                    / self.grid._data_ndim(a, ndim)
            y.shape = (np.zeros(self.shape) / np.ones(a.shape)).shape
        else:
            if hasattr(a, 'ndim'):
                data = self.grid._data_ndim(self, max(a.ndim, self.ndim))
            else:
                data = self._data
            y = self.grid.array(None)
            y._data = data / a
            y.shape = (np.zeros(self.shape) / a).shape
        return y

    def __rdiv__(self, a):
        return self.__rtruediv__(a)

    def __rtruediv__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            y = self.grid.array(None)
            y._data = self.grid._data_ndim(a, ndim) \
                    / self.grid._data_ndim(self, ndim)
            y.shape = (np.ones(a.shape) / np.zeros(self.shape)).shape
        else:
            if hasattr(a, 'ndim'):
                data = self.grid._data_ndim(self, max(a.ndim, self.ndim))
            else:
                data = self._data
            y = self.grid.array(None)
            y._data = a / data
            y.shape = (a / np.zeros(self.shape)).shape
        return y

    def __pow__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            y = self.grid.array(None)
            y._data = self.grid._data_ndim(self, ndim) \
                    ** self.grid._data_ndim(a, ndim)
            y.shape = (np.ones(self.shape) ** np.ones(a.shape)).shape
        else:
            if hasattr(a, 'ndim'):
                data = self.grid._data_ndim(self, max(a.ndim, self.ndim))
            else:
                data = self._data
            y = self.grid.array(None)
            y._data = data ** a
            y.shape = (np.ones(self.shape) ** a).shape
        return y

    def sum(self, axis=None):
        y = self.grid.array(None)
        y._data = self._data.sum(axis)
        y.shape = y._data.shape[2:]
        return y


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
    def __init__(self, grid, init_func):
        psarray_base.__init__(self, grid)

        if init_func:
            j, i = np.meshgrid(np.arange(self.grid.ny), np.arange(self.grid.nx))
            data = np.array(init_func(i, j))

            # roll the last two axes, i and j, to the first two
            data = np.rollaxis(data, -1)
            data = np.rollaxis(data, -1)

            self._data = np.array(data, dtype=np.float64, order='C')
            self.shape = self._data.shape[2:]

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
    def __init__(self, grid, init_func):
        psarray_base.__init__(self, grid)

        if init_func:
            raw_data = np.array(init(grid._i, grid._j))
            self.shape = raw_data.shape

            # rollaxis
            while raw_data.ndim > 0:
                new_shape = raw_data.shape[1:]
                new_data = []
                for i in itertools.product(*(range(n) for n in new_shape)):
                    ds = raw_data[(slice(None),) + i]
                    ds = [T.shape_padright(d.astype('float64')) for d in ds]
                    new_data.append(T.concatenate(ds, axis=-1))
                raw_data = np.array(new_data).reshape(new_shape)

            self._data = new_data[0]

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
        ret = u.grid.array(None)
        ret._data = self._compiled_function(u._data)
        ret.shape = ret._data.shape[2:]
        return ret

    def adjoint(self, out_adj, u, *args, **kargs):
        assert isinstance(u, psarray_numpy)
        if not self._compiled_adjoint:
            self._compiled_adjoint = self.compile_adjoint(u, *args, **kargs)
        in_adj = u.grid.array(None)
        in_adj._data = self._compiled_adjoint(out_adj._data, u._data)
        in_adj.shape = in_adj._data.shape[2:]
        return in_adj

    def compile(self, u_np, *args, **kargs):
        grid = u_np.grid
        grid_math = grid._math
        grid._math = T

        tensor_dim = u_np.ndim + 2
        input_data = T.TensorType('float64', (False,) * tensor_dim)()

        u_theano = grid.array(None)
        u_theano._data = input_data.copy()
        u_theano.shape = u_np.shape

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

        u_theano = grid.array(None)
        u_theano._data = input_data.copy()
        u_theano.shape = u_np.shape

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
