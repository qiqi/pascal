import os
import sys
import time
import unittest
import multiprocessing
import numpy

class Pipe(object):
    def __init__(self, length):
        assert isinstance(length, int)
        self._len = length
        self._data = multiprocessing.Array('d', self._len + 1, lock=False)
        self._data[-1] = numpy.nan

    def copyInto(self, a, readyCode):
        while self._data[-1] != readyCode:
            pass
        a[:] = self._data[:-1]
        self._data[-1] = numpy.nan
        #assert a.size == self._len

    def copyFrom(self, a, readyCode):
        while not numpy.isnan(self._data[-1]):
            pass
        self._data[:-1] = a
        self._data[-1] = readyCode
        #assert a.size == self._len


# ============================================================================ #
#                                  unit tests                                  #
# ============================================================================ #

class TestPipe(unittest.TestCase):
    def testLatency(self):
        n, m = 1000, 1
        p0 = Pipe(m)
        p1 = Pipe(m)
        def f(n, p_out, p_in, whoami):
            a = numpy.zeros(m)
            for i in range(n):
                p_out.copyFrom(a, i)
                p_in.copyInto(a, i)

        p = multiprocessing.Process(target=f, args=(n, p0, p1, 1))
        p.start()
        t0 = time.time()
        f(n, p1, p0, 0)
        latency = (time.time() - t0) / (n*2)
        print('1-way latency: ', latency * 1E6, 'us')
        p.join()

        self.assertLess(latency, 2E-5)

    def testLatencyBandwidth(self):
        n = 1000
        for m in [1, 10, 100, 1000, 10000]:
            p0 = Pipe(m)
            p1 = Pipe(m)
            def f(n, p_out, p_in, whoami):
                a = numpy.zeros(m)
                for i in range(n):
                    p_out.copyFrom(a, i)
                    p_in.copyInto(a, i)

            p = multiprocessing.Process(target=f, args=(n, p0, p1, 1))
            p.start()
            t0 = time.time()
            f(n, p1, p0, 0)
            latency = (time.time() - t0) / (n*2)
            print(m * 8, 'bytes', latency * 1E6, 'us')
            p.join()

if __name__ == '__main__':
    unittest.main()
