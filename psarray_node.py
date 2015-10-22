################################################################################
#                                                                              #
#            psarray.py copyright 2015 Qiqi Wang (qiqi.wang@gmail.com)         #
#                                                                              #
################################################################################

import numbers
import weakref
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
    ''
    # --------------------------------------------------------------------- #
    #                          "global" variables                           #
    # --------------------------------------------------------------------- #

    (ixStart, ixEnd), (iyStart, iyEnd) = iRange
    comm_x_p, comm_x_m, comm_y_p, comm_y_m = commArray

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
            v = V['key']
            comm_x_p.send(v[-1,:]); comm_x_m.send(v[0,:])
            comm_y_p.send(v[:,-1]); comm_y_m.send(v[:,0])

            shape_with_ghost = (v.shape[0] + 2, v.shape[1] + 2) + v.shape[2:]
            _V_with_ghost[key] = np.empty(shape_with_ghost)
            _V_with_ghost[key][1:-1,1:-1] = v

            _V_with_ghost[key][0,1:-1] = comm_x_m.recv()
            _V_with_ghost[key][-1,1:-1] = comm_x_p.recv()
            _V_with_ghost[key][1:-1,0] = comm_p_m.recv()
            _V_with_ghost[key][1:-1,-1] = comm_p_p.recv()

    def invalidate_ghost(key):
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
        commandType, cmd, data = commandPipe.recv()
        if commandType < 0:
            break
        elif commandType == 0:
            exec(cmd, {})
        elif commandType == 1:
            commandPipe.send(eval(cmd, {}))
        else:
            raise NotImplementedError


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

    def exec_async(self, cmd, data=None):
        for p in self.directors:
            p.send((0, cmd, data))

    def eval_sync(self, cmd, data=None):
        for p in self.directors:
            p.send((1, cmd, data))
        return tuple(p.recv() for p in self.directors) 


def assign_i_ranges(nx, ny, nxWorkers, nyWorkers):
    'return a tuple of (ixStart,ixEnd,iyStart,iyEnd) quads'
    def assign_1d_ranges(n, nRanges):
        'return a generator of (iStart,iEnd) pairs'
        i_boundary = lambda i : i * n / nRanges
        return ((i_boundary(i), i_boundary(i+1)) for i in range(nRanges))
    ixRanges = assign_1d_ranges(nx, nxWorkers)
    iyRanges = assign_1d_ranges(ny, nyWorkers)
    return tuple(itertools.product(ixRanges, iyRanges))


def make_comm_arrays(iRanges):
    last functionto implement


#==============================================================================#
#                                 grid2d class                                 #
#==============================================================================#

class grid2d(object):
    def __init__(self, nx, ny, nxWorkers, nyWorkers, maxCommBytesPerGrid=256):
        assert nx > 0
        assert ny > 0

        self._nx = int(nx)
        self._ny = int(ny)
        
        self._nxWorkers = int(nxWorkers)
        self._nyWorkers = int(nyWorkers)

        self._commandPipe = CommandPipe(nxWorkers * nyWorkers)
        self._iRanges = assign_i_ranges(nx, ny, nxWorkers, nyWorkers)
        self._commArrays = make_comm_arrays(self._iRanges)

        def make_worker(commandPipe, self._iRange, self._commArray):
            return multiprocessing.Process(target=grid2d_worker_main,
                    args=(commandPipe, iRange, commArray))

        self._workers = tuple(map(make_worker, commandPipe.listeners,
                np.ravel(self._iRanges), np.ravel(self._commArrays)))
        assert len(self._workers) == nxWorkers * nyWorkers

        self._math = np

        self._var_key_number = 0
        self._var_weak_refs = {}


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
        self._var_weak_refs[key] = weakref.ref(a, self._del_var_key_)
        return key

    def _del_var_key_(self, a):
        del self._var_weak_refs[a._key]
        self._commandPipe.exec_async('del_V("{0}")'.format(a._key)

    # -------------------------------------------------------------------- #
    #                           array constructors                         #
    # -------------------------------------------------------------------- #

    def _array(self, workerCommand, workerData, shape):
        if self._math is np:
            return psarray_numpy(self, workerCommand, workerData, shape)
        elif self._math is T:
            return psarray_theano(self, workerCommand, workerData, shape)

    def zeros(self, shape):
        cmd = 'math.zeros(prepend_shape({0}))'
        return self._array(cmd.format(str(shape)), shape)

    def ones(self, shape):
        cmd = 'math.ones(prepend_shape({0}))'
        return self._array(cmd.format(str(shape)), shape)

    def random(self, shape=()):
        cmd = 'math.random.random(preppend_shape({0}))'
        return self._array(cmd.format(str(shape)), shape)

    # def load(self, filename):
    #     assert self._math is np
    #     data = np.load(filename)
    #     return self._array(data, data.shape[2:])

    @property
    def i(self):
        cmd = '''math.outer(math.arange(ixStart, ixEnd),
                            math.ones(iyEnd - iyStart))'''
        return self._array(cmd, ())

    @property
    def j(self):
        cmd = '''math.outer(math.ones(ixEnd - ixStart),
                            math.arange(iyStart, iyEnd))'''
        return self._array(cmd, ())

    # -------------------------------------------------------------------- #
    #                        array transformations                         #
    # -------------------------------------------------------------------- #

    def log(self, x):
        cmd = 'math.log(V["{0}"])'
        return self._array(cmd.format(x._key), x.shape)

    def exp(self, x):
        cmd = 'math.exp(V["{0}"])'
        return self._array(cmd.format(x._key), x.shape)

    def sin(self, x):
        cmd = 'math.sin(V["{0}"])'
        return self._array(cmd.format(x._key), x.shape)

    def cos(self, x):
        cmd = 'math.cos(V["{0}"])'
        return self._array(cmd.format(x._key), x.shape)

    def copy(self, x):
        cmd = 'math.copy(V["{0}"])'
        return self._array(cmd.format(x._key), x.shape)

    def transpose(self, x, axes=None):
        assert x.grid is self
        if axes is None:
            axes = tuple(reversed(range(x.ndim)))
        dataAxes = (0, 1) + tuple(i+2 for i in axes)
        cmd = 'V["{0}"].transpose({1})'.format(x._key, dataAxes)
        shape = tuple(x.shape[i] for i in axes)
        return self._array(cmd, shape)

    def roll(self, x, shift, axis=None):
        if axis is None:
            cmd = '''math.roll( \\
                     V["{0}"].reshape((ixEnd - ixStart, iyEnd - iyStart, -1)),
                     {1}).reshape(V["{0}"].shape)'''.format(x._key, shift)
        else:
            cmd = 'math.roll(V["{0}"], {1}, {2})'.format(x._key, shift, axis+2)
        return self._array(cmd, x.shape)


    # -------------------------------------------------------------------- #
    #                            global operations                         #
    # -------------------------------------------------------------------- #

    def reduce_sum(self, a):
        assert a.grid == self
        cmd = 'V["{0}"].sum(axis=(0,1))'.format(x._key)
        return sum(self._commandPipe.eval_sync(cmd))

    def reduce_mean(self, a):
        assert a.grid == self
        cmd = 'V["{0}"].mean(axis=(0,1))'.format(x._key)
        return sum(self._commandPipe.eval_sync(cmd)) / len(self._workers)

#==============================================================================#
#                               psarray base class                             #
#==============================================================================#

class psarray_base(object):
    def __init__(self, grid, cmd, data, shape):
        self.grid = grid
        assert grid.nx > 0
        assert grid.ny > 0
        self._key = grid._new_var_key_(self)
        exec_cmd = 'V["{0}"] = {1}'.format(self._key, cmd)
        grid._commandPipe.exec_async(exec_cmd, data)
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
        dataInd = self._data_index_(ind)
        shape = np.empty(self.shape)[ind].shape
        cmd = 'V["{0}"][{1}]'.format(self._key, dataInd)
        return self.grid._array(cmd, shape)


    # -------------------------------------------------------------------- #
    #                         access spatial neighbors                     #
    # -------------------------------------------------------------------- #

    @property
    def x_p(self):
        return self.grid._array('x_p("{0}")'.format(self._key), self.shape)

    @property
    def x_m(self):
        return self.grid._array('x_m("{0}")'.format(self._key), self.shape)

    @property
    def y_p(self):
        return self.grid._array('y_p("{0}")'.format(self._key), self.shape)

    @property
    def y_m(self):
        return self.grid._array('y_m("{0}")'.format(self._key), self.shape)

    # -------------------------------------------------------------------- #
    #                         algorithmic operations                       #
    # -------------------------------------------------------------------- #

    def __neg__(self):
        return self.grid._array('-V["{0}"]'.format(self._key), self.shape)

    def __radd__(self, a):
        return self.__add__(a)

    def __add__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            cmd = 'data_ndim(V["{0}"], {2}) + data_ndim(V["{1}"], {2})' \
                  .format(self._key, a._key, ndim)
            shape = (np.zeros(self.shape) + np.zeros(a.shape)).shape
            return self.grid._array(cmd, shape)
        else:
            if hasattr(a, 'ndim'):
                ndim = max(a.ndim, self.ndim)
                var = 'data_ndim(V["{0}"], {1})'.format(self._key, ndim)
            else:
                var = 'V["{0}"]'.format(self._key)
            cmd = '{0} + data'.format(var)
            shape = (np.zeros(self.shape) + a).shape
            return self.grid._array(cmd, a, shape)

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

            cmd = 'data_ndim(V["{0}"], {2}) * data_ndim(V["{1}"], {2})' \
                  .format(self._key, a._key, ndim)
            shape = (np.zeros(self.shape) * np.zeros(a.shape)).shape
            return self.grid._array(cmd, shape)
        else:
            if hasattr(a, 'ndim'):
                ndim = max(a.ndim, self.ndim)
                var = 'data_ndim(V["{0}"], {1})'.format(self._key, ndim)
            else:
                var = 'V["{0}"]'.format(self._key)
            cmd = '{0} * data'.format(var)
            shape = (np.zeros(self.shape) * a).shape
            return self.grid._array(cmd, a, shape)

    def __div__(self, a):
        return self.__truediv__(a)

    def __truediv__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            cmd = 'data_ndim(V["{0}"], {2}) / data_ndim(V["{1}"], {2})' \
                  .format(self._key, a._key, ndim)
            shape = (np.zeros(self.shape) / np.zeros(a.shape)).shape
            return self.grid._array(cmd, shape)
        else:
            if hasattr(a, 'ndim'):
                ndim = max(a.ndim, self.ndim)
                var = 'data_ndim(V["{0}"], {1})'.format(self._key, ndim)
            else:
                var = 'V["{0}"]'.format(self._key)
            cmd = '{0} / data'.format(var)
            shape = (np.zeros(self.shape) / a).shape
            return self.grid._array(cmd, a, shape)

    def __rdiv__(self, a):
        return self.__rtruediv__(a)

    def __rtruediv__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            cmd = 'data_ndim(V["{1}"], {2}) / data_ndim(V["{0}"], {2})' \
                  .format(self._key, a._key, ndim)
            shape = (np.zeros(a.shape) / np.ones(self.shape)).shape
            return self.grid._array(cmd, shape)
        else:
            if hasattr(a, 'ndim'):
                ndim = max(a.ndim, self.ndim)
                var = 'data_ndim(V["{0}"], {1})'.format(self._key, ndim)
            else:
                var = 'V["{0}"]'.format(self._key)
            cmd = 'data / {0}'.format(var)
            shape = (a / np.ones(self.shape)).shape
            return self.grid._array(cmd, a, shape)

    def __pow__(self, a):
        if isinstance(a, psarray_base):
            assert a.grid is self.grid
            ndim = max(a.ndim, self.ndim)

            cmd = 'data_ndim(V["{0}"], {2}) ** data_ndim(V["{1}"], {2})' \
                  .format(self._key, a._key, ndim)
            shape = (np.zeros(self.shape) ** np.zeros(a.shape)).shape
            return self.grid._array(cmd, shape)
        else:
            if hasattr(a, 'ndim'):
                ndim = max(a.ndim, self.ndim)
                var = 'data_ndim(V["{0}"], {1})'.format(self._key, ndim)
            else:
                var = 'V["{0}"]'.format(self._key)
            cmd = '{0} ** data'.format(var)
            shape = (np.zeros(self.shape) ** a).shape
            return self.grid._array(cmd, a, shape)

    def sum(self, axis=None):
        if axis is None:
            cmd = '''V["{0}"].reshape((ixEnd - ixStart, iyEnd - iyStart, -1)) \
                     .sum(2)'''.format(self._key)
            return self.grid._array(cmd, ())
        else:
            cmd = 'V["{0}"].sum({1})'.format(self._key, axis + 2)
            shape = np.ones(self.shape).sum(axis).shape
            return self.grid._array(cmd, shape)

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
        cmd = 'invalidate_ghost("{0}")'.format(a._key)
        self.grid._commandPipe.exec_async(cmd)

        if isinstance(a, psarray_numpy):
            assert a.grid is self.grid
            a_cmd = 'V["{0}"]'.format(ind, a._key)
            data = None
        else:
            a_cmd = 'data'
            data = a
        ind = self._data_index_(ind)
        cmd = 'V["{0}"][{1}] = {2}'.format(a._key, ind, a_cmd)
        self.grid._commandPipe.exec_async(cmd, data)


    # -------------------------------------------------------------------- #
    #                           input / output                             #
    # -------------------------------------------------------------------- #

    def _gather_data(self):
        cmd = 'V["{0}"]'.format(self._key)
        dataSubarrays = self.grid._commandPipe.eval_sync(cmd)

        data = np.empty((self.nx, self.ny) + self.shape)
        for iRange, dataSubarray in zip(self._iRange, dataSubarrays):
            ixStart, ixEnd, iyStart, iyEnd = iRange
            data[ixStart:ixEnd, iyStart:iyEnd,:] = dataSubarray
        return data

    def save(self, filename):
        np.save(filename, self._gather_data())


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


# ---------------------------------------------------------------------------- #

if __name__ == '__main__':
    # _VERBOSE_ = True
    unittest.main()


################################################################################
################################################################################
################################################################################
