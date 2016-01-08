import os
import sys
import time
import unittest
import multiprocessing
import numpy

# ============================================================================ #

# ============================================================================ #

class PipeCore(object):
    '''
    PipeCore object, should be constructed in pairs using Pipe
    '''
    def __init__(self, init):
        if isinstance(init, int):
            self._len = init
            self._i_end = 0
            a = multiprocessing.Array('d', 2 * (self._len + 3))
            data = numpy.frombuffer(a.get_obj())
            self._data = data.reshape([2, self._len + 3])
            self._data[:,self._len+1] = numpy.nan
            self._tag = 0
        else:
            assert isinstance(init, PipeCore)
            assert init._i_end == 0 and init._tag == 0
            self._len = init._len
            self._i_end = 1
            self._data = init._data
            self._tag = 0
        self._waiting_array = None

    def exchange(self, a_in, a_out):
        '''
        exchange(self, a_in, a_out)
        a_in is copied into a_out at the other process.

        Structure of self._data:
            self._data[0:self._len]: buffer to contain transmitted data
            self._data[self._len]:   length of transmitted data
            self._data[self._len+1]: tag
            self._data[self._len+2]: used in _copyFrom_long and _copyInto_long
                                to store currently transmitting array position
        '''
        self._tag += 1
        assert a_in.size == a_out.size
        i_in, i_out = self._i_end, 1 - self._i_end
        while not numpy.isnan(self._data[i_in, self._len+1]): pass
        if a_in.size <= self._len:
            self._data[i_in, self._len] = a_in.size
            self._data[i_in, 0:a_in.size] = a_in.ravel()
            self._data[i_in, self._len+1] = self._tag
            self._waiting_array = a_out
        else:
            self._data[i_in, self._len+1] = self._tag
            while self._data[i_out, self._len+1] != self._tag: pass
            self._exchange_long(a_in, a_out)
            self._data[i_out, self._len+1] = numpy.nan
        return self

    def is_wait_over(self):
        if self._waiting_array is None:
            return True
        i_out = 1 - self._i_end
        if self._data[i_out, self._len+1] != self._tag:
            return False
        else:
            data = self._data[i_out, :self._waiting_array.size]
            self._waiting_array[:] = data.reshape(self._waiting_array.shape)
            self._data[i_out, self._len+1] = numpy.nan
            self._waiting_array = None
            return True

    def _exchange_long(self, a_in, a_out):
        i_in, i_out = self._i_end, 1 - self._i_end
        self._data[i_in, self._len+2] = numpy.nan

        a_out_tmp = a_out.ravel()

        a_in = a_in.ravel()
        i0, i1 = 0, self._len
        while i0 < a_in.size:
            while not numpy.isnan(self._data[i_in, self._len+2]): pass
            self._data[i_in, :i1-i0] = a_in[i0:i1]
            self._data[i_in, self._len+2] = i0

            while self._data[i_out, self._len+2] != i0: pass
            a_out_tmp[i0:i1] = self._data[i_out, :i1-i0]
            self._data[i_out, self._len+2] = numpy.nan

            i0, i1 = i1, min(i1 + self._len, a_out.size)
        a_out[:] = a_out_tmp.reshape(a_out.shape)


# ============================================================================ #

def Pipe(length=2000):
    '''
    Return a pair of pipes that can be used to exchange
    between multiprocessing processes numpy arrays of the same size
    >>> def f(p):
    ...    a = numpy.ones(10)
    ...    b = numpy.empty(10)
    ...    wait(p.exchange(a, b))
    ...    return b[0]
    >>> p0, p1 = Pipe()
    >>> proc = multiprocessing.Process(target=f, args=(p1,))
    >>> proc.start()
    >>> f(p0)
    1.0
    '''
    p0 = PipeCore(length)
    p1 = PipeCore(p0)
    return p0, p1


# ============================================================================ #

def wait(*p):
    '''
    Wait for all pipes to finish transmitting
    '''
    p = list(p)
    while p:
        for pi in p:
            if pi.is_wait_over():
                p.remove(pi)


# ============================================================================ #
#                                  unit tests                                  #
# ============================================================================ #

class TestPipe(unittest.TestCase):
    def _test(self, m):
        n = 2000
        p00, p01 = Pipe()
        p10, p11 = Pipe()

        def f(n, p0, p1):
            a = numpy.zeros([2,m])
            b = numpy.zeros([2,m,1])
            for i in range(n):
                a[:] = i
                p0.exchange(a[0], b[0])
                p1.exchange(a[1], b[1])
                wait(p0, p1)
                self.assertEqual(numpy.abs(b - i).max(), 0)

        p = multiprocessing.Process(target=f, args=(n, p01, p11))
        p.start()

        t0 = time.time()
        f(n, p00, p10)
        latency = (time.time() - t0) / (n*2)

        p.join()
        return latency

    def testLatency(self):
        print('\nLatency')
        latency = self._test(1)
        print('1-way latency: {0} us'.format(latency * 1E6))
        self.assertLess(latency, 3E-5)

    def testUndersizeLatency(self):
        print('\nUndersize')
        for m in [10, 100, 1000]:
            latency = self._test(m)
            print('{0} bytes: {1} us'.format(m * 8, latency * 1E6))

    def testOversizeLatency(self):
        print('\nOversize')
        for m in [5000, 10000]:
            latency = self._test(m)
            print('{0} bytes: {1} us'.format(m * 8, latency * 1E6))


# ============================================================================ #

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    unittest.main()
