# ============================================================================ #
#                                                                              #
#                    sa2d_theano.py copyright(c) Qiqi Wang 2015                #
#                                                                              #
# ============================================================================ #

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

def _binary_op(op, a, b):
    '''
    Perform operations between arrays with or without ghost cells.
    When both arrays have ghost cells, the resulting array also has ghost cell.
    When either array has no ghost cell, the resulting array has no ghost cell.
    This behavior is the primary functionality this module tries to achieve.
    '''
    def _promote_ndim(at, bt):
        if at.ndim == bt.ndim:
            return at, bt
        elif at.ndim < bt.ndim:
            at, bt = bt, at
        assert(at.ndim > bt.ndim)
        pad_dim = T.ones(at.ndim - bt.ndim, int)
        new_shape = T.join(0, bt.shape[0:2], pad_dim, bt.shape[2:])
        return at, T.reshape(bt, new_shape, ndim=at.ndim)

    if _is_like_sa(a) and _is_like_sa(b):
        if a.has_ghost == b.has_ghost:  # both have or do not have ghost
            at, bt = _promote_ndim(a.tensor, b.tensor)
        elif a.has_ghost:  # b does not have ghost
            at, bt = _promote_ndim(a.tensor[1:-1,1:-1], b.tensor)
        else:  # a has ghost but b does not have ghost
            at, bt = _promote_ndim(a.tensor, b.tensor[1:-1,1:-1])
        return stencil_array(op(at, bt), a.has_ghost and b.has_ghost)
    elif _is_like_sa(a):
        return stencil_array(op(a.tensor, b), a.has_ghost)
    elif _is_like_sa(b):
        return stencil_array(op(a, b.tensor), b.has_ghost)
    else:
        return op(a, b)


# ============================================================================ #
#                                                                              #
# ============================================================================ #

class stencil_array(object):
    '''
    Objects involved in computation.  It should be used like theano arrays,
    except functions like sin and exp should use the ones defined in this module
    '''
    def __init__(self, tensor, has_ghost):
        self.tensor = tensor
        self.has_ghost = has_ghost

    @property
    def ndim(self):
        return self.tensor.ndim - 2

    # --------------------------- operations ------------------------------ #

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

    def __div__(self, a):
        return self.__truediv__(a)

    def __rdiv__(self, a):
        return self.__rtruediv__(a)

    def __truediv__(self, a):
        return _binary_op(operator.truediv, self, a)

    def __rtruediv__(self, a):
        return _binary_op(operator.truediv, a, self)

    def __pow__(self, a):
        return _binary_op(operator.pow, self, a)

    def __rpow__(self, a):
        return _binary_op(operator.pow, a, self)

    def __neg__(self):
        return stencil_array(-a.tensor, self.has_ghost)

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

    def _assert_has_ghost(self):
        if not self.has_ghost:
            raise ValueError('has no ghost')

    @property
    def x_p(self):
        self._assert_has_ghost()
        return stencil_array(self.tensor[2:,1:-1], False)

    @property
    def x_m(self):
        self._assert_has_ghost()
        return stencil_array(self.tensor[:-2,1:-1], False)

    @property
    def y_p(self):
        self._assert_has_ghost()
        return stencil_array(self.tensor[1:-1,2:], False)

    @property
    def y_m(self):
        self._assert_has_ghost()
        return stencil_array(self.tensor[1:-1,:-2], False)

    # ---------------------------- indexing ------------------------------- #
    #TODO


# ============================================================================ #
#                             data transformations                             #
# ============================================================================ #

def transpose(x, axes=None):
    if axes is None:
        axes = tuple(reversed(range(x.ndim)))
    return stencil_array(x.tensor.transpose((0, 1) + tuple(i+2 for i in axes)),
               x.has_ghost)

def reshape(x, shape):
    shape = list(shape)
    ndim = len(shape) + 2
    tensor_shape = T.join(0, x.tensor.shape[:2], shape)
    return stencil_array(x.tensor.reshape(tensor_shape, ndim=ndim), x.has_ghost)

def roll(x, shift, axis=None):
    if axis is None:
        tensor_shape = T.join(0, x.tensor.shape[:2], [-1])
        new_tensor = x.tensor.reshape(tensor_shape, ndim=3)
        new_tensor = T.roll(new_tensor, shift, 2)
        new_tensor = new_tensor.reshape(x.tensor.shape, ndim=x.tensor.ndim)
    else:
        new_tensor = T.roll(x.tensor, shift, axis+2)
    return stencil_array(new_tensor, x.has_ghost)

def copy(a):
    assert _is_like_sa(a)
    return stencil_array(a.tensor, a.has_ghost)
    # return stencil_array(T.copy(a.tensor), a.has_ghost)


# ============================================================================ #
#                            mathematical functions                            #
# ============================================================================ #

def sin(a):
    assert _is_like_sa(a)
    return stencil_array(T.sin(a.tensor), a.has_ghost)

def cos(a):
    assert _is_like_sa(a)
    return stencil_array(T.cos(a.tensor), a.has_ghost)

def exp(a):
    assert _is_like_sa(a)
    return stencil_array(T.sin(a.tensor), a.has_ghost)


# ============================================================================ #
#                              atomic sa arrays                               #
# ============================================================================ #

i = stencil_array(T.tensor('float64', (False,) * 2), True)
j = stencil_array(T.tensor('float64', (False,) * 2), True)

def ij_np(i0, i1, j0, j1):
    return np.outer(np.arange(i0, i1), np.ones(j1 - j0, int)), \
           np.outer(np.ones(i1 - i0, int), np.arange(j0, j1))


# ============================================================================ #
#                          compiling into theano function                      #
# ============================================================================ #

def compile(func, inputs=(), args=(), argv={}, with_ij=True):
    np2theano = lambda a: T.Tensor('float64', (False,) * a.ndim)()
    input_list = [inputs] if hasattr(inputs, 'ndim') else list(inputs)
    theano_inputs = [np2theano(a) for a in input_list]
    sa_inputs = [stencil_array(a, True) for a in theano_inputs]

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

    if with_ij:
        theano_inputs += [i.tensor, j.tensor]
    return theano.function(theano_inputs, theano_outputs,
            on_unused_input='ignore')


# ============================================================================ #
#                                 unit tests                                   #
# ============================================================================ #

class TestOperators(unittest.TestCase):
    def testLaplacian(self):
        def laplacian(a):
            return (a.x_p + a.x_m + a.y_p + a.y_m - 4 * a) / 4
        a = np.ones([4,5])
        f = compile(laplacian, a, with_ij=False)
        self.assertEqual(f(a).shape, (2,3))
        self.assertAlmostEqual(abs(f(a)).max(), 0)

    def testNonlinear(self):
        def nlLaplacian(a):
            lapla = a.x_p + a.x_m + a.y_p + a.y_m - 4 * a
            return lapla * exp(a) / sin(a) * cos(a)
        a = np.ones([4,5])
        f = compile(nlLaplacian, a, with_ij=False)
        self.assertEqual(f(a).shape, (2,3))
        self.assertAlmostEqual(abs(f(a)).max(), 0)

    def testGradient(self):
        def grad(a):
            return (a.x_p - a.x_m) / 2, (a.y_p - a.y_m) / 2
        a = np.outer(np.ones(4), np.arange(5) * 2) \
          + np.outer(np.arange(4), np.ones(5)) + 1
        f = compile(grad, a, with_ij=False)
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
        f = compile(div, v, with_ij=False)
        vDiv = f(*v)
        self.assertEqual(vDiv.shape, (2,3))
        self.assertAlmostEqual(abs(vDiv - 5).max(), 0)

# ---------------------------------------------------------------------------- #

class TestIJ(unittest.TestCase):
    def testLaplacianByIpJ(self):
        def laplacian(a):
            return (a.x_p + a.x_m + a.y_p + a.y_m - 4 * a) / 4 * (i + j)
        a = np.ones([4,5])
        f = compile(laplacian, a)
        fa = f(a, *ij_np(0,a.shape[0],0,a.shape[1]))
        self.assertEqual(fa.shape, (2,3))
        self.assertAlmostEqual(abs(fa).max(), 0)

    def testDivYX(self):
        def divYX():
            x, y = i * 0.1, j * 0.2
            return y.x_p - y.x_m + x.y_p - x.y_m
        f = compile(divYX)
        fa = f(*ij_np(0,4,0,6))
        self.assertEqual(fa.shape, (2,4))
        self.assertAlmostEqual(abs(fa).max(), 0)

# ---------------------------------------------------------------------------- #

class TestTransforms(unittest.TestCase):
    def testTranspose1(self):
        def xtm1(a):
            return a.T - 1
        a = np.ones([4,5,2,3])
        f = compile(xtm1, a, with_ij=False)
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
        f = compile(xtm1, a, with_ij=False)
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
        f = compile(xrm1, a, with_ij=False)
        fa = f(a)
        self.assertEqual(fa.shape, (4,5,3,8))
        for i in range(4):
            self.assertAlmostEqual(abs(fa[:,:,:,i] - i).max(), 0)
            self.assertAlmostEqual(abs(fa[:,:,:,i+4] - i).max(), 0)

    def testRoll1(self):
        def xrm1(a):
            return roll(a, 1) - 1
        a = np.ones([4,5,2,3]) + np.arange(2)[:,np.newaxis]
        f = compile(xrm1, a, with_ij=False)
        fa = f(a)
        self.assertEqual(fa.shape, a.shape)
        self.assertAlmostEqual(abs(fa[:,:,0,1:]).max(), 0)
        self.assertAlmostEqual(abs(fa[:,:,1,0]).max(), 0)
        self.assertAlmostEqual(abs(fa[:,:,0,0] - 1).max(), 0)
        self.assertAlmostEqual(abs(fa[:,:,1,1:] - 1).max(), 0)

    def testRoll2(self):
        def xr0m1(a):
            return roll(a, 1, axis=0) - 1
        a = np.ones([4,5,2,3]) + np.arange(2)[:,np.newaxis]
        f = compile(xr0m1, a, with_ij=False)
        fa = f(a)
        self.assertEqual(fa.shape, a.shape)
        self.assertAlmostEqual(abs(fa[:,:,0,:] - 1).max(), 0)
        self.assertAlmostEqual(abs(fa[:,:,1,:]).max(), 0)

# ============================================================================ #
#                                                                              #
# ============================================================================ #

if __name__ == '__main__':
    unittest.main()

################################################################################
################################################################################
################################################################################
