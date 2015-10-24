################################################################################
#                                                                              #
#            psarray.py copyright 2015 Qiqi Wang (qiqi.wang@gmail.com)         #
#                                                                              #
################################################################################

import time
import numbers
import unittest
import itertools
import multiprocessing
import numpy as np
import theano
import theano.tensor as T

_VERBOSE_ = False

#==============================================================================#
#                               grid2d worker                                  #
#==============================================================================#

def grid2d_worker_main(commandPipe, iRange, commArray):
    '''
    Each worker process executes this function.
    Expressions sent from director only has access to local variables
    and functions of this function.  To these expressions, these local
    variables and functions are effective global variables and functions.
    '''
    # --------------------------------------------------------------------- #
    #                          "global" variables                           #
    # --------------------------------------------------------------------- #

    (ixStart, ixEnd), (iyStart, iyEnd) = iRange
    iWorker, ((comm_x_m, comm_x_p), (comm_y_m, comm_y_p)) = commArray

    V, _V_with_ghost = {}, {}
    math = np

    # --------------------------------------------------------------------- #
    #                        "global" utility functions                     #
    # --------------------------------------------------------------------- #

    def prepend_shape(shape):
        return (ixEnd - ixStart, iyEnd - iyStart) + shape

    def data_ndim(a, ndim):
        ndim_insert = ndim + 2 - a.ndim
        assert ndim_insert >= 0
        dataShape = a.shape[:2] + (1,) * ndim_insert + a.shape[2:]
        return a.reshape(dataShape)

    def del_V(key):
        del V[key]
        if key in _V_with_ghost:
            del _V_with_ghost[key]

    # --------------------------------------------------------------------- #
    #                           neighbor access                             #
    # --------------------------------------------------------------------- #

    def _update_V_with_ghost(key):
        if key not in _V_with_ghost:
            v = V[key]
            comm_x_p.send(v[-1,:]); comm_x_m.send(v[0,:])
            comm_y_p.send(v[:,-1]); comm_y_m.send(v[:,0])

            shape_with_ghost = (v.shape[0] + 2, v.shape[1] + 2) + v.shape[2:]
            _V_with_ghost[key] = np.empty(shape_with_ghost)
            _V_with_ghost[key][1:-1,1:-1] = v

            _V_with_ghost[key][0,1:-1] = comm_x_m.recv()
            _V_with_ghost[key][-1,1:-1] = comm_x_p.recv()
            _V_with_ghost[key][1:-1,0] = comm_y_m.recv()
            _V_with_ghost[key][1:-1,-1] = comm_y_p.recv()

    def _invalidate_ghost(key):
        if key in _V_with_ghost:
            del _V_with_ghost[key]

    def x_p(key):
        _update_V_with_ghost(key)
        return _V_with_ghost[key][2:,1:-1]

    def x_m(key):
        _update_V_with_ghost(key)
        return _V_with_ghost[key][:-2,1:-1]

    def y_p(key):
        _update_V_with_ghost(key)
        return _V_with_ghost[key][1:-1,2:]

    def y_m(key):
        _update_V_with_ghost(key)
        return _V_with_ghost[key][1:-1,:-2]

    # --------------------------------------------------------------------- #
    #                           main event loop                             #
    # --------------------------------------------------------------------- #

    while True:
        varKey, varIndex, expression, data, wantResult = commandPipe.recv()
        try:
            if varKey == 'KILL':
                return
            elif varKey is None:
                result = eval(expression, {}, locals())
                if wantResult:
                    commandPipe.send(result)
            elif varIndex is None:
                V[varKey] = eval(expression, {}, locals())
            else:
                V[varKey][varIndex] = eval(expression, {}, locals())
                _invalidate_ghost(varKey)
        except Exception as e:
            print('Worker {0} CRASH caused by'.format(iWorker) + \
                  '\n\tk:{0}\n\ti:{1}\n\te:{2}\n\td:{3}\n'.format(
                   varKey, varIndex, expression, data) + \
                  str(e) + '\n')
            raise


#==============================================================================#
#                              grid2d helper functions                         #
#==============================================================================#

class CommandPipe(object):
    def __init__(self, nWorkers):
        self.directors, self.listeners = [], []
        for i in range(nWorkers):
            p0, p1 = multiprocessing.Pipe()
            self.directors.append(p0)
            self.listeners.append(p1)

    def exec_async(self, expression, data=None):
        for p in self.directors:
            p.send((None, None, expression, data, False))

    def assign_async(self, varKey, expression, data=None):
        for p in self.directors:
            p.send((varKey, None, expression, data, False))

    def assign_with_index_async(self, varKey, varIndex, expression, data=None):
        for p in self.directors:
            p.send((varKey, varIndex, expression, data, False))

    def eval_sync(self, expression, data=None):
        for p in self.directors:
            p.send((None, None, expression, data, True))
        return tuple(p.recv() for p in self.directors) 

    def kill(self):
        for p in self.directors:
            p.send(('KILL', None, None, None, None))


def assign_i_ranges(nx, ny, nxWorkers, nyWorkers):
    'return a tuple of ((ixStart, ixEnd), (iyStart, iyEnd)) quads'
    def assign_1d_ranges(n, nRanges):
        'return a generator of (iStart,iEnd) pairs'
        i_boundary = lambda i : int(i * n / nRanges)
        return ((i_boundary(i), i_boundary(i+1)) for i in range(nRanges))
    ixRanges = assign_1d_ranges(nx, nxWorkers)
    iyRanges = assign_1d_ranges(ny, nyWorkers)
    return tuple(itertools.product(ixRanges, iyRanges))


def make_comm_arrays(nxWorkers, nyWorkers):
    '''
    return a tuple of periodically connected,
    ((p_xm, p_xp), (p_ym, p_yp)) pipe quads
    '''
    class iter_1d_comm_arrays(object):
        '''
        iterator that returns circular pairs of pipes
        that links backward and forward
        '''
        def __init__(self, n):
            self.n = n
        def __iter__(self):
            pipes = np.array([multiprocessing.Pipe() for i in range(self.n)])
            for pair in zip(pipes[:,0], np.roll(pipes[:,1], -1)):
                yield pair

    def product_without_duplication(xGen, yGen):
        '''
        Similar to itertools.product, except what's returned are not
        duplicate alias of each other, but individually generated
        '''
        comm = [[] for x in xGen]
        for iy, y in enumerate(yGen):
            for ix, x in enumerate(xGen):
                comm[ix].append(x)
        for ix, x in enumerate(xGen):
            for iy, y in enumerate(yGen):
                yield comm[ix][iy], y

    return tuple(enumerate(product_without_duplication(
        iter_1d_comm_arrays(nxWorkers), iter_1d_comm_arrays(nyWorkers))))



#==============================================================================#
#                                 grid2d class                                 #
#==============================================================================#

class grid2d(object):
    def __init__(self, nx, ny, nxWorkers, nyWorkers):
        assert nx > 0
        assert ny > 0

        self._nx = int(nx)
        self._ny = int(ny)
        
        self._nxWorkers = int(nxWorkers)
        self._nyWorkers = int(nyWorkers)

        self._commandPipe = CommandPipe(nxWorkers * nyWorkers)
        self._iRanges = assign_i_ranges(nx, ny, nxWorkers, nyWorkers)
        self._commArrays = make_comm_arrays(nxWorkers, nyWorkers)

        def make_worker(commandPipe, iRange, commArray):
            return multiprocessing.Process(target=grid2d_worker_main,
                    args=(commandPipe, iRange, commArray))

        self._workers = tuple(map(make_worker,
            self._commandPipe.listeners, self._iRanges, self._commArrays))
        for w in self._workers:
            w.start()
        assert len(self._workers) == nxWorkers * nyWorkers

        self._math = np

        self._var_key_number = 0

    def __del__(self):
        self._commandPipe.kill()
        for w in self._workers:
            w.join()


    @property
    def nx(self):
        return self._nx

    @property
    def ny(self):
        return self._ny

    # -------------------------------------------------------------------- #
    #                             array utilities                          #
    # -------------------------------------------------------------------- #

    def _new_var_key_(self, a):
        key = self._var_key_number
        self._var_key_number += 1
        return key

    def _del_var_key_(self, key):
        self._commandPipe.exec_async('del_V({0})'.format(key))

    # -------------------------------------------------------------------- #
    #                           array constructors                         #
    # -------------------------------------------------------------------- #

    def _array(self, workerCommand, shape, data=None):
        shape = np.empty(shape).shape
        if self._math is np:
            return psarray_numpy(self, workerCommand, data, shape)
        elif self._math is T:
            return psarray_theano(self, workerCommand, data, shape)

    def zeros(self, shape):
        expr = 'math.zeros(prepend_shape({0}))'
        return self._array(expr.format(str(np.empty(shape).shape)), shape)

    def ones(self, shape):
        expr = 'math.ones(prepend_shape({0}))'
        return self._array(expr.format(str(np.empty(shape).shape)), shape)

    def random(self, shape=()):
        expr = 'math.random.random(preppend_shape({0}))'
        return self._array(expr.format(str(np.empty(shape).shape)), shape)

    # def load(self, filename):
    #     assert self._math is np
    #     data = np.load(filename)
    #     return self._array(data, data.shape[2:])

    @property
    def i(self):
        expr = '''math.outer(math.arange(ixStart, ixEnd),
                            math.ones(iyEnd - iyStart))'''
        return self._array(expr, ())

    @property
    def j(self):
        expr = '''math.outer(math.ones(ixEnd - ixStart),
                            math.arange(iyStart, iyEnd))'''
        return self._array(expr, ())

    # -------------------------------------------------------------------- #
    #                        array transformations                         #
    # -------------------------------------------------------------------- #

    def log(self, x):
        expr = 'math.log(V[{0}])'
        return self._array(expr.format(x._key), x.shape)

    def exp(self, x):
        expr = 'math.exp(V[{0}])'
        return self._array(expr.format(x._key), x.shape)

    def sin(self, x):
        expr = 'math.sin(V[{0}])'
        return self._array(expr.format(x._key), x.shape)

    def cos(self, x):
        expr = 'math.cos(V[{0}])'
        return self._array(expr.format(x._key), x.shape)

    def copy(self, x):
        expr = 'math.copy(V[{0}])'
        return self._array(expr.format(x._key), x.shape)

    def transpose(self, x, axes=None):
        assert x.grid is self
        if axes is None:
            axes = tuple(reversed(range(x.ndim)))
        dataAxes = (0, 1) + tuple(i+2 for i in axes)
        expr = 'V[{0}].transpose({1})'.format(x._key, dataAxes)
        shape = tuple(x.shape[i] for i in axes)
        return self._array(expr, shape)

    def roll(self, x, shift, axis=None):
        if axis is None:
            expr = '''math.roll( \\
                     V[{0}].reshape((ixEnd - ixStart, iyEnd - iyStart, -1)),
                     {1}).reshape(V[{0}].shape)'''.format(x._key, shift)
        else:
            expr = 'math.roll(V[{0}], {1}, {2})'.format(x._key, shift, axis+2)
        return self._array(expr, x.shape)


    # -------------------------------------------------------------------- #
    #                            global operations                         #
    # -------------------------------------------------------------------- #

    def reduce_sum(self, a):
        assert a.grid == self
        expr = 'V[{0}].sum(axis=(0,1))'.format(a._key)
        return sum(self._commandPipe.eval_sync(expr))

    def reduce_mean(self, a):
        assert a.grid == self
        expr = 'V[{0}].mean(axis=(0,1))'.format(a._key)
        return sum(self._commandPipe.eval_sync(expr)) / len(self._workers)

#==============================================================================#
#                               psarray base class                             #
#==============================================================================#

class psarray_base(object):
    def __init__(self, grid, expression, data, shape):
        self.grid = grid
        assert grid.nx > 0
        assert grid.ny > 0
        self._key = grid._new_var_key_(self)
        grid._commandPipe.assign_async(self._key, expression, data)
        self._shape = shape

    def __del__(self):
        self.grid._del_var_key_(self._key)

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
        dataInd = self._data_index_(ind)
        shape = np.empty(self.shape)[ind].shape
        expr = 'V[{0}][{1}]'.format(self._key, dataInd)
        return self.grid._array(expr, shape)


    # -------------------------------------------------------------------- #
    #                         access spatial neighbors                     #
    # -------------------------------------------------------------------- #

    @property
    def x_p(self):
        return self.grid._array('x_p({0})'.format(self._key), self.shape)

    @property
    def x_m(self):
        return self.grid._array('x_m({0})'.format(self._key), self.shape)

    @property
    def y_p(self):
        return self.grid._array('y_p({0})'.format(self._key), self.shape)

    @property
    def y_m(self):
        return self.grid._array('y_m({0})'.format(self._key), self.shape)

    # -------------------------------------------------------------------- #
    #                         algorithmic operations                       #
    # -------------------------------------------------------------------- #

    def __neg__(self):
        return self.grid._array('-V[{0}]'.format(self._key), self.shape)

    def __radd__(self, a):
        return self.__add__(a)

    def __add__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            expr = 'data_ndim(V[{0}], {2}) + data_ndim(V[{1}], {2})' \
                  .format(self._key, a._key, ndim)
            shape = (np.zeros(self.shape) + np.zeros(a.shape)).shape
            return self.grid._array(expr, shape)
        else:
            if hasattr(a, 'ndim'):
                ndim = max(a.ndim, self.ndim)
                var = 'data_ndim(V[{0}], {1})'.format(self._key, ndim)
            else:
                var = 'V[{0}]'.format(self._key)
            expr = '{0} + data'.format(var)
            shape = (np.zeros(self.shape) + a).shape
            return self.grid._array(expr, shape, data=a)

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

            expr = 'data_ndim(V[{0}], {2}) * data_ndim(V[{1}], {2})' \
                  .format(self._key, a._key, ndim)
            shape = (np.zeros(self.shape) * np.zeros(a.shape)).shape
            return self.grid._array(expr, shape)
        else:
            if hasattr(a, 'ndim'):
                ndim = max(a.ndim, self.ndim)
                var = 'data_ndim(V[{0}], {1})'.format(self._key, ndim)
            else:
                var = 'V[{0}]'.format(self._key)
            expr = '{0} * data'.format(var)
            shape = (np.zeros(self.shape) * a).shape
            return self.grid._array(expr, shape, data=a)

    def __div__(self, a):
        return self.__truediv__(a)

    def __truediv__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            expr = 'data_ndim(V[{0}], {2}) / data_ndim(V[{1}], {2})' \
                  .format(self._key, a._key, ndim)
            shape = (np.zeros(self.shape) / np.zeros(a.shape)).shape
            return self.grid._array(expr, shape)
        else:
            if hasattr(a, 'ndim'):
                ndim = max(a.ndim, self.ndim)
                var = 'data_ndim(V[{0}], {1})'.format(self._key, ndim)
            else:
                var = 'V[{0}]'.format(self._key)
            expr = '{0} / data'.format(var)
            shape = (np.zeros(self.shape) / a).shape
            return self.grid._array(expr, shape, data=a)

    def __rdiv__(self, a):
        return self.__rtruediv__(a)

    def __rtruediv__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            expr = 'data_ndim(V[{1}], {2}) / data_ndim(V[{0}], {2})' \
                  .format(self._key, a._key, ndim)
            shape = (np.zeros(a.shape) / np.ones(self.shape)).shape
            return self.grid._array(expr, shape)
        else:
            if hasattr(a, 'ndim'):
                ndim = max(a.ndim, self.ndim)
                var = 'data_ndim(V[{0}], {1})'.format(self._key, ndim)
            else:
                var = 'V[{0}]'.format(self._key)
            expr = 'data / {0}'.format(var)
            shape = (a / np.ones(self.shape)).shape
            return self.grid._array(expr, shape, data=a)

    def __pow__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            expr = 'data_ndim(V[{0}], {2}) ** data_ndim(V[{1}], {2})' \
                  .format(self._key, a._key, ndim)
            shape = (np.zeros(self.shape) ** np.zeros(a.shape)).shape
            return self.grid._array(expr, shape)
        else:
            if hasattr(a, 'ndim'):
                ndim = max(a.ndim, self.ndim)
                var = 'data_ndim(V[{0}], {1})'.format(self._key, ndim)
            else:
                var = 'V[{0}]'.format(self._key)
            expr = '{0} ** data'.format(var)
            shape = (np.zeros(self.shape) ** a).shape
            return self.grid._array(expr, shape, data=a)

    def sum(self, axis=None):
        if axis is None:
            expr = '''V[{0}].reshape((ixEnd - ixStart, iyEnd - iyStart, -1)) \
                     .sum(2)'''.format(self._key)
            return self.grid._array(expr, ())
        else:
            expr = 'V[{0}].sum({1})'.format(self._key, axis + 2)
            shape = np.ones(self.shape).sum(axis).shape
            return self.grid._array(expr, shape)

    def transpose(self, axis=None):
        return self.grid.transpose(self, axis)

    @property
    def T(self):
        return self.grid.transpose(self)


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
        if isinstance(a, psarray_numpy):
            assert a.grid is self.grid
            expr, data = 'V[{0}]'.format(ind, a._key), None
            data = None
        else:
            expr, data = 'data', a
        self.grid._commandPipe.assign_with_index_async( \
                self._key, self._data_index(ind), expr, data)


    # -------------------------------------------------------------------- #
    #                           input / output                             #
    # -------------------------------------------------------------------- #

    def _gather_data(self):
        expr = 'V[{0}]'.format(self._key)
        dataSubarrays = self.grid._commandPipe.eval_sync(expr)

        data = np.empty((self.grid.nx, self.grid.ny) + self.shape)
        for iRange, dataSubarray in zip(self.grid._iRanges, dataSubarrays):
            (ixStart, ixEnd), (iyStart, iyEnd) = iRange
            data[ixStart:ixEnd, iyStart:iyEnd,:] = dataSubarray
        return data

    def save(self, filename):
        np.save(filename, self._gather_data())


#==============================================================================#
#                                  unit tests                                  #
#==============================================================================#

class _Grid2dHelperFunctionsTest(unittest.TestCase):
    def test_assign_i_ranges(self):
        res = assign_i_ranges(4,4,2,2)
        self.assertEqual(res[0], ((0,2),(0,2)))
        self.assertEqual(res[1], ((0,2),(2,4)))
        self.assertEqual(res[2], ((2,4),(0,2)))
        self.assertEqual(res[3], ((2,4),(2,4)))

    def test_make_comm_arrays_2_2(self):
        arr = make_comm_arrays(2,2)
        (p00_xm, p00_xp), (p00_ym, p00_yp) = arr[0][1]
        (p01_xm, p01_xp), (p01_ym, p01_yp) = arr[1][1]
        (p10_xm, p10_xp), (p10_ym, p10_yp) = arr[2][1]
        (p11_xm, p11_xp), (p11_ym, p11_yp) = arr[3][1]

        p00_xm.send(0)
        self.assertEqual(p10_xp.recv(), 0)
        p10_xm.send(1)
        self.assertEqual(p00_xp.recv(), 1)

        p00_yp.send(2)
        self.assertEqual(p01_ym.recv(), 2)
        p11_yp.send(3)
        self.assertEqual(p10_ym.recv(), 3)

    def test_make_comm_arrays_3_1(self):
        arr = make_comm_arrays(3,1)
        (p0_xm, p0_xp), (p0_ym, p0_yp) = arr[0][1]
        (p1_xm, p1_xp), (p1_ym, p1_yp) = arr[1][1]
        (p2_xm, p2_xp), (p2_ym, p2_yp) = arr[2][1]
        
        p0_xm.send(0)
        self.assertEqual(p2_xp.recv(), 0)
        p1_xp.send(1)
        self.assertEqual(p2_xm.recv(), 1)
        
        p0_ym.send(100)
        self.assertEqual(p0_yp.recv(), 100)
        p1_yp.send(101)
        self.assertEqual(p1_ym.recv(), 101)


class _OpTest(unittest.TestCase):
    def __init__(self, *args, **kargs):
        unittest.TestCase.__init__(self, *args, **kargs)
        self.G = grid2d(8,8)

    def _testOp(self, func, x_shp):
        x = self.G.ones(x_shp)
        y0 = func(x)
        y1 = psc_compile(func)(x)
        self.assertAlmostEqual(0, np.abs((y0 - y1)._data).sum())


# class _MathOps(_OpTest):
#     def testAdd(self):
#         self._testOp(lambda x : 1 + x, 3)
#         self._testOp(lambda x : x + 1, 3)
# 
#         self._testOp(lambda x : x + np.ones(3), 3)
#         self._testOp(lambda x : np.ones(3) + x, 3)
#         self._testOp(lambda x : np.ones([4,2,3]) + x + np.ones([3]), [2,3])
# 
#         G = self.G
#         self._testOp(lambda x : x + G.ones(3), 3)
#         self._testOp(lambda x : G.ones(3) + x, 3)
#         self._testOp(lambda x : G.ones([4,2,3]) + x + G.ones([3]), [2,3])


#==============================================================================#
#                                 smoke tests                                  #
#==============================================================================#

def smoke_test():
    'Does the code crash?'
    G = grid2d(8, 10, 3, 1)
    a = G.ones(1) + G.zeros(2)
    b = a.x_p + a.x_m + a.y_p + a.y_m - 4 * a
    b._gather_data()
    print('Smoke test completed')

#==============================================================================#
#                                 speed tests                                  #
#==============================================================================#

def speed_test():
    nGridX, nRepeat = 920, 100
    a = np.ones([nGridX, 40])
    t0 = time.time()
    for i in range(nRepeat):
        a += np.sin(a)
    a.sum()
    print(time.time() - t0)

    G = grid2d(nGridX, 40, 4, 1)
    a = G.ones(1)
    t0 = time.time()
    for i in range(nRepeat):
        a += G.sin(a)
    G.reduce_sum(a)
    print(time.time() - t0)



# ---------------------------------------------------------------------------- #

if __name__ == '__main__':
    # _VERBOSE_ = True
    smoke_test()
    speed_test()
    unittest.main()


################################################################################
################################################################################
################################################################################
