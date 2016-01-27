# ============================================================================ #
#                                                                              #
#       sa2d_theano.py copyright(c) Qiqi Wang 2015 (qiqi.wang@gmail.com)       #
#                                                                              #
# ============================================================================ #

from __future__ import division

import sys
import unittest
import operator
import numpy as np
import theano
import theano.tensor as T

def _is_like_sa(a):
    '''
    Check attributes of sa object
    '''
    return hasattr(a, 'tensor') and hasattr(a, 'has_ghost')

def _promote_ndim(t, ndim):
    if t.ndim == ndim:
        return t
    else:
        assert t.ndim < ndim
        pad_dim = T.ones(ndim - t.ndim, int)
        new_shape = T.join(0, t.shape[:2], pad_dim, t.shape[2:])
        pt = T.reshape(t, new_shape, ndim=ndim)

        broadcastable = t.broadcastable[:2] + (True,) * (ndim - t.ndim) \
                      + t.broadcastable[2:]
        pt = T.patternbroadcast(pt, broadcastable)
        return pt

def _is_broadcastable(t):
    return t.broadcastable[0] and t.broadcastable[1]

def _binary_op(op, a, b):
    '''
    Perform operations between arrays with or without ghost cells.
    When both arrays have ghost cells, the resulting array also has ghost cell.
    When either array has no ghost cell, the resulting array has no ghost cell.
    This behavior is the primary functionality this module tries to achieve.
    '''
    if _is_like_sa(a) and _is_like_sa(b):
        ndim = max(a.ndim, b.ndim) + 2
        at = _promote_ndim(a.tensor, ndim)
        bt = _promote_ndim(b.tensor, ndim)
        if a.has_ghost and not b.has_ghost:
            if not _is_broadcastable(at):
                at = at[1:-1,1:-1]
        elif not a.has_ghost and b.has_ghost:
            if not _is_broadcastable(bt):
                bt = bt[1:-1,1:-1]
        shape = op(np.ones(a.shape), np.ones(b.shape)).shape
        return stencil_array(shape, op(at, bt), a.has_ghost and b.has_ghost)
    elif _is_like_sa(a):
        shape = op(np.ones(a.shape), b).shape
        if len(shape) > a.ndim:
            at = _promote_ndim(a.tensor, len(shape) + 2)
        else:
            at = a.tensor
        return stencil_array(shape, op(at, b), a.has_ghost)
    elif _is_like_sa(b):
        shape = op(a, np.ones(b.shape)).shape
        if len(shape) > b.ndim:
            bt = _promote_ndim(b.tensor, len(shape) + 2)
        else:
            bt = b.tensor
        return stencil_array(shape, op(a, bt), b.has_ghost)


# ============================================================================ #
#                                                                              #
# ============================================================================ #

class stencil_array(object):
    '''
    Objects involved in computation.  It should be used like theano arrays,
    except functions like sin and exp should use the ones defined in this module
    '''
    __context__ = sys.modules[__name__]

    def __init__(self, shape, tensor, has_ghost):
        assert tensor.ndim == len(shape) + 2
        for i in shape:
            assert isinstance(i, int)
        self.shape = tuple(shape)
        self.tensor = tensor
        self.has_ghost = has_ghost

    # --------------------------- properties ------------------------------ #

    @property
    def ndim(self):
        return len(self.shape)

    @property
    def size(self):
        return np.prod(self.shape)

    def __len__(self):
        return self.shape[0]

    # --------------------------- operations ------------------------------ #

    # asks ndarray to use the __rops__ defined in this class
    __array_priority__ = 3000

    def __add__(self, a):
        return _binary_op(operator.add, self, a)

    def __radd__(self, a):
        return _binary_op(operator.add, a, self)

    def __sub__(self, a):
        return _binary_op(operator.sub, self, a)

    def __rsub__(self, a):
        return _binary_op(operator.sub, a, self)

    def __mul__(self, a):
        return _binary_op(operator.mul, self, a)

    def __rmul__(self, a):
        return _binary_op(operator.mul, a, self)

    def __truediv__(self, a):
        return _binary_op(operator.truediv, self, a)

    def __rtruediv__(self, a):
        return _binary_op(operator.truediv, a, self)

    def __pow__(self, a):
        return _binary_op(operator.pow, self, a)

    def __rpow__(self, a):
        return _binary_op(operator.pow, a, self)

    def __neg__(self):
        return stencil_array(self.shape, -self.tensor, self.has_ghost)

    # ------------------------- math functions ---------------------------- #

    def sum(self, axis=None):
        return sum(self, axis)

    def mean(self, axis=None):
        return mean(self, axis)

    # ------------------------- transformations --------------------------- #

    @property
    def T(self):
        return transpose(self)

    def transpose(self, axes=None):
        return transpose(self, axes)

    def reshape(self, shape):
        return reshape(self, shape)

    def copy(self):
        return copy(self)

    # ------------------------ neighbor access -------------------------- #

    @property
    def x_p(self):
        assert self.has_ghost, 'Has No Ghost'
        if _is_broadcastable(self.tensor):
            return self
        else:
            return stencil_array(self.shape, self.tensor[2:,1:-1], False)

    @property
    def x_m(self):
        assert self.has_ghost, 'Has No Ghost'
        if _is_broadcastable(self.tensor):
            return self
        else:
            return stencil_array(self.shape, self.tensor[:-2,1:-1], False)

    @property
    def y_p(self):
        assert self.has_ghost, 'Has No Ghost'
        if _is_broadcastable(self.tensor):
            return self
        else:
            return stencil_array(self.shape, self.tensor[1:-1,2:], False)

    @property
    def y_m(self):
        assert self.has_ghost, 'Has No Ghost'
        if _is_broadcastable(self.tensor):
            return self
        else:
            return stencil_array(self.shape, self.tensor[1:-1,:-2], False)

    # ---------------------------- indexing ------------------------------- #

    @staticmethod
    def _data_index_(ind):
        if not isinstance(ind, tuple):
            ind = (ind,)
        ind = (slice(None),) * 2 + ind
        return ind

    def __getitem__(self, ind):
        shape = np.empty(self.shape)[ind].shape
        tensor_ind = self._data_index_(ind)
        return stencil_array(shape, self.tensor[tensor_ind], self.has_ghost)

    def __setitem__(self, ind, a):
        sub_tensor = self.tensor[self._data_index_(ind)]
        if not _is_like_sa(a):
            self.tensor = T.set_subtensor(sub_tensor, a)
        else:
            a_tensor = _promote_ndim(a.tensor, sub_tensor.ndim)
            if _is_broadcastable(self.tensor):
                z = T.zeros_like(a_tensor)
                while z.ndim > 2:
                    z = z[:,:,0]
                self.tensor = self.tensor + _promote_ndim(z, self.tensor.ndim)
                sub_tensor = self.tensor[self._data_index_(ind)]

            if a.has_ghost == self.has_ghost or _is_broadcastable(a_tensor):
                self.tensor = T.set_subtensor(sub_tensor, a_tensor)
            elif a.has_ghost:   # self has no ghost
                self.tensor = T.set_subtensor(sub_tensor, a_tensor[1:-1,1:-1])
            else:               # self has ghost but a does not
                sub_tensor = self.tensor[1:-1,1:-1][self._data_index_(ind)]
                self.tensor = T.set_subtensor(sub_tensor, a_tensor)
                self.has_ghost = False

# ============================================================================ #
#                             data transformations                             #
# ============================================================================ #

def transpose(x, axes=None):
    if axes is None:
        axes = tuple(reversed(range(x.ndim)))
    transposed_shape = tuple(x.shape[i] for i in axes)
    transposed_tensor = x.tensor.transpose((0, 1) + tuple(i+2 for i in axes))
    return stencil_array(transposed_shape, transposed_tensor, x.has_ghost)

def reshape(x, shape):
    shape = np.empty(x.shape).reshape(shape).shape
    ndim = len(shape) + 2
    tensor_shape = T.join(0, x.tensor.shape[:2], shape)
    reshaped_tensor = x.tensor.reshape(tensor_shape, ndim=ndim)
    return stencil_array(shape, reshaped_tensor, x.has_ghost)

def roll(x, shift, axis=None):
    if axis is None:
        tensor_shape = T.join(0, x.tensor.shape[:2], [-1])
        new_tensor = x.tensor.reshape(tensor_shape, ndim=3)
        new_tensor = T.roll(new_tensor, shift, 2)
        new_tensor = new_tensor.reshape(x.tensor.shape, ndim=x.tensor.ndim)
    else:
        new_tensor = T.roll(x.tensor, shift, axis+2)
    return stencil_array(x.shape, new_tensor, x.has_ghost)

def copy(a):
    assert _is_like_sa(a)
    return stencil_array(a.shape, a.tensor, a.has_ghost)


# ============================================================================ #
#                            mathematical functions                            #
# ============================================================================ #

def sin(a):
    assert _is_like_sa(a)
    return stencil_array(a.shape, T.sin(a.tensor), a.has_ghost)

def cos(a):
    assert _is_like_sa(a)
    return stencil_array(a.shape, T.cos(a.tensor), a.has_ghost)

def exp(a):
    assert _is_like_sa(a)
    return stencil_array(a.shape, T.sin(a.tensor), a.has_ghost)

def sum(a, axis=None):
    assert _is_like_sa(a)
    if axis is None:
        tensor_shape = T.join(0, a.tensor.shape[:2], [a.size])
        tensor = T.sum(T.reshape(a.tensor, tensor_shape, ndim=3), axis=2)
        return stencil_array((), tensor, a.has_ghost)
    else:
        shape = np.zeros(a.shape).sum(axis).shape
        tensor = T.sum(a.tensor, axis+2)
        return stencil_array(shape, tensor, a.has_ghost)

def mean(a, axis=None):
    assert _is_like_sa(a)
    if axis is None:
        tensor_shape = T.join(0, a.tensor.shape[:2], [a.size])
        tensor = T.mean(T.reshape(a.tensor, tensor_shape, ndim=3), axis=2)
        return stencil_array((), tensor, a.has_ghost)
    else:
        shape = np.zeros(a.shape).mean(axis).shape
        tensor = T.mean(a.tensor, axis+2)
        return stencil_array(shape, tensor, a.has_ghost)

# ============================================================================ #
#                               sa arrays generators                         #
# ============================================================================ #

def ones(shape=()):
    shape = np.ones(shape).shape
    return stencil_array(shape, T.ones((1,1) + shape), has_ghost=True)

def zeros(shape=()):
    shape = np.zeros(shape).shape
    return stencil_array(shape, T.zeros((1,1) + shape), has_ghost=True)

# ============================================================================ #
#                          compiling into theano function                      #
# ============================================================================ #

def compile(func, inputs=(), args=(), argv={}):
    np2theano = lambda a: T.Tensor('float64', (False,) * a.ndim)()
    input_list = [inputs] if hasattr(inputs, 'ndim') else list(inputs)
    theano_inputs = [np2theano(a) for a in input_list]
    sa_inputs = [stencil_array(a.shape[2:], t, True) \
            for t, a in zip(theano_inputs, input_list)]

    if hasattr(inputs, 'ndim'):
        sa_outputs = func(sa_inputs[0], *args, **argv)
    elif len(inputs):
        sa_outputs = func(sa_inputs, *args, **argv)
    else:
        sa_outputs = func(*args, **argv)

    if hasattr(sa_outputs, 'tensor'):
        theano_outputs = sa_outputs.tensor
    else:
        theano_outputs = [a.tensor for a in sa_outputs]

    return theano.function(theano_inputs, theano_outputs,
            on_unused_input='ignore')


# ============================================================================ #
#                                 unit tests                                   #
# ============================================================================ #

class _TestOperators(unittest.TestCase):
    def testLaplacian(self):
        def laplacian(a):
            z = zeros()
            zz = (z.x_p + z.x_m + z.y_p + z.y_m - 4 * z) / 4
            return (a.x_p + a.x_m + a.y_p + a.y_m - 4 * a) / 4 + zz
        a = np.ones([4,5])
        f = compile(laplacian, a)
        self.assertEqual(f(a).shape, (2,3))
        self.assertAlmostEqual(abs(f(a)).max(), 0)

    def testNonlinear(self):
        def nlLaplacian(a):
            lapla = -4 * a + a.x_p + a.x_m + a.y_p + a.y_m
            return lapla * exp(a) / sin(a) * cos(a)
        a = np.ones([4,5])
        f = compile(nlLaplacian, a)
        self.assertEqual(f(a).shape, (2,3))
        self.assertAlmostEqual(abs(f(a)).max(), 0)

    def testGradient(self):
        def grad(a):
            return (a.x_p - a.x_m) / 2, (a.y_p - a.y_m) / 2
        a = np.outer(np.ones(4), np.arange(5) * 2) \
          + np.outer(np.arange(4), np.ones(5)) + 1
        f = compile(grad, a)
        ax, ay = f(a)
        self.assertEqual(ax.shape, (2,3))
        self.assertEqual(ay.shape, (2,3))
        self.assertAlmostEqual(abs(ax - 1).max(), 0)
        self.assertAlmostEqual(abs(ay - 2).max(), 0)

    def testDivergence(self):
        def div(v):
            vx, vy = v
            return (vx.x_p - vx.x_m) / 2 + (vy.y_p - vy.y_m) / 2
        v = [np.outer(np.arange(4) * 3, np.ones(5)),
             np.outer(np.ones(4), np.arange(5) * 2)]
        f = compile(div, v)
        vDiv = f(*v)
        self.assertEqual(vDiv.shape, (2,3))
        self.assertAlmostEqual(abs(vDiv - 5).max(), 0)

    def testArbitrary(self):
        def arb(a):
            b = 3 + (a.x_p + a.x_m)
            c = -1 - np.ones(6) * b
            d = ones(6) ** (a / (ones([5,6]) / c))
            e = b ** np.ones(6) ** (a / (np.ones([5,6]) / d))
            f = np.ones([2,1,6]) + a - np.zeros([1,2,5,1])
            return -d
        a = np.ones([3,4,5,6])
        f = compile(arb, a)
        self.assertEqual(f(a).shape, (1,2,5,6))

    def testNoArg(self):
        def func():
            return -ones([2,3,4]) * 123
        f = compile(func)
        self.assertEqual(f().shape, (1,1,2,3,4))
        self.assertAlmostEqual(abs(f() + 123).max(), 0)

# ---------------------------------------------------------------------------- #

class _TestIJ(unittest.TestCase):
    @staticmethod
    def ij_np(i0, i1, j0, j1):
        return np.outer(np.arange(i0, i1), np.ones(j1 - j0, int)), \
               np.outer(np.ones(i1 - i0, int), np.arange(j0, j1))

    def testLaplacianByIpJ(self):
        def laplacian(inputs):
            a, i, j = inputs
            return (a.x_p + a.x_m + a.y_p + a.y_m - 4 * a) / 4 * (i + j)
        a = np.ones([4,5])
        i, j = self.ij_np(0,a.shape[0],0,a.shape[1])
        f = compile(laplacian, (a, i, j))
        fa = f(a, i, j)
        self.assertEqual(fa.shape, (2,3))
        self.assertAlmostEqual(abs(fa).max(), 0)

    def testDivYX(self):
        def divYX(inputs):
            i, j = inputs
            x, y = i * 0.1, j * 0.2
            return y.x_p - y.x_m + x.y_p - x.y_m
        i, j = self.ij_np(-1,3,-1,5)
        f = compile(divYX, (i, j))
        fa = f(i, j)
        self.assertEqual(fa.shape, (2,4))
        self.assertAlmostEqual(abs(fa).max(), 0)

# ---------------------------------------------------------------------------- #

class _TestTransforms(unittest.TestCase):
    def testSize(self):
        def size_a(a):
            return ones(()) * a.size
        a = np.ones([4,5,2,3])
        f = compile(size_a, a)
        fa = f(a)
        self.assertEqual(fa.shape, (1,1))
        self.assertAlmostEqual(abs(fa - 6).max(), 0)

    def testLen(self):
        def len_a(a):
            return zeros(()) + len(a)
        a = np.ones([4,5,2,3])
        f = compile(len_a, a)
        fa = f(a)
        self.assertEqual(fa.shape, (1,1))
        self.assertAlmostEqual(abs(fa - 2).max(), 0)

    def testTranspose1(self):
        def xtm1(a):
            return a.T - 1
        a = np.ones([4,5,2,3])
        f = compile(xtm1, a)
        fa = f(a)
        self.assertEqual(fa.shape, (4,5,3,2))
        self.assertAlmostEqual(abs(fa).max(), 0)

        a = np.zeros([2,3,2,1]) + np.arange(3)
        self.assertEqual(a.shape, (2,3,2,3))
        fa = f(a)
        self.assertEqual(fa.shape, (2,3,3,2))
        self.assertAlmostEqual(abs(fa[:,:,0,:] + 1).max(), 0)
        self.assertAlmostEqual(abs(fa[:,:,1,:]).max(), 0)
        self.assertAlmostEqual(abs(fa[:,:,2,:] - 1).max(), 0)

    def testTranspose2(self):
        def xtm1(a):
            return a.transpose([2,3,1,0]) - 1
        a = np.ones([2,3,4,5,6,7])
        f = compile(xtm1, a)
        fa = f(a)
        self.assertEqual(fa.shape, (2,3,6,7,5,4))
        self.assertAlmostEqual(abs(fa).max(), 0)

        a = np.ones([2,3,4,5,6,1]) + np.arange(7)
        self.assertEqual(a.shape, (2,3,4,5,6,7))
        fa = f(a)
        self.assertEqual(fa.shape, (2,3,6,7,5,4))
        for i in range(7):
            self.assertAlmostEqual(abs(fa[:,:,:,i] - i).max(), 0)

    def testReshape(self):
        def xrm1(a):
            return a.reshape([3,-1]) - 1
        a = np.ones([4,5,2,3,4]) + np.arange(4)
        f = compile(xrm1, a)
        fa = f(a)
        self.assertEqual(fa.shape, (4,5,3,8))
        for i in range(4):
            self.assertAlmostEqual(abs(fa[:,:,:,i] - i).max(), 0)
            self.assertAlmostEqual(abs(fa[:,:,:,i+4] - i).max(), 0)

    def testRoll1(self):
        def xrm1(a):
            return roll(a, 1) - 1
        a = np.ones([4,5,2,3]) + np.arange(2)[:,np.newaxis]
        f = compile(xrm1, a)
        fa = f(a)
        self.assertEqual(fa.shape, a.shape)
        self.assertAlmostEqual(abs(fa[:,:,0,1:]).max(), 0)
        self.assertAlmostEqual(abs(fa[:,:,1,0]).max(), 0)
        self.assertAlmostEqual(abs(fa[:,:,0,0] - 1).max(), 0)
        self.assertAlmostEqual(abs(fa[:,:,1,1:] - 1).max(), 0)

    def testRoll2(self):
        def xr0m1(a):
            return roll(a, 1, axis=0).copy() - 1
        a = np.ones([4,5,2,3]) + np.arange(2)[:,np.newaxis]
        f = compile(xr0m1, a)
        fa = f(a)
        self.assertEqual(fa.shape, a.shape)
        self.assertAlmostEqual(abs(fa[:,:,0,:] - 1).max(), 0)
        self.assertAlmostEqual(abs(fa[:,:,1,:]).max(), 0)

# ---------------------------------------------------------------------------- #

class _TestIndexing(unittest.TestCase):
    def testGetItem1(self):
        def pick12(a):
            return a[1,2]
        a = np.ones([3,4,5,1]) + np.arange(6)
        f = compile(pick12, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4))
        self.assertAlmostEqual(abs(fa - a[:,:,1,2]).max(), 0)

    def testGetItem2(self):
        def pickRange(a):
            return a[1:-1,1:-1]
        a = np.ones([3,4,5,1]) + np.arange(6)
        f = compile(pickRange, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4,3,4))
        self.assertAlmostEqual(abs(fa - a[:,:,1:-1,1:-1]).max(), 0)

    def testGetItem3(self):
        def pickLast(a):
            return a[-1]
        a = np.zeros([3,4,1]) + np.arange(5)
        f = compile(pickLast, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4))
        self.assertAlmostEqual(abs(fa - 4).max(), 0)

    def testSetItem1(self):
        def set12(a):
            a[1,2] = 0
            return a
        a = np.ones([3,4,5,1]) + np.arange(6)
        f = compile(set12, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4,5,6))
        self.assertAlmostEqual(abs(fa[:,:,1,2]).max(), 0)
        diff = fa - a
        diff[:,:,1,2] = 0
        self.assertAlmostEqual(abs(diff).max(), 0)

    def testSetItem2(self):
        def set12(a):
            a[1,2] = 2 * a[1,2].x_p
            return a
        a = np.ones([3,4,5,1]) + np.arange(6)
        f = compile(set12, a)
        fa = f(a)
        self.assertEqual(fa.shape, (1,2,5,6))
        self.assertAlmostEqual(abs(fa[:,:,1,2] - a[0,0,1,2] * 2).max(), 0)
        diff = fa - a[0,0]
        diff[:,:,1,2] = 0
        self.assertAlmostEqual(abs(diff).max(), 0)

    def testSetItem3(self):
        def setRange(a):
            b = a.y_p * 0
            b[1:-1,1:-1] = sin(a[2,3])
            return b
        a = np.ones([3,4,5,1]) + np.arange(6)
        f = compile(setRange, a)
        fa = f(a)
        self.assertEqual(fa.shape, (1,2,5,6))
        self.assertAlmostEqual(abs(fa[:,:,1:-1,1:-1] \
                             - np.sin(a[0,0,2,3])).max(), 0)
        fa[:,:,1:-1,1:-1] = 0
        self.assertAlmostEqual(abs(fa).max(), 0)

    def testSetItem4(self):
        def setToOnes(a):
            a[1,2:4] = ones(2)
            return a
        a = np.ones([3,4,5,1]) + np.arange(6)
        f = compile(setToOnes, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4,5,6))
        self.assertAlmostEqual(abs(fa[:,:,1,2:4] - 1).max(), 0)

    def testSetItem5(self):
        def setToOnes(a):
            b = zeros(4)
            b[1:3] = a[1:3,0] * 2
            a[0,:] = b
            return a
        a = np.ones([3,4,3,4]) + np.arange(4)
        f = compile(setToOnes, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4,3,4))
        self.assertAlmostEqual(abs(fa[:,:,0,[0,3]]).max(), 0)

# ---------------------------------------------------------------------------- #

class _TestSumMean(unittest.TestCase):
    def testSum1(self):
        def sum1(a):
            return a.sum()
        a = np.zeros([3,4,3,4]) + np.arange(4)
        f = compile(sum1, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4))
        self.assertAlmostEqual(abs(fa - 18).max(), 0)

    def testSum2(self):
        def sum1(a):
            return a.sum(1)
        a = np.zeros([3,4,3,4]) + np.arange(4)
        f = compile(sum1, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4,3))
        self.assertAlmostEqual(abs(fa - 6).max(), 0)

    def testMean1(self):
        def mean1(a):
            return a.mean()
        a = np.zeros([3,4,3,4]) + np.arange(4)
        f = compile(mean1, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4))
        self.assertAlmostEqual(abs(fa - 1.5).max(), 0)

    def testMean2(self):
        def mean2(a):
            return a.mean(1)
        a = np.zeros([3,4,3,4]) + np.arange(4)
        f = compile(mean2, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4,3))
        self.assertAlmostEqual(abs(fa - 1.5).max(), 0)

# ============================================================================ #
#                                                                              #
# ============================================================================ #

if __name__ == '__main__':
    unittest.main()

################################################################################
################################################################################
################################################################################
