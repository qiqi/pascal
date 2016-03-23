###############################################################################
#                                                                              #
#       sa2d_decomp.py copyright(c) Qiqi Wang 2015 (qiqi.wang@gmail.com)       #
#                                                                              #
################################################################################

import builtins
import sys

import numpy as np

from . import operators
from . import sa2d_decomp_value
from .sa2d_decomp_value import _is_like_sa_value, stencil_array_value
from .sa2d_decomp_value import builtin as builtin_values
from .sa2d_decomp_value import AtomicStage

# ============================================================================ #

def _is_like_sa(a):
    '''
    Check if object has a stencil array value
    '''
    return hasattr(a, 'value') and _is_like_sa_value(a.value)

# ============================================================================ #
#                          stencil array variable                              #
# ============================================================================ #

class stencil_array(object):

    __context__ = sys.modules[__name__]

    def __init__(self, init=()):
        if _is_like_sa_value(init):
            self.value = init
        else:
            shape = init
            self.value = stencil_array_value(shape)

    def __repr__(self):
        return 'Variable holding {0}'.format(self.value)

    # --------------------------- properties ------------------------------ #

    @property
    def shape(self):
        return self.value.shape

    @property
    def ndim(self):
        return self.value.ndim

    @property
    def size(self):
        return self.value.size

    def __len__(self):
        return len(self.value)

    # --------------------------- operations ------------------------------ #

    # asks ndarray to use the __rops__ defined in this class
    __array_priority__ = 3000

    def __add__(self, a):
        if hasattr(a, '__array_priority__') and \
                a.__array_priority__ > self.__array_priority__:
            return a.__add__(self)
        a = a.value if _is_like_sa(a) else a
        return stencil_array(operators.add(self.value, a).output)

    def __radd__(self, a):
        return self.__add__(a)

    def __sub__(self, a):
        if hasattr(a, '__array_priority__') and \
                a.__array_priority__ > self.__array_priority__:
            return a.__rsub__(self)
        a = a.value if _is_like_sa(a) else a
        return stencil_array(operators.sub(self.value, a).output)

    def __rsub__(self, a):
        a = a.value if _is_like_sa(a) else a
        return stencil_array(operators.sub(a, self.value).output)

    def __mul__(self, a):
        if hasattr(a, '__array_priority__') and \
                a.__array_priority__ > self.__array_priority__:
            return a.__rmul__(self)
        a = a.value if _is_like_sa(a) else a
        return stencil_array(operators.mul(self.value, a).output)

    def __rmul__(self, a):
        return self.__mul__(a)

    def __div__(self, a):
        return self.__truediv__(a)

    def __rdiv__(self, a):
        return self.__rtruediv__(a)

    def __truediv__(self, a):
        if hasattr(a, '__array_priority__') and \
                a.__array_priority__ > self.__array_priority__:
            return a.__rtruediv__(self)
        a = a.value if _is_like_sa(a) else a
        return stencil_array(operators.truediv(self.value, a).output)

    def __rtruediv__(self, a):
        if hasattr(a, '__array_priority__') and \
                a.__array_priority__ > self.__array_priority__:
            return a.__truediv__(self)
        a = a.value if _is_like_sa(a) else a
        return stencil_array(operators.truediv(a, self.value).output)

    def __pow__(self, a):
        if hasattr(a, '__array_priority__') and \
                a.__array_priority__ > self.__array_priority__:
            return a.__rpow__(self)
        a = a.value if _is_like_sa(a) else a
        return stencil_array(operators.pow(self.value, a).output)

    def __rpow__(self, a):
        a = a.value if _is_like_sa(a) else a
        return stencil_array(operators.pow(a, self.value).output)

    def __neg__(self):
        return stencil_array(operators.neg(self.value).output)

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
    def i_p(self):
        return stencil_array(operators.i_p(self.value).output)

    @property
    def i_m(self):
        return stencil_array(operators.i_m(self.value).output)

    @property
    def j_p(self):
        return stencil_array(operators.j_p(self.value).output)

    @property
    def j_m(self):
        return stencil_array(operators.j_m(self.value).output)

    # ---------------------------- indexing ------------------------------- #

    def __getitem__(self, ind):
        return stencil_array(operators.getitem(self.value, ind).output)

    def __setitem__(self, ind, a):
        a = a.value if _is_like_sa(a) else np.array(a, float)
        owner = operators.setitem(self.value, ind, a)
        assert self.shape == owner.output.shape
        self.value = owner.output


# ============================================================================ #
#                             data transformations                             #
# ============================================================================ #

def transpose(x, axes=None):
    assert _is_like_sa(x)
    return stencil_array(operators.transpose(x.value, axes).output)

def reshape(x, shape):
    assert _is_like_sa(x)
    return stencil_array(operators.reshape(x.value, shape).output)

def roll(x, shift, axis=None):
    assert _is_like_sa(x)
    return stencil_array(operators.roll(x.value, shift, axis).output)

def copy(x):
    assert _is_like_sa(x)
    return stencil_array(x.value)


# ============================================================================ #
#                            mathematical functions                            #
# ============================================================================ #

def sin(a):
    assert _is_like_sa(a)
    return stencil_array(operators.sin(a.value).output)

def cos(a):
    assert _is_like_sa(a)
    return stencil_array(operators.cos(a.value).output)

def exp(a):
    assert _is_like_sa(a)
    return stencil_array(operators.exp(a.value).output)

def sum(a, axis=None):
    assert _is_like_sa(a)
    return stencil_array(operators.sum(a.value, axis).output)

def mean(a, axis=None):
    assert _is_like_sa(a)
    n = np.ravel(np.ones(a.shape, int).sum(axis))[0]
    return sum(a) / n

# ============================================================================ #
#                             array generators                                 #
# ============================================================================ #

class builtin:
    ZERO = stencil_array(builtin_values.ZERO)
    I = stencil_array(builtin_values.I)
    J = stencil_array(builtin_values.J)

def ones(shape=()):
    return builtin.ZERO + np.ones(shape)

def zeros(shape=()):
    return builtin.ZERO + np.zeros(shape)


# ============================================================================ #
#                                decomposition                                 #
# ============================================================================ #

def stack_upstream(stage):
    upstream_total_size = builtins.sum(
            [v.size for v in stage.upstream_values])
    stacked_upstream_array = stencil_array((upstream_total_size,))
    stacked_upstream_value = stacked_upstream_array.value
    # split stacked upstream array
    upstream_arrays = []
    i_ptr = 0
    for v in stage.upstream_values:
        array_slice = stacked_upstream_array[i_ptr:i_ptr+v.size]
        upstream_arrays.append(array_slice.reshape(v.shape))
        i_ptr += v.size
    # construct stage based on stacked upstream values
    triburary_arrays = [stencil_array(v) for v in stage.triburary_values]
    downstream_arrays = stage(upstream_arrays, triburary_arrays)
    downstream_values = [a.value for a in downstream_arrays]
    return AtomicStage([stacked_upstream_value], downstream_values)

def stack_downstream(stage):
    downstream_total_size = builtins.sum(
            [v.size for v in stage.downstream_values])
    stacked_downstream_array = zeros((downstream_total_size,))
    i_ptr = 0
    for v in stage.downstream_values:
        downstream_array_slice = stencil_array(v).reshape((v.size,))
        stacked_downstream_array[i_ptr:i_ptr+v.size] = downstream_array_slice
        i_ptr += v.size
    return AtomicStage(stage.upstream_values, [stacked_downstream_array.value])

def decompose_function(func, inputs, verbose=False,
                       stack_upstream_downstream=True):
    if not isinstance(inputs, (tuple, list)):
        inputs = (inputs,)
    inputs = tuple([stencil_array(inp.shape) for inp in inputs])
    upstream_values = tuple(inp.value for inp in inputs)
    outputs = func(*inputs)
    if not isinstance(outputs, tuple):
        outputs = (outputs,)
    downstream_values = tuple(out.value for out in outputs)
    stages = sa2d_decomp_value.decompose(upstream_values,
                                         downstream_values, verbose)
    if stack_upstream_downstream:
        for k in range(len(stages) - 1):
            stages[k] = stack_downstream(stages[k])
        for k in range(1, len(stages)):
            stages[k] = stack_upstream(stages[k])
    if verbose == 'visualize':
        for k, s in enumerate(stages):
            sa2d_decomp_value.visualize_graph(
                    'decomp_{0}.gv'.format(k),
                    s.upstream_values, s.downstream_values, False, color=k)
    return stages

################################################################################
################################################################################
################################################################################
