################################################################################
#                                                                              #
#          sa2d_mpi.py copyright 2016 Qiqi Wang (qiqi.wang@gmail.com)          #
#                                                                              #
################################################################################

from __future__ import division
from __future__ import unicode_literals
import sys
import numbers
import weakref
import doctest
import unittest
import operator
import time
import dill
import numpy as np
import theano
import theano.tensor as T
import mpi_worker_commander as commander

import sa2d_decomp

#==============================================================================#

def _is_like_sa(a):
    return hasattr(a, '_var') and isinstance(a._var, commander.WorkerVariable)

def _dummy(a):
    return a._dummy if _is_like_sa(a) else a

def _var(a):
    return a._var if _is_like_sa(a) else a

def _extend_ndim(a, ndim):
    if not hasattr(a, 'ndim'):
        return a
    else:
        assert a.ndim <= ndim
        if a.ndim == ndim:
            return a
        else:
            return a.reshape((1,) * (ndim - a.ndim) + a.shape)

#==============================================================================#
#                                                                              #
#==============================================================================#

def subdivide_rectangle(rect, max_squares):
    '''
    Subdivide a rectangle represented by rect=(x,y), into approximate
    squares.  The resulting subdivision balances two objectives.
    First, it tries to divide the large rectangle into identical rectangles
    that are as square as possible.  Second, it tries to maximize
    the number of rectangles, given that the number does not exceed
    the max_squares parameter.  Examples:

    >>> subdivide_rectangle((200, 200), 4)
    (2, 2)
    >>> subdivide_rectangle((100, 200), 4)
    (2, 2)
    >>> subdivide_rectangle((100, 300), 4)
    (1, 4)
    >>> subdivide_rectangle((100, 300), 8)
    (2, 4)
    >>> subdivide_rectangle((100, 200), 6)
    (2, 3)
    >>> subdivide_rectangle((300, 100), 6)
    (3, 2)
    >>> subdivide_rectangle((400, 100), 6)
    (6, 1)
    '''
    def aspect_ratio(nx, ny):
        x, y = rect
        x_square, y_square = x / nx, y / ny
        return min(x_square / y_square, y_square / x_square)

    class Subdivision:
        def __init__(self, nx, ny):
            self.n = (nx, ny)
            n_squares = float(nx * ny)
            self.score = aspect_ratio(nx, ny) + n_squares / max_squares * 4

    best_subdiv = Subdivision(1, 1)
    for num_cuts in range(max_squares):
        for num_x_cuts in range(num_cuts + 1):
            num_y_cuts = num_cuts - num_x_cuts
            nx, ny = num_x_cuts + 1, num_y_cuts + 1
            if nx * ny <= max_squares:
                subdiv = Subdivision(nx, ny)
                if subdiv.score > best_subdiv.score:
                    best_subdiv = subdiv

    return best_subdiv.n


#==============================================================================#
#                                 grid2d class                                 #
#==============================================================================#

class grid2d(object):
    '''
    Provides "global" utility function for array2d family of classes
    '''

    def __init__(self, nx, ny, num_processors):
        assert nx > 0
        assert ny > 0

        self._nx = int(nx)
        self._ny = int(ny)

        rect = (self._nx, self._ny)
        self._nxProc, self._nyProc = subdivide_rectangle(rect, num_processors)

        self._commander = commander.MPI_Commander(
                self._nx, self._ny, self._nxProc, self._nyProc)

        self._define_custom_functions()

        self._temp_vars = {}

    def delete(self):
        self._commander.dismiss()

    def __del__(self):
        self.delete()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.delete()
        return self

    def __repr__(self):
        return 'Grid at memory {0}\n\twith shape ' \
               '{1} x {2}, distributed on {3} x {4} MPI processes'.format(
               hex(id(self)), self._nx, self._ny, self._nxProc, self._nyProc)

    def _define_custom_functions(self):
        '''
        Define custom functions required by methods
        '''
        commander = self._commander
        commander.set_custom_func('make_worker_variable',
                lambda ZERO, x: x + ZERO.reshape(ZERO.shape + (1,) * x.ndim))
        commander.set_custom_func('reshape',
                lambda x, shape: x.reshape(x.shape[:2] + shape))
        commander.set_custom_func('func_with_interior', (
                lambda func, x, args, kwargs:
                       func(x[1:-1,1:-1], *args, **kwargs)))

    @property
    def nx(self):
        '''
        number of grid points in the x direction.
        '''
        return self._nx

    @property
    def ny(self):
        '''
        number of grid points in the y direction.
        '''
        return self._ny

    def _func(self, func, args=(), kwargs={}, is_nonuniform_args=False):
        '''
        Call a function defined in mpi_worker_commander.MPI_Commander
        with a fresh WorkerVariable, and return this WorkerVariable.

        Parameters
        ----------
        func : callable function (visible to mpi_worker_commander) or string
            specify the function to be called;
            if func is a string, it specifies a custom function defined by
            self._commander.set_custom_func.
        args : tuple
            Arguments to func, can contain WorkerVariable instances and
            other picklable objects.
        kwargs : dict
            Keyword arguments to func, can contain WorkerVariable instances and
            other picklable objects.

        Returns
        ----------
        var : newly created WorkerVariable instance,
            the result of the function call.
        '''
        result = commander.WorkerVariable()
        if is_nonuniform_args:
            self._commander.func_nonuniform_args(func, args, kwargs,
                    result_var=result, return_result=False)
        else:
            self._commander.func(func, args, kwargs, result_var=result,
                                 return_result=False)
        return result

    # -------------------------------------------------------------------- #
    #                           array constructors                         #
    # -------------------------------------------------------------------- #

    def _array(self, value, shape):
        '''
        Construct an array containing value of specified shape.

        Parameters
        ----------
        value : mpi_worker_commander.WorkerVariable
            specify the variable containing data
        shape : int or sequence of ints
            Shape of the new array, e.g., ``(2, 3)`` or ``2``.
        '''
        return stencil_array(self, value, shape)

    def zeros(self, shape=()):
        '''
        Return a new array of given shape and type, filled with zeros.

        Parameters
        ----------
        shape : int or sequence of ints
            Shape of the new array, e.g., ``(2, 3)`` or ``2``.

        Returns
        -------
        out : an array of zeros managed by the current grid.
        '''
        z = np.zeros(shape)
        res = self._func('make_worker_variable', (commander.ZERO, z))
        return self._array(res, z.shape)

    def ones(self, shape=()):
        '''
        Return a new array of given shape and type, filled with ones.

        Parameters
        ----------
        shape : int or sequence of ints
            Shape of the new array, e.g., ``(2, 3)`` or ``2``.

        Returns
        -------
        out : an array of ones managed by the current grid.
        '''
        o = np.ones(shape)
        res = self._func('make_worker_variable', (commander.ZERO, o))
        return self._array(res, o.shape)

    @property
    def i(self):
        '''
        An array containing i-index of a grid.
        '''
        return self._array(commander.I, ())

    @property
    def j(self):
        '''
        An array containing j-index of a grid.
        '''
        return self._array(commander.J, ())

    # -------------------------------------------------------------------- #
    #                        array transformations                         #
    # -------------------------------------------------------------------- #

    def log(self, x):
        '''
        Calculate the logorithm of all elements in the input array.
        '''
        assert _is_like_sa(x) and x.grid is self
        res = self._func(dill.dumps(np.log), (x._var,))
        return self._array(res, x.shape)

    def exp(self, x):
        '''
        Calculate the exponential of all elements in the input array.
        '''
        assert _is_like_sa(x) and x.grid is self
        res = self._func(dill.dumps(np.exp), (x._var,))
        return self._array(res, x.shape)

    def sin(self, x):
        '''
        Sine element-wise.
        '''
        assert _is_like_sa(x) and x.grid is self
        res = self._func(dill.dumps(np.sin), (x._var,))
        return self._array(res, x.shape)

    def cos(self, x):
        '''
        Cosine element-wise.
        '''
        assert _is_like_sa(x) and x.grid is self
        res = self._func(dill.dumps(np.cos), (x._var,))
        return self._array(res, x.shape)

    def sum(self, x, axis=None):
        '''
        Sum of array elements over a given axis.

        Parameters
        ----------
        a : array to sum; must live on this grid.
        axis : None or int or tuple of ints, optional
            Axis or axes along which a sum is performed.
            The default (`axis` = `None`) is perform a sum over all
            the dimensions of the input array. `axis` may be negative, in
            which case it counts from the last to the first axis.
            If this is a tuple of ints, a sum is performed on multiple
            axes, instead of a single axis or all the axes as before.

        Returns
        -------
        sum_along_axis : a new array on this grid, with a value
            at each grid point.
            An array with the same shape as `a`, with the specified
            axis removed.  If `a` is a 0-d array, or if `axis` is None, the
            result is a scalar on each grid point is returned.
        '''
        assert _is_like_sa(x) and x.grid is self
        if axis is None:
            axis = tuple(range(x.ndim))
        elif isinstance(axis, int):
            axis = (axis,)
        else:
            axis = tuple(axis)
        shape = x._dummy.sum(axis).shape
        axis = tuple(a + 2 for a in axis)
        res = self._func(np.sum, (x._var,), {'axis': axis})
        return self._array(res, shape)

    def mean(self, x, axis=None):
        '''
        Compute the arithmetic mean along the specified axis.

        Parameters
        ----------
        a : array to take the mean of; must live on this grid.
        axis : None or int or tuple of ints, optional
            Axis or axes along which a mean is taken
            The default (`axis` = `None`) is perform an average over all
            the dimensions of the input array. `axis` may be negative, in
            which case it counts from the last to the first axis.
            If this is a tuple of ints, a mean is taken on multiple
            axes, instead of a single axis or all the axes as before.

        Returns
        -------
        mean_along_axis : a new array on this grid, with a value
            at each grid point.
            An array with the same shape as `a`, with the specified
            axis removed.  If `a` is a 0-d array, or if `axis` is None, the
            result is a scalar on each grid point is returned.
        '''
        assert _is_like_sa(x) and x.grid is self
        if axis is None:
            axis = tuple(range(x.ndim))
        elif isinstance(axis, int):
            axis = (axis,)
        else:
            axis = tuple(axis)
        shape = x._dummy.sum(axis).shape
        axis = tuple(a + 2 for a in axis)
        res = self._func(np.mean, (x._var,), {'axis': axis})
        return self._array(res, shape)

    def copy(self, x):
        '''
        Return an array copy of the given object.
        '''
        assert _is_like_sa(x) and x.grid is self
        res = self._func(np.copy, (x._var,))
        return self._array(res, x.shape)

    def transpose(self, x, axes=None):
        '''
        Permute the dimensions of an array.

        Parameters
        ----------
        a : Input array on this grid.
        axes : list of ints, optional
            By default, reverse the dimensions, otherwise permute the axes
            according to the values given.

        Returns
        -------
        p : `a` with its axes permuted.
        '''
        assert _is_like_sa(x) and x.grid is self
        shape = np.transpose(x._dummy, axes).shape
        if axes is None:
            axes = [0, 1] + list(reversed(range(2, 2 + x.ndim)))
        else:
            axes = [0, 1] + list(2 + i for i in axes)
        res = self._func(np.transpose, (x._var,), {'axes': axes})
        return self._array(res, shape)

    def roll(self, a, shift, axis=None):
        '''
        Roll array elements along a given axis, emulating numpy's behavior.

        Parameters
        ----------
        a : Input array on this grid.
        shift : int
            The number of places by which elements are shifted.
        axis : int, optional
            The axis along which elements are shifted.  By default, the array
            is flattened before shifting, after which the original
            shape is restored.

        Returns
        -------
        res : Output array, with the same shape as `a`.
        '''
        if not hasattr(self, '_has_set_custom_func_roll_'):
            def func_roll(a, shift, axis):
                if axis is None:
                    shape = a.shape
                    a = a.reshape(a.shape[:2] + (-1,))
                    a = np.roll(a, shift, axis=2)
                    return a.reshape(shape)
                else:
                    return np.roll(a, shift, axis=axis+2)

            self._commander.set_custom_func('roll', func_roll)
            self._has_set_custom_func_roll_ = True

            # satisfy coverage.py
            func_roll(np.ones([1,1,2]), 1, None)
            func_roll(np.ones([1,1,2,2]), 1, 0)

        assert _is_like_sa(a) and a.grid is self
        res = self._func('roll', (a._var, shift, axis))
        return self._array(res, a.shape)

    def reshape(self, a, newshape):
        '''
        Gives a new shape to an array without changing its data.

        Parameters
        ----------
        a : array on this grid to be reshaped.
        newshape : int or tuple of ints
            The new shape should be compatible with the original shape. If
            an integer, then the result will be a 1-D array of that length.
            One shape dimension can be -1. In this case, the value is inferred
            from the length of the array and remaining dimensions.

        Returns
        -------
        reshaped_array
        '''
        assert _is_like_sa(a) and a.grid == self
        if isinstance(newshape, int):
            newshape = (newshape,)
        else:
            newshape = tuple(newshape)

        res = self._func('reshape', (a._var, newshape))
        shape = a._dummy.reshape(newshape).shape
        return self._array(res, shape)

    # -------------------------------------------------------------------- #
    #                            global operations                         #
    # -------------------------------------------------------------------- #

    def reduce_sum(self, a):
        '''
        Sum over all the grid points, returns an numpy array of the

        Parameters
        ----------
        a : array on this grid to be summed over the grid points

        Returns
        -------
        sum_a : a numpy array that has the same shape as a,
            one that does not live on this grid.
        '''
        assert _is_like_sa(a) and a.grid == self
        sum_a = self._commander.func('func_with_interior',
                (np.sum, a._var, (), {'axis': (0,1)}))
        sum_a = np.sum(sum_a, axis=0)
        assert sum_a.shape == a.shape
        return sum_a

    def reduce_mean(self, a):
        '''
        Average over all the grid points, returns an numpy array.

        Parameters
        ----------
        a : array on this grid to be averaged over the grid points

        Returns
        -------
        mean_a : a numpy array that has the same shape as a,
            one that does not live on this grid.
        '''
        assert _is_like_sa(a) and a.grid is self
        mean_a = self._commander.func('func_with_interior',
                (np.mean, a._var, (), {'axis': (0,1)}))
        mean_a = np.mean(mean_a, axis=0)
        assert mean_a.shape == a.shape
        return mean_a

    def _tile_data(self, data_iterable):
        data_tuple = tuple(data_iterable)
        assert len(data_tuple) == self._nxProc * self._nyProc
        data = []
        for ix in range(self._nxProc):
            data_ix = data_tuple[ix * self._nyProc: (ix + 1) * self._nyProc]
            data.append(np.concatenate(data_ix, axis=1))
        return np.concatenate(data, axis=0)

    def gather_all_data(self, a):
        assert _is_like_sa(a) and a.grid is self
        interior = (slice(1,-1), slice(1,-1))
        data_list = self._commander.method(a._var, '__getitem__', (interior,))
        return self._tile_data(data_list)

    def save(self, filename, a):
        np.save(filename, self.gather_all_data(a))

    def _decomp_data(self, big_data):
        assert big_data.ndim >= 2
        ni = self._commander.iRanges[-1][1]
        nj = self._commander.jRanges[-1][1]
        assert big_data.shape[:2] == (ni, nj)

        data_list = []
        for i0, i1 in self._commander.iRanges:
            for j0, j1 in self._commander.jRanges:
                data_list.append(big_data[i0:i1, j0:j1])
        return tuple(data_list)

    def from_data(self, big_data):
        decomp_data = self._decomp_data(big_data)
        res = self._func(np.array, tuple((data,) for data in decomp_data),
                is_nonuniform_args=True)
        return self._array(res, big_data.shape[2:])

    def load(self, filename):
        return self.from_data(np.load(filename))


#==============================================================================#
#                              stencil_array class                             #
#==============================================================================#

class stencil_array(object):
    '''
    A distributed array over mpi processes
    '''
    def __init__(self, grid, var, shape):
        self.grid = grid
        assert grid.nx > 0
        assert grid.ny > 0
        self._var = var
        self._dummy = np.ones(shape)
        self.__context__ = grid

        self._decomp_sa_value = sa2d_decomp.stencil_array_value(self.shape)
        self._decomp_sa_value._reference = self

    def __repr__(self):
        return repr(self.grid.gather_all_data(self)) \
                + '\n    of shape ' + repr(self.shape) \
                + ', living on ' + repr(self.grid)

    def __del__(self):
        self.grid._commander.delete_variable(self._var)

    def copy(self):
        return self.grid.copy(self)

    def _method(self, method_name, args=(), kwargs={}):
        result = commander.WorkerVariable()
        self.grid._commander.method(self._var, method_name, args, kwargs,
                result_var=result, return_result=False)
        return result

    # -------------------------------------------------------------------- #
    #                           size information                           #
    # -------------------------------------------------------------------- #

    def __len__(self):
        shape = self.shape
        return shape[0] if len(shape) else 1

    @property
    def shape(self):
        return self._dummy.shape

    @property
    def size(self):
        return np.prod(self.shape)

    @property
    def ndim(self):
        return len(self.shape)

    # -------------------------------------------------------------------- #
    #                               indexing                               #
    # -------------------------------------------------------------------- #

    def __getitem__(self, ind):
        shape = self._dummy.__getitem__(ind).shape
        if not isinstance(ind, tuple):
            ind = (ind,)
        data_ind = (slice(None), slice(None)) + ind
        res = self._method('__getitem__', (data_ind,))
        return self.grid._array(res, shape)

    def __setitem__(self, ind, a):
        if not isinstance(ind, tuple):
            ind = (ind,)
        ind = (slice(None), slice(None)) + ind
        self.grid._commander.method(self._var, '__setitem__', (ind, a._var),
                return_result=False)

    # -------------------------------------------------------------------- #
    #                         access spatial neighbors                     #
    # -------------------------------------------------------------------- #

    @property
    def x_p(self):
        res = self._method('__getitem__', ((slice(2,None), slice(1,-1)),))
        return self.grid._array(res, self.shape)

    @property
    def x_m(self):
        res = self._method('__getitem__', ((slice(None,-2), slice(1,-1)),))
        return self.grid._array(res, self.shape)

    @property
    def y_p(self):
        res = self._method('__getitem__', ((slice(1,-1), slice(2,None)),))
        return self.grid._array(res, self.shape)

    @property
    def y_m(self):
        res = self._method('__getitem__', ((slice(1,-1), slice(None,-2)),))
        return self.grid._array(res, self.shape)

    # -------------------------------------------------------------------- #
    #                         algorithmic operations                       #
    # -------------------------------------------------------------------- #

    # asks ndarray to use the __rops__ defined in this class
    __array_priority__ = 5000

    def __neg__(self):
        res = self._method('__neg__')
        return self.grid._array(res, self.shape)

    def __radd__(self, a):
        return self.__add__(a)

    def __add__(self, a):
        if sa2d_decomp._is_like_sa(a):
            return a.__add__(self._decomp_sa_value)

        shape = (_dummy(self) + _dummy(a)).shape
        self, a = _extend_ndim(self, len(shape)), _extend_ndim(a, len(shape))
        res = self.grid._func(operator.add, (_var(self), _var(a)))
        return self.grid._array(res, shape)

    def __rsub__(self, a):
        return a + (-self)

    def __sub__(self, a):
        return self + (-a)

    def __rmul__(self, a):
        return self.__mul__(a)

    def __mul__(self, a):
        if sa2d_decomp._is_like_sa(a):
            return a.__mul__(self._decomp_sa_value)

        shape = (_dummy(self) + _dummy(a)).shape
        self, a = _extend_ndim(self, len(shape)), _extend_ndim(a, len(shape))
        res = self.grid._func(operator.mul, (_var(self), _var(a)))
        return self.grid._array(res, shape)

    def __truediv__(self, a):
        if sa2d_decomp._is_like_sa(a):
            return a.__rtruediv__(self._decomp_sa_value)

        shape = (_dummy(self) + _dummy(a)).shape
        self, a = _extend_ndim(self, len(shape)), _extend_ndim(a, len(shape))
        res = self.grid._func(operator.truediv, (_var(self), _var(a)))
        return self.grid._array(res, shape)

    def __rtruediv__(self, a):
        if sa2d_decomp._is_like_sa(a):
            return a.__truediv__(self._decomp_sa_value)

        shape = (_dummy(self) + _dummy(a)).shape
        self, a = _extend_ndim(self, len(shape)), _extend_ndim(a, len(shape))
        res = self.grid._func(operator.truediv, (_var(a), _var(self)))
        return self.grid._array(res, shape)

    def __pow__(self, a):
        if sa2d_decomp._is_like_sa(a):
            return a.__rpow__(self._decomp_sa_value)

        shape = (_dummy(self) + _dummy(a)).shape
        self, a = _extend_ndim(self, len(shape)), _extend_ndim(a, len(shape))
        res = self.grid._func(operator.pow, (_var(self), _var(a)))
        return self.grid._array(res, shape)

    def __rpow__(self, a):
        if sa2d_decomp._is_like_sa(a):
            return a.__pow__(self._decomp_sa_value)

        shape = (_dummy(self) + _dummy(a)).shape
        self, a = _extend_ndim(self, len(shape)), _extend_ndim(a, len(shape))
        res = self.grid._func(operator.pow, (_var(a), _var(self)))
        return self.grid._array(res, shape)

    def sum(self, axis=None):
        return self.grid.sum(self, axis)

    def mean(self, axis=None):
        return self.grid.mean(self, axis)

    def transpose(self, axes=None):
        return self.grid.transpose(self, axes)

    @property
    def T(self):
        return self.grid.transpose(self)

    def reshape(self, shape):
        return self.grid.reshape(self, shape)

    # -------------------------------------------------------------------- #
    #                           input / output                             #
    # -------------------------------------------------------------------- #

    def save(self, filename):
        self.grid.save(filename, self)



#==============================================================================#
#                                  unit tests                                  #
#==============================================================================#

class TestGridLife(unittest.TestCase):
    def testDelete(self):
        G = grid2d(16, 8, 2)
        del G

    def testGarbageCollection(self):
        import gc
        G = grid2d(16, 8, 2)
        a = G.ones(3)
        b = G.ones((1,3))
        c = a + b
        del a, b, c, G
        gc.collect()

# ---------------------------------------------------------------------------- #

class TestOperation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.G = grid2d(32, 16, 2)

    @classmethod
    def tearDownClass(cls):
        cls.G.delete()

    def testLogMean(self):
        a = self.G.ones()
        b = self.G.log(a)
        b2_sum = self.G.reduce_sum((b ** 2))
        self.assertAlmostEqual(b2_sum, 0)

    def testSinSum(self):
        a = np.pi + self.G.zeros()
        b = self.G.sin(a)
        b2_sum = self.G.reduce_sum((b ** 2))
        self.assertAlmostEqual(b2_sum, 0)

    def testTransposeCopy(self):
        a = 1 - self.G.zeros([2,3,4])
        b = a.T
        self.assertEqual(len(b), 4)
        self.assertEqual(b.size, 24)
        self.assertAlmostEqual(self.G.reduce_mean(b.sum(2).mean()), 2)
        self.assertAlmostEqual(self.G.reduce_mean(b.sum([1,2]).mean()), 6)
        c = a.copy().transpose([0,2,1])
        self.assertEqual(len(c), 2)
        self.assertEqual(c.size, 24)
        self.assertAlmostEqual(self.G.reduce_mean(c.mean(2).sum()), 8)
        self.assertAlmostEqual(self.G.reduce_mean(c.mean([1,2]).sum()), 2)

    def testRoll(self):
        a = self.G.zeros([2,1]) + np.arange(3) + 3 * np.arange(2)[:,np.newaxis]
        b = self.G.roll(a, 1).reshape(6)
        self.assertEqual(self.G.reduce_mean(b[0]), 5)
        self.assertEqual(self.G.reduce_mean(b[1]), 0)
        c = self.G.roll(a, 1, axis=1)
        self.assertEqual(self.G.reduce_mean(c[0,0]), 2)
        self.assertEqual(self.G.reduce_mean(c[0,1]), 0)
        self.assertEqual(self.G.reduce_mean(c[1,0]), 5)
        self.assertEqual(self.G.reduce_mean(c[1,1]), 3)

# ---------------------------------------------------------------------------- #

class TestReduction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.G = grid2d(32, 16, 2)

    @classmethod
    def tearDownClass(cls):
        cls.G.delete()

    def testReduceSum(self):
        a = 1 / self.G.ones()
        a_sum = self.G.reduce_sum(a)
        self.assertEqual(a_sum, 32 * 16)

    def testReduceMean(self):
        a = self.G.ones()
        a_mean = self.G.reduce_mean(a)
        self.assertEqual(a_mean, 1)

    def testPrint(self):
        a = 10 ** self.G.ones()
        self.assertTrue(isinstance(repr(a), str))

    def testSaveLoad(self):
        a = self.G.ones()
        a.save('_tmp.npy')
        b = self.G.load('_tmp.npy')
        import os
        os.unlink('_tmp.npy')
        self.assertEqual(self.G.reduce_sum((a - b)**2), 0)

# ---------------------------------------------------------------------------- #

class InteractWithDecomp(unittest.TestCase):
    def testOp(self):
        import sa2d_decomp
        b = sa2d_decomp.stencil_array()
        with grid2d(8,4,2) as G:
            a = G.ones()
            c = a + b
            self.assertTrue(isinstance(c, sa2d_decomp.stencil_array))
            c = a - b
            self.assertTrue(isinstance(c, sa2d_decomp.stencil_array))
            c = a * b
            self.assertTrue(isinstance(c, sa2d_decomp.stencil_array))
            c = a / b
            self.assertTrue(isinstance(c, sa2d_decomp.stencil_array))
            c = a ** b
            self.assertTrue(isinstance(c, sa2d_decomp.stencil_array))
            c = b / a
            self.assertTrue(isinstance(c, sa2d_decomp.stencil_array))
            c = b ** a
            self.assertTrue(isinstance(c, sa2d_decomp.stencil_array))


# ---------------------------------------------------------------------------- #

class CompareSerialMPI(unittest.TestCase):
    def testEuler(self):
        DISS_COEFF = 0.0025
        gamma, R = 1.4, 287.
        T0, p0, M0 = 300., 101325., 0.25

        rho0 = p0 / (R * T0)
        c0 = np.sqrt(gamma * R * T0)
        u0 = c0 * M0
        w0 = np.array([np.sqrt(rho0), np.sqrt(rho0) * u0, 0., p0])

        Lx, Ly = 40., 10.
        dx = dy = 0.25
        dt = dx / c0 * 0.5

        def EulerSteps(grid):
            # ------------------------------------------------------------ #
            #                        PROBLEM SET UP                        #
            # ------------------------------------------------------------ #

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
                # conservative, negative definite dissipation
                # applied to r*d(ru)/dt
                laplace = lambda u: (u.x_p + u.x_m + u.y_p + u.y_m) * 0.25 - u
                return laplace(dc * r * r * laplace(u))

            def rhs(w):
                r, ru, rv, p = w
                u, v = ru / r, rv / r

                mass = diffx(r * ru) + diffy(r * rv)
                momentum_x = (diffx(ru*ru) + (r*ru) * diffx(u)) / 2.0 \
                           + (diffy(rv*ru) + (r*rv) * diffy(u)) / 2.0 \
                           + diffx(p)
                momentum_y = (diffx(ru*rv) + (r*ru) * diffx(v)) / 2.0 \
                           + (diffy(rv*rv) + (r*rv) * diffy(v)) / 2.0 \
                           + diffy(p)
                energy = gamma * (diffx(p * u) + diffy(p * v)) \
                       - (gamma - 1) * (u * diffx(p) + v * diffy(p))

                one = grid.ones(r.shape)
                dissipation_x = dissipation(r, u, DISS_COEFF) * c0 / dx
                dissipation_y = dissipation(r, v, DISS_COEFF) * c0 / dy
                dissipation_p = dissipation(one, p, DISS_COEFF) * c0 / dx

                momentum_x += dissipation_x
                momentum_y += dissipation_y
                energy += dissipation_p \
                        - (gamma - 1) * (u * dissipation_x + v * dissipation_y)

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

            w0 = grid.zeros()
            w0 += np.array([np.sqrt(rho0), np.sqrt(rho0) * u0, 0., p0])
            w1 = step(w0)
            return w1

        with grid2d(int(Lx / dx), int(Ly / dy), 3) as grid:
            w1 = EulerSteps(grid)
            w1_mpi = grid.gather_all_data(w1)

        import sa2d_single_thread
        grid_serial = sa2d_single_thread.grid2d(int(Lx / dx), int(Ly / dy))
        w1 = EulerSteps(grid_serial)
        w1_serial = w1._data

        self.assertAlmostEqual(np.abs(w1_mpi - w1_serial).max(), 0)


#==============================================================================#

if __name__ == '__main__':
    unittest.main()
