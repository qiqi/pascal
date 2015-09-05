import numbers
import numpy as np

class array2d(object):
    def __init__(self, nx, ny, init_func):
        assert nx > 0
        assert ny > 0

        self._nx = int(nx)
        self._ny = int(ny)

        if init_func:
            j, i = np.meshgrid(np.arange(self._ny), np.arange(self._nx))
            data = np.array(init_func(i, j))

            # roll the last two axes, i and j, to the first two
            data = np.rollaxis(data, -1)
            data = np.rollaxis(data, -1)

            self._data = np.array(data, dtype=np.float64, order='C')

    @property
    def shape(self):
        return self._data.shape[2:]

    @property
    def size(self):
        return self._data[0,0].size

    @property
    def ndim(self):
        return self._data.ndim - 2

    @property
    def nx(self):
        return self._nx

    @property
    def ny(self):
        return self._ny

    def __neg__(self):
        y = empty_like(self)
        y._data[:] = -self._data
        return y

    def __radd__(self, a):
        return self.__add__(a)

    def __add__(self, a):
        if isinstance(a, array2d):
            assert a.nx == self.nx and a.ny == self.ny
            y = array2d(self.nx, self.ny, None)
            y._data = self._data + a._data
        elif isinstance(a, numbers.Number):
            y = empty_like(self)
            y._data[:] = self._data + a
        return y

    def __rmul__(self, a):
        return self.__mul__(a)

    def __mul__(self, a):
        if isinstance(a, array2d):
            assert a.nx == self.nx and a.ny == self.ny
            y = array2d(self.nx, self.ny, None)
            y._data = self._data * a._data
        elif isinstance(a, numbers.Number):
            y = empty_like(self)
            y._data[:] = self._data * a
        return y

    def __div__(self, a):
        return self.__truediv__(a)

    def __truediv__(self, a):
        if not isinstance(a, numbers.Number):
            return NotImplemented
        y = empty_like(self)
        y._data[:] = self._data / a
        return y

    def __pow__(self, a):
        if not isinstance(a, numbers.Number):
            return NotImplemented
        y = empty_like(self)
        y._data[:] = self._data**a
        return y

def empty_like(a):
    b = array2d(a.nx, a.ny, None)
    b._data = np.empty((a.nx, a.ny) + a.shape)
    return b

def exp(x):
    if isinstance(x, array2d):
        y = empty_like(x)
        y._data[:] = np.exp(x._data)
        return y
    else:
        return np.exp(x)

def sqrt(x):
    if isinstance(x, array2d):
        y = empty_like(x)
        y._data[:] = np.sqrt(x._data)
        return y
    else:
        return np.sqrt(x)

def sin(x):
    y = empty_like(x)
    y._data[:] = np.sin(x._data)
    return y

def cos(x):
    y = empty_like(x)
    y._data[:] = np.cos(x._data)
    return y

def log(x):
    y = empty_like(x)
    y._data[:] = np.log(x._data)
    return y

def copy(x):
    y = empty_like(x)
    y._data[:] = x._data
    return y

def ravel(x):
    y = empty_like(x)
    y._data[:] = x._data
    y._data = y._data.reshape(y.shape + (y.size,))
    return y

def transpose(x, axes=None):
    y = empty_like(x)
    y._data[:] = x._data
    if axes is None:
        axes = reversed(tuple(range(x.ndim)))
    y._data = y._data.transpose((0, 1) + tuple(i+2 for i in axes))
    return y


if __name__ == '__main__':
    a = array2d(2,2,lambda i,j : [[i,j], [i,j]])
    b = exp(a)
