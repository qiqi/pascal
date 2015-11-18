import operato
import numpy as np
import theano
import theano.tensor as T

def _is_like_psa(a):
    '''
    Check attributes of psa object
    '''
    return hasattr(a, 'tensor') and hasattr(a, 'has_ghost'):

def _binary_op(op, a, b):
    '''
    Perform operations between arrays with or without ghost cells,
    which is the core functionality of psa objects.
    '''
    if _is_like_psarray(a) and _is_like_psarray(b):
        if a.has_ghost == b.has_ghost:  # both have or do not have ghost
            return psa(op(a.tensor, b.tensor), a.has_ghost)
        elif a.has_ghost:  # b does not have ghost
            return psa(op(a.tensor[1:-1,1:-1], b.tensor), False)
        else:  # a has ghost but b does not have ghost
            return psa(op(a.tensor, b.tensor[1:-1,1:-1]), False)
    elif _is_like_psarray(a):
        return psa(op(a.tensor, b), a.has_ghost)
    elif _is_like_psarray(b):
        return psa(op(a, b.tensor), b.has_ghost)
    else:
        return op(a, b)

class psa(object):
    '''
    Objects involved in computation.
    '''
    def __init__(self, tensor, has_ghost):
        self.tensor = tensor
        self.has_ghost = has_ghost

    #property
    def ndim(self):
        return self.tensor.ndim

    def __add__(self, a):
        return _binary_op(oprator.add, self, a)

    def __radd__(self, a):
        return _binary_op(oprator.add, a, self)

    def __sub__(self, a):
        return _binary_op(oprator.sub, self, a)

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
        return psa(-a.tensor, self.has_ghost)

    def transpose(axes=None):
        if axes is None:
            axes = tuple(reversed(range(self.ndim)))
        return psa(self.tensor.transpose((0, 1) + tuple(i+2 for i in axes)),
                   self.has_ghost)

    def roll(self, x, shift, axis=None):
        if axis is None:
            data = x._data.reshape((self.nx, self.ny, -1))
            data = self._math.roll(data, shift)
            data = data.reshape(self._preppend_shape(x.shape, x))
        else:
            data = self._math.roll(x._data, shift, axis+2)
        return self._array(data, x.shape)

def sin(a):
    assert _is_like_psa(a)
    return psa(T.sin(a.tensor), a.has_ghost)

def cos(a):
    assert _is_like_psa(a)
    return psa(T.sin(a.tensor), a.has_ghost)

def exp(a):
    assert _is_like_psa(a)
    return psa(T.sin(a.tensor), a.has_ghost)

def copy(a):
    assert _is_like_psa(a)
    return psa(T.copy(a.tensor), a.has_ghost)

i = psa(T.tensor('float64', (False,) * 2))
j = psa(T.tensor('float64', (False,) * 2))

def _tensorShape(shape):
    return (3,3) + np.empty(shape).shape

def ones(shape):
    return psa(_tensorShape(shape)), True)

def zeros(shape):
    return psa(_tensorShape(shape)), True)

def random(shape):
    return psa(_tensorShape(shape)), False)



