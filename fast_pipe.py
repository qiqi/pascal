import os
import sys
import time
import unittest
import multiprocessing
import numpy

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
        else:
            assert isinstance(init, PipeCore) and init._i_end == 0
            self._len = init._len
            self._i_end = 1
            self._data = init._data

    def exchange(self, a_in, a_out, tag):
        '''
        Structure of self._data:
            self._data[0:self._len]: buffer to contain transmitted data
            self._data[self._len]:   length of transmitted data
            self._data[self._len+1]: tag
            self._data[self._len+2]: used in _copyFrom_long and _copyInto_long
                                to store currently transmitting array position
        '''
        assert a_in.ndim == 1 and a_out.ndim == 1 and a_in.size == a_out.size
        i_in, i_out = self._i_end, 1 - self._i_end
        while not numpy.isnan(self._data[i_in, self._len+1]): pass
        if a_in.size <= self._len:
            self._data[i_in, self._len] = a_in.size
            self._data[i_in, 0:a_in.size] = a_in
            self._data[i_in, self._len+1] = tag

            while self._data[i_out, self._len+1] != tag: pass
            a_out[:] = self._data[i_out, :a_out.size]
        else:
            self._data[i_in, self._len+1] = tag
            while self._data[i_out, self._len+1] != tag: pass
            self._exchange_long(a_in, a_out)
        self._data[i_out, self._len+1] = numpy.nan

    def _exchange_long(self, a_in, a_out):
        i_in, i_out = self._i_end, 1 - self._i_end
        self._data[i_in, self._len+2] = numpy.nan

        i0, i1 = 0, self._len
        while i0 < a_in.size:
            while not numpy.isnan(self._data[i_in, self._len+2]): pass
            self._data[i_in, :i1-i0] = a_in[i0:i1]
            self._data[i_in, self._len+2] = i0

            while self._data[i_out, self._len+2] != i0: pass
            a_out[i0:i1] = self._data[i_out, :i1-i0]
            self._data[i_out, self._len+2] = numpy.nan

            i0, i1 = i1, min(i1 + self._len, a_out.size)


# ============================================================================ #

def Pipe(length=10000):
    p0 = PipeCore(length)
    p1 = PipeCore(p0)
    return p0, p1


# ============================================================================ #
#                                  unit tests                                  #
# ============================================================================ #

class TestPipe(unittest.TestCase):
    def _test(self, m, pipe_length):
        n = 1000
        p0, p1 = Pipe(pipe_length)

        def f(n, p):
            a, b = numpy.zeros([2,m])
            for i in range(n):
                a[:] = i
                p.exchange(a, b, i)
                self.assertEqual(numpy.abs(b - i).max(), 0)

        p = multiprocessing.Process(target=f, args=(n, p1))
        p.start()

        t0 = time.time()
        f(n, p0)
        latency = (time.time() - t0) / (n*2)

        p.join()
        return latency

    def testLatency(self):
        print('\nLatency')
        latency = self._test(1, 1)
        print('1-way latency: ', latency * 1E6, 'us')
        self.assertLess(latency, 2E-5)

    def testLatencyBandwidth(self):
        print('\nLatency Bandwidth')
        n = 1000
        for m in [10, 100, 1000, 10000, 100000]:
            latency = self._test(m, m)
            print(m * 8, 'bytes', latency * 1E6, 'us')

    def testUndersizeLatency(self):
        print('\nUndersize')
        n = 1000
        for m in [1, 10, 100, 1000, 10000, 100000]:
            latency = self._test(m, 100000)
            print(m * 8, 'bytes', latency * 1E6, 'us')

    def testOversizeLatency(self):
        print('\nOversize')
        n = 1000
        for m in [1, 10, 100, 1000, 10000, 100000]:
            latency = self._test(m, 100)
            print(m * 8, 'bytes', latency * 1E6, 'us')

if __name__ == '__main__':
    unittest.main()
