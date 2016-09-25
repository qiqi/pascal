################################################################################
#                                                                              #
#   symbolic_variable.py copyright(c) Qiqi Wang 2015 (qiqi.wang@gmail.com)     #
#                                                                              #
################################################################################

import sys
import pdb

import numpy as np

from . import operators
from . import symbolic_value
from .symbolic_value import _is_like_sa_value, symbolic_array_value
from .symbolic_value import builtin as builtin_values
from .symbolic_value import AtomicStage

__all__ = ['symbolic_array', 'decompose', 'im', 'ip', 'km', 'kp', 'jm', 'jp',
           'transpose', 'reshape', 'roll', 'copy', 'sin', 'cos', 'exp',
           'sum', 'mean', 'builtin', 'ones', 'zeros']

# ============================================================================ #

def _is_like_sa(a):
    '''
    Check if object has a stencil array value
    '''
    return hasattr(a, 'value') and _is_like_sa_value(a.value)

# ============================================================================ #
#                          stencil array variable                              #
# ============================================================================ #

class symbolic_array(object):

    __context__ = sys.modules[__name__]

    def __init__(self, init=()):
        if _is_like_sa_value(init):
            self.value = init
        else:
            shape = init
            if isinstance(shape, int):
                shape = (shape,)
            self.value = symbolic_array_value(shape)

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
        # if hasattr(a, '__array_priority__') and \
        #         a.__array_priority__ > self.__array_priority__:
        #     return a.__add__(self)
        a = a.value if _is_like_sa(a) else a
        return symbolic_array(operators.add(self.value, a).output)

    def __radd__(self, a):
        return self.__add__(a)

    def __sub__(self, a):
        # if hasattr(a, '__array_priority__') and \
        #         a.__array_priority__ > self.__array_priority__:
        #     return a.__rsub__(self)
        a = a.value if _is_like_sa(a) else a
        return symbolic_array(operators.sub(self.value, a).output)

    def __rsub__(self, a):
        a = a.value if _is_like_sa(a) else a
        return symbolic_array(operators.sub(a, self.value).output)

    def __mul__(self, a):
        # if hasattr(a, '__array_priority__') and \
        #         a.__array_priority__ > self.__array_priority__:
        #     return a.__rmul__(self)
        a = a.value if _is_like_sa(a) else a
        return symbolic_array(operators.mul(self.value, a).output)

    def __rmul__(self, a):
        return self.__mul__(a)

    def __div__(self, a):
        return self.__truediv__(a)

    def __rdiv__(self, a):
        return self.__rtruediv__(a)

    def __truediv__(self, a):
        # if hasattr(a, '__array_priority__') and \
        #         a.__array_priority__ > self.__array_priority__:
        #     return a.__rtruediv__(self)
        a = a.value if _is_like_sa(a) else a
        return symbolic_array(operators.truediv(self.value, a).output)

    def __rtruediv__(self, a):
        # if hasattr(a, '__array_priority__') and \
        #         a.__array_priority__ > self.__array_priority__:
        #     return a.__truediv__(self)
        a = a.value if _is_like_sa(a) else a
        return symbolic_array(operators.truediv(a, self.value).output)

    def __pow__(self, a):
        # if hasattr(a, '__array_priority__') and \
        #         a.__array_priority__ > self.__array_priority__:
        #     return a.__rpow__(self)
        a = a.value if _is_like_sa(a) else a
        return symbolic_array(operators.pow(self.value, a).output)

    def __rpow__(self, a):
        a = a.value if _is_like_sa(a) else a
        return symbolic_array(operators.pow(a, self.value).output)

    def __neg__(self):
        return symbolic_array(operators.neg(self.value).output)

    # ------------------------- neighbor access --------------------------- #

    @property
    def im(self): return im(self)
    @property
    def ip(self): return ip(self)
    @property
    def jm(self): return jm(self)
    @property
    def jp(self): return jp(self)
    @property
    def km(self): return km(self)
    @property
    def kp(self): return kp(self)

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

    # ---------------------------- indexing ------------------------------- #

    def __getitem__(self, ind):
        return symbolic_array(operators.getitem(self.value, ind).output)

    def __setitem__(self, ind, a):
        a = a.value if _is_like_sa(a) else np.array(a, float)
        owner = operators.setitem(self.value, ind, a)
        assert self.shape == owner.output.shape
        self.value = owner.output


# ============================================================================ #
#                              neighbor access                                 #
# ============================================================================ #

def ip(a):
    return symbolic_array(operators.ip(a.value).output)

def im(a):
    return symbolic_array(operators.im(a.value).output)

def jp(a):
    return symbolic_array(operators.jp(a.value).output)

def jm(a):
    return symbolic_array(operators.jm(a.value).output)

def kp(a):
    return symbolic_array(operators.kp(a.value).output)

def km(a):
    return symbolic_array(operators.km(a.value).output)

# ============================================================================ #
#                             data transformations                             #
# ============================================================================ #

def transpose(x, axes=None):
    assert _is_like_sa(x)
    return symbolic_array(operators.transpose(x.value, axes).output)

def reshape(x, shape):
    assert _is_like_sa(x)
    return symbolic_array(operators.reshape(x.value, shape).output)

def roll(x, shift, axis=None):
    assert _is_like_sa(x)
    return symbolic_array(operators.roll(x.value, shift, axis).output)

def copy(x):
    assert _is_like_sa(x)
    return symbolic_array(x.value)


# ============================================================================ #
#                            mathematical functions                            #
# ============================================================================ #

def sin(a):
    assert _is_like_sa(a)
    return symbolic_array(operators.sin(a.value).output)

def cos(a):
    assert _is_like_sa(a)
    return symbolic_array(operators.cos(a.value).output)

def exp(a):
    assert _is_like_sa(a)
    return symbolic_array(operators.exp(a.value).output)

def sum(a, axis=None):
    assert _is_like_sa(a)
    return symbolic_array(operators.sum(a.value, axis).output)

def mean(a, axis=None):
    assert _is_like_sa(a)
    n = np.ravel(np.ones(a.shape, int).sum(axis))[0]
    return sum(a, axis) / float(n)

# ============================================================================ #
#                             array generators                                 #
# ============================================================================ #

class builtin:
    ZERO = symbolic_array(builtin_values.ZERO)
    I = symbolic_array(builtin_values.I)
    J = symbolic_array(builtin_values.J)
    K = symbolic_array(builtin_values.K)

def ones(shape=()):
    return builtin.ZERO + np.ones(shape)

def zeros(shape=()):
    return builtin.ZERO + np.zeros(shape)


# ============================================================================ #
#                                decomposition                                 #
# ============================================================================ #

def _stack_input(stage):
    input_total_size = np.sum([v.size for v in stage.input_values], dtype=int)
    stacked_input_array = symbolic_array((input_total_size,))
    stacked_input_value = stacked_input_array.value
    # split stacked input array
    input_map = {}
    i_ptr = 0
    for v in stage.input_values:
        array_slice = stacked_input_array[i_ptr:i_ptr+v.size]
        input_map[v] = array_slice.reshape(v.shape)
        i_ptr += v.size
    for v in stage.additional_input_values:
        input_map[v] = symbolic_array(v)
    # construct stage based on stacked input values
    output_arrays = stage(input_map)
    output_values = [a.value for a in output_arrays]
    return AtomicStage([stacked_input_value], output_values)

def _stack_output(stage):
    output_total_size = np.sum([v.size for v in stage.output_values], dtype=int)
    stacked_output_array = zeros((output_total_size,))
    i_ptr = 0
    for v in stage.output_values:
        output_array_slice = symbolic_array(v).reshape((v.size,))
        stacked_output_array[i_ptr:i_ptr+v.size] = output_array_slice
        i_ptr += v.size
    return AtomicStage(stage.input_values, [stacked_output_array.value])

def decompose(func, inputs=symbolic_array(), stack_input_output=True,
              comp_graph_output_file=None, init_graph_output_file=None):
    if not isinstance(inputs, (tuple, list)):
        inputs = (inputs,)
    inputs = tuple([symbolic_array(inp.shape) for inp in inputs])
    input_values = tuple(inp.value for inp in inputs)
    outputs = func(*inputs)
    if not isinstance(outputs, tuple):
        outputs = (outputs,)
    output_values = tuple(out.value for out in outputs)
    stages, inits = symbolic_value.decompose(input_values, output_values,
                                             comp_graph_output_file,
                                             init_graph_output_file)
    if stack_input_output:
        for s in (stages, inits):
            for k in range(len(s)):
                s[k] = _stack_output(s[k])
                s[k] = _stack_input(s[k])
    return stages, inits

################################################################################
################################################################################
################################################################################
