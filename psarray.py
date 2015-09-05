import numbers
import numpy as np

# =============================================================================#
#                                 grid2d class                                 #
# =============================================================================#

class grid2d(object):
    def __init__(self, nx, ny):
        assert nx > 0
        assert ny > 0

        self._nx = int(nx)
        self._ny = int(ny)

    @property
    def nx(self):
        return self._nx

    @property
    def ny(self):
        return self._ny

    # ---------------------------------------------------------------------#
    #                           array constructors                         #
    # ---------------------------------------------------------------------#

    def array(self, init_func):
        return psarray(self, init_func)

    def empty(self, shape):
        a = self.array(None)
        a._data = np.empty((self.nx, self.ny) + tuple(shape))
        return a

    def zeros(self, shape):
        a = self.array(None)
        a._data = np.zeros((self.nx, self.ny) + tuple(shape))
        return a

    def ones(self, shape):
        a = self.array(None)
        a._data = np.ones((self.nx, self.ny) + tuple(shape))
        return a

    def random(self, shape=()):
        a = self.array(None)
        a._data = np.random.random((self.nx, self.ny) + tuple(shape))
        return a

    # ---------------------------------------------------------------------#
    #                            global operations                         #
    # ---------------------------------------------------------------------#

    def sum(self, a):
        assert a.grid == self
        return a._data.sum(axis=(0,1))

# =============================================================================#
#                                 psarray class                                #
# =============================================================================#

class psarray(object):
    def __init__(self, grid, init_func):
        self.grid = grid
        assert grid.nx > 0
        assert grid.ny > 0

        if init_func:
            j, i = np.meshgrid(np.arange(self.ny), np.arange(self.nx))
            data = np.array(init_func(i, j))

            # roll the last two axes, i and j, to the first two
            data = np.rollaxis(data, -1)
            data = np.rollaxis(data, -1)

            self._data = np.array(data, dtype=np.float64, order='C')

    # ---------------------------------------------------------------------#
    #                           size information                           #
    # ---------------------------------------------------------------------#

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
        return self.grid.nx

    @property
    def ny(self):
        return self.grid.ny

    # ---------------------------------------------------------------------#
    #                         access spatial neighbors                     #
    # ---------------------------------------------------------------------#

    @property
    def x_p(self):
        y = self.grid.array(None)
        y._data = np.roll(self._data, -1, axis=0)
        return y

    @property
    def x_m(self):
        y = self.grid.array(None)
        y._data = np.roll(self._data, +1, axis=0)
        return y

    @property
    def y_p(self):
        y = self.grid.array(None)
        y._data = np.roll(self._data, -1, axis=1)
        return y

    @property
    def y_m(self):
        y = self.grid.array(None)
        y._data = np.roll(self._data, +1, axis=1)
        return y

    # ---------------------------------------------------------------------#
    #                         algorithmic operations                       #
    # ---------------------------------------------------------------------#

    def __neg__(self):
        y = empty_like(self)
        y._data[:] = -self._data
        return y

    def __radd__(self, a):
        return self.__add__(a)

    def __add__(self, a):
        if isinstance(a, psarray):
            assert a.nx == self.nx and a.ny == self.ny
            y = self.grid.array(None)
            if self.ndim > 0 and a.ndim == 0:
                y._data = self._data + a._data[:,:,np.newaxis]
            elif self.ndim == 0 and a.ndim > 0:
                y._data = self._data[:,:,np.newaxis] + a._data
            else:
                y._data = self._data + a._data
        elif isinstance(a, numbers.Number):
            y = empty_like(self)
            y._data[:] = self._data + a
        elif isinstance(a, np.ndarray):
            y = self.grid.array(None)
            y._data = self._data + a
        else:
            return NotImplemented
        return y

    def __rsub__(self, a):
        return a + (-self)

    def __sub__(self, a):
        return self + (-a)

    def __rmul__(self, a):
        return self.__mul__(a)

    def __mul__(self, a):
        if isinstance(a, psarray):
            assert a.nx == self.nx and a.ny == self.ny
            y = self.grid.array(None)
            if self.ndim > 0 and a.ndim == 0:
                y._data = self._data * a._data[:,:,np.newaxis]
            elif self.ndim == 0 and a.ndim > 0:
                y._data = self._data[:,:,np.newaxis] * a._data
            else:
                y._data = self._data * a._data
        elif isinstance(a, numbers.Number):
            y = empty_like(self)
            y._data[:] = self._data * a
        elif isinstance(a, np.ndarray):
            y = self.grid.array(None)
            y._data[:] = self._data * a
        return y

    def __div__(self, a):
        return self.__truediv__(a)

    def __truediv__(self, a):
        if isinstance(a, psarray):
            assert a.nx == self.nx and a.ny == self.ny
            y = self.grid.array(None)
            if self.ndim > 0 and a.ndim == 0:
                y._data = self._data / a._data[:,:,np.newaxis]
            elif self.ndim == 0 and a.ndim > 0:
                y._data = self._data[:,:,np.newaxis] / a._data
            else:
                y._data = self._data / a._data
        elif isinstance(a, numbers.Number):
            y = empty_like(self)
            y._data[:] = self._data / a
        elif isinstance(a, np.ndarray):
            y = self.grid.array(None)
            y._data[:] = self._data / a
        return y

    def __pow__(self, a):
        if not isinstance(a, numbers.Number):
            return NotImplemented
        y = empty_like(self)
        y._data[:] = self._data**a
        return y

    # ---------------------------------------------------------------------#
    #                               indexing                               #
    # ---------------------------------------------------------------------#

    def _data_index_(self, ind):
        if not isinstance(ind, tuple):
            ind = (ind,)
        ind = (slice(None,None,None),) * 2 + ind
        return ind

    def __getitem__(self, ind):
        ind = self._data_index_(ind)
        a = self.grid.array(None)
        a._data = self._data[ind]
        return a
        
    def __setitem__(self, ind, a):
        ind = self._data_index_(ind)
        if isinstance(a, psarray):
            assert a.nx == self.nx and a.ny == self.ny
            self._data[ind] = a._data
        elif isinstance(a, numbers.Number):
            self._data[ind] = a
        elif isinstance(a, np.ndarray):
            self._data[ind] = a


# =============================================================================#
#                                 array operations                             #
# =============================================================================#

def empty_like(a):
    b = a.grid.array(None)
    b._data = np.empty((a.nx, a.ny) + a.shape)
    return b

def exp(x):
    if isinstance(x, psarray):
        y = empty_like(x)
        y._data[:] = np.exp(x._data)
        return y
    else:
        return np.exp(x)

def sqrt(x):
    if isinstance(x, psarray):
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
    G = grid2d(2,2)
    a = G.array(lambda i,j : [[i,j], [i,j]])
    b = exp(a)

