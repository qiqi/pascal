################################################################################
#                                                                              #
#       sa2d_theano.py copyright(c) Qiqi Wang 2015 (qiqi.wang@gmail.com)       #
#                                                                              #
################################################################################

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
    return hasattr(a, '_tensor') and hasattr(a, 'has_ghost')

def _promote_ndim(t, ndim):
    if t.ndim == ndim:
        return t
    else:
        assert t.ndim < ndim
        pad_dim = T.ones(ndim - t.ndim, int)
        if t.ndim == 2:
            new_shape = T.join(0, t.shape[:2], pad_dim)
        else:
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
        at = _promote_ndim(a._tensor, ndim)
        bt = _promote_ndim(b._tensor, ndim)
        if a.has_ghost and not b.has_ghost:
            if not _is_broadcastable(at):
                at = at[1:-1,1:-1]
        elif not a.has_ghost and b.has_ghost:
            if not _is_broadcastable(bt):
                bt = bt[1:-1,1:-1]
        shape = op(np.ones(a.shape), np.ones(b.shape)).shape
        return stencil_array(op(at, bt), shape, a.has_ghost and b.has_ghost)
    elif _is_like_sa(a):
        shape = op(np.ones(a.shape), b).shape
        if len(shape) > a.ndim:
            at = _promote_ndim(a._tensor, len(shape) + 2)
        else:
            at = a._tensor
        return stencil_array(op(at, b), shape, a.has_ghost)
    elif _is_like_sa(b):
        shape = op(a, np.ones(b.shape)).shape
        if len(shape) > b.ndim:
            bt = _promote_ndim(b._tensor, len(shape) + 2)
        else:
            bt = b._tensor
        return stencil_array(op(a, bt), shape, b.has_ghost)


# ============================================================================ #
#                                                                              #
# ============================================================================ #

class stencil_array(object):
    '''
    Objects involved in computation.  It should be used like theano arrays,
    except functions like sin and exp should use the ones defined in this module
    '''
    __context__ = sys.modules[__name__]

    def __init__(self, tensor, shape, has_ghost):
        if tensor is not None:
            assert tensor.ndim == len(shape) + 2
        else:
            tensor_type = T.Tensor('float64', (False,) * (len(shape) + 2))
            tensor = tensor_type()
        for i in shape:
            assert isinstance(i, int)
        self.shape = tuple(shape)
        self._tensor = tensor
        self.has_ghost = has_ghost

    # --------------------------- properties ------------------------------ #

    @property
    def value(self):
        return self._tensor

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
        return stencil_array(-self._tensor, self.shape, self.has_ghost)

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
        if _is_broadcastable(self._tensor):
            return self
        else:
            return stencil_array(self._tensor[2:,1:-1], self.shape, False)

    @property
    def x_m(self):
        assert self.has_ghost, 'Has No Ghost'
        if _is_broadcastable(self._tensor):
            return self
        else:
            return stencil_array(self._tensor[:-2,1:-1], self.shape, False)

    @property
    def y_p(self):
        assert self.has_ghost, 'Has No Ghost'
        if _is_broadcastable(self._tensor):
            return self
        else:
            return stencil_array(self._tensor[1:-1,2:], self.shape, False)

    @property
    def y_m(self):
        assert self.has_ghost, 'Has No Ghost'
        if _is_broadcastable(self._tensor):
            return self
        else:
            return stencil_array(self._tensor[1:-1,:-2], self.shape, False)

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
        return stencil_array(self._tensor[tensor_ind], shape, self.has_ghost)

    def __setitem__(self, ind, a):
        sub_tensor = self._tensor[self._data_index_(ind)]
        if not _is_like_sa(a):
            self._tensor = T.set_subtensor(sub_tensor, a)
        else:
            a_tensor = _promote_ndim(a._tensor, sub_tensor.ndim)
            if _is_broadcastable(self._tensor):
                z = T.zeros_like(a_tensor)
                while z.ndim > 2:
                    z = z[:,:,0]
                self._tensor = self._tensor + _promote_ndim(z, self._tensor.ndim)
                self.has_ghost = a.has_ghost
                sub_tensor = self._tensor[self._data_index_(ind)]

            if a.has_ghost == self.has_ghost or _is_broadcastable(a_tensor):
                self._tensor = T.set_subtensor(sub_tensor, a_tensor)
            elif a.has_ghost:   # self has no ghost
                self._tensor = T.set_subtensor(sub_tensor, a_tensor[1:-1,1:-1])
            else:               # self has ghost but a does not
                sub_tensor = self._tensor[1:-1,1:-1][self._data_index_(ind)]
                self._tensor = T.set_subtensor(sub_tensor, a_tensor)
                self.has_ghost = False

# ============================================================================ #
#                             data transformations                             #
# ============================================================================ #

def transpose(x, axes=None):
    if axes is None:
        axes = tuple(reversed(range(x.ndim)))
    transposed_shape = tuple(x.shape[i] for i in axes)
    transposed_tensor = x._tensor.transpose((0, 1) + tuple(i+2 for i in axes))
    return stencil_array(transposed_tensor, transposed_shape, x.has_ghost)

def reshape(x, shape):
    shape = np.empty(x.shape).reshape(shape).shape
    ndim = len(shape) + 2
    if len(shape):
        tensor_shape = T.join(0, x._tensor.shape[:2], shape)
    else:
        tensor_shape = x._tensor.shape[:2]
    reshaped_tensor = x._tensor.reshape(tensor_shape, ndim=ndim)
    return stencil_array(reshaped_tensor, shape, x.has_ghost)

def roll(x, shift, axis=None):
    if axis is None:
        tensor_shape = T.join(0, x._tensor.shape[:2], [-1])
        new_tensor = x._tensor.reshape(tensor_shape, ndim=3)
        new_tensor = T.roll(new_tensor, shift, 2)
        new_tensor = new_tensor.reshape(x._tensor.shape, ndim=x._tensor.ndim)
    else:
        new_tensor = T.roll(x._tensor, shift, axis+2)
    return stencil_array(new_tensor, x.shape, x.has_ghost)

def copy(a):
    assert _is_like_sa(a)
    return stencil_array(a._tensor, a.shape, a.has_ghost)


# ============================================================================ #
#                            mathematical functions                            #
# ============================================================================ #

def sin(a):
    assert _is_like_sa(a)
    return stencil_array(T.sin(a._tensor), a.shape, a.has_ghost)

def cos(a):
    assert _is_like_sa(a)
    return stencil_array(T.cos(a._tensor), a.shape, a.has_ghost)

def exp(a):
    assert _is_like_sa(a)
    return stencil_array(T.sin(a._tensor), a.shape, a.has_ghost)

def sum(a, axis=None):
    assert _is_like_sa(a)
    if axis is None:
        tensor_shape = T.join(0, a._tensor.shape[:2], [a.size])
        tensor = T.sum(T.reshape(a._tensor, tensor_shape, ndim=3), axis=2)
        return stencil_array(tensor, (), a.has_ghost)
    else:
        shape = np.zeros(a.shape).sum(axis).shape
        tensor = T.sum(a._tensor, axis+2)
        return stencil_array(tensor, shape, a.has_ghost)

def mean(a, axis=None):
    assert _is_like_sa(a)
    if axis is None:
        tensor_shape = T.join(0, a._tensor.shape[:2], [a.size])
        tensor = T.mean(T.reshape(a._tensor, tensor_shape, ndim=3), axis=2)
        return stencil_array(tensor, (), a.has_ghost)
    else:
        shape = np.zeros(a.shape).mean(axis).shape
        tensor = T.mean(a._tensor, axis+2)
        return stencil_array(tensor, shape, a.has_ghost)

# ============================================================================ #
#                               sa arrays generators                         #
# ============================================================================ #

def ones(shape=()):
    shape = np.ones(shape).shape
    return stencil_array(T.ones((1,1) + shape), shape, has_ghost=True)

def zeros(shape=()):
    shape = np.zeros(shape).shape
    return stencil_array(T.zeros((1,1) + shape), shape, has_ghost=True)

# ============================================================================ #
#                          compiling into theano function                      #
# ============================================================================ #

def compile(input_values, output_values):
    if hasattr(input_values, 'shape') and \
            hasattr(input_values, 'broadcastable'):
        input_values = [input_values]
    return theano.function(input_values, output_values,
                           on_unused_input='ignore', mode='FAST_COMPILE')

def numpy_to_sa(a):
    assert isinstance(a, np.ndarray)
    return stencil_array(None, a.shape[2:], True)

def compile_function(func, inputs=(), args=(), argv={}):
    input_list = [inputs] if hasattr(inputs, 'ndim') else list(inputs)
    sa_inputs = list(map(numpy_to_sa, input_list))
    input_values = [sa.value for sa in sa_inputs]

    if hasattr(inputs, 'ndim'):
        sa_outputs = func(sa_inputs[0], *args, **argv)
    elif len(inputs):
        sa_outputs = func(sa_inputs, *args, **argv)
    else:
        sa_outputs = func(*args, **argv)

    if _is_like_sa(sa_outputs):
        output_values = sa_outputs.value
    else:
        output_values = [sa.value for sa in sa_outputs]

    return compile(input_values, output_values)

################################################################################
################################################################################
################################################################################
