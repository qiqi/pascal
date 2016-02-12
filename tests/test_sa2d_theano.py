import os
import sys
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..'))

from pascal.sa2d_theano import *


class _TestOperators(unittest.TestCase):
    def testLaplacian(self):
        def laplacian(a):
            z = zeros()
            zz = (z.x_p + z.x_m + z.y_p + z.y_m - 4 * z) / 4
            return (a.x_p + a.x_m + a.y_p + a.y_m - 4 * a) / 4 + zz
        a = np.ones([4,5])
        f = compile_function(laplacian, a)
        self.assertEqual(f(a).shape, (2,3))
        a = np.ones([6,7])
        self.assertEqual(f(a).shape, (4,5))
        self.assertAlmostEqual(abs(f(a)).max(), 0)

    def testNonlinear(self):
        def nlLaplacian(a):
            lapla = -4 * a + a.x_p + a.x_m + a.y_p + a.y_m
            return lapla * exp(a) / sin(a) * cos(a)
        a = np.ones([4,5])
        f = compile_function(nlLaplacian, a)
        self.assertEqual(f(a).shape, (2,3))
        a = np.ones([6,7])
        self.assertEqual(f(a).shape, (4,5))
        self.assertAlmostEqual(abs(f(a)).max(), 0)

    def testGradient(self):
        def grad(a):
            return (a.x_p - a.x_m) / 2, (a.y_p - a.y_m) / 2
        a = np.outer(np.ones(4), np.arange(5) * 2) \
          + np.outer(np.arange(4), np.ones(5)) + 1
        f = compile_function(grad, a)
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
        f = compile_function(div, v)
        vDiv = f(*v)
        self.assertEqual(vDiv.shape, (2,3))
        self.assertAlmostEqual(abs(vDiv - 5).max(), 0)

    def testArbitrary(self):
        def arb(a):
            b = 3 + (a.x_p + a.x_m)
            c = -1 - np.ones(6) * b
            d = ones(6) ** (a / (ones([5,6]) / c))
            e = b ** np.ones(6) ** (a / (np.ones([5,6]) / d))
            f = np.ones([2,1,6]) + a - np.zeros([1,2,5,1])
            return -d
        a = np.ones([3,4,5,6])
        f = compile_function(arb, a)
        self.assertEqual(f(a).shape, (1,2,5,6))

    def testNoArg(self):
        def func():
            return -ones([2,3,4]) * 123
        f = compile_function(func)
        self.assertEqual(f().shape, (1,1,2,3,4))
        self.assertAlmostEqual(abs(f() + 123).max(), 0)

# ---------------------------------------------------------------------------- #

class _TestIJ(unittest.TestCase):
    @staticmethod
    def ij_np(i0, i1, j0, j1):
        return np.outer(np.arange(i0, i1), np.ones(j1 - j0, int)), \
               np.outer(np.ones(i1 - i0, int), np.arange(j0, j1))

    def testLaplacianByIpJ(self):
        def laplacian(inputs):
            a, i, j = inputs
            return (a.x_p + a.x_m + a.y_p + a.y_m - 4 * a) / 4 * (i + j)
        a = np.ones([4,5])
        i, j = self.ij_np(0,a.shape[0],0,a.shape[1])
        f = compile_function(laplacian, (a, i, j))
        fa = f(a, i, j)
        self.assertEqual(fa.shape, (2,3))
        self.assertAlmostEqual(abs(fa).max(), 0)

    def testDivYX(self):
        def divYX(inputs):
            i, j = inputs
            x, y = i * 0.1, j * 0.2
            return y.x_p - y.x_m + x.y_p - x.y_m
        i, j = self.ij_np(-1,3,-1,5)
        f = compile_function(divYX, (i, j))
        fa = f(i, j)
        self.assertEqual(fa.shape, (2,4))
        self.assertAlmostEqual(abs(fa).max(), 0)

# ---------------------------------------------------------------------------- #

class _TestTransforms(unittest.TestCase):
    def testSize(self):
        def size_a(a):
            return ones(()) * a.size
        a = np.ones([4,5,2,3])
        f = compile_function(size_a, a)
        fa = f(a)
        self.assertEqual(fa.shape, (1,1))
        self.assertAlmostEqual(abs(fa - 6).max(), 0)

    def testLen(self):
        def len_a(a):
            return zeros(()) + len(a)
        a = np.ones([4,5,2,3])
        f = compile_function(len_a, a)
        fa = f(a)
        self.assertEqual(fa.shape, (1,1))
        self.assertAlmostEqual(abs(fa - 2).max(), 0)

    def testTranspose1(self):
        def xtm1(a):
            return a.T - 1
        a = np.ones([4,5,2,3])
        f = compile_function(xtm1, a)
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
        f = compile_function(xtm1, a)
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
        f = compile_function(xrm1, a)
        fa = f(a)
        self.assertEqual(fa.shape, (4,5,3,8))
        for i in range(4):
            self.assertAlmostEqual(abs(fa[:,:,:,i] - i).max(), 0)
            self.assertAlmostEqual(abs(fa[:,:,:,i+4] - i).max(), 0)

    def testReshape0(self):
        def xrm1(a):
            return a.reshape(())
        a = np.ones([4,5,1])
        f = compile_function(xrm1, a)
        fa = f(a)
        self.assertEqual(fa.shape, (4,5))
        self.assertAlmostEqual(abs(fa - 1).max(), 0)

    def testRoll1(self):
        def xrm1(a):
            return roll(a, 1) - 1
        a = np.ones([4,5,2,3]) + np.arange(2)[:,np.newaxis]
        f = compile_function(xrm1, a)
        fa = f(a)
        self.assertEqual(fa.shape, a.shape)
        self.assertAlmostEqual(abs(fa[:,:,0,1:]).max(), 0)
        self.assertAlmostEqual(abs(fa[:,:,1,0]).max(), 0)
        self.assertAlmostEqual(abs(fa[:,:,0,0] - 1).max(), 0)
        self.assertAlmostEqual(abs(fa[:,:,1,1:] - 1).max(), 0)

    def testRoll2(self):
        def xr0m1(a):
            return roll(a, 1, axis=0).copy() - 1
        a = np.ones([4,5,2,3]) + np.arange(2)[:,np.newaxis]
        f = compile_function(xr0m1, a)
        fa = f(a)
        self.assertEqual(fa.shape, a.shape)
        self.assertAlmostEqual(abs(fa[:,:,0,:] - 1).max(), 0)
        self.assertAlmostEqual(abs(fa[:,:,1,:]).max(), 0)

# ---------------------------------------------------------------------------- #

class _TestIndexing(unittest.TestCase):
    def testGetItem1(self):
        def pick12(a):
            return a[1,2]
        a = np.ones([3,4,5,1]) + np.arange(6)
        f = compile_function(pick12, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4))
        self.assertAlmostEqual(abs(fa - a[:,:,1,2]).max(), 0)

    def testGetItem2(self):
        def pickRange(a):
            return a[1:-1,1:-1]
        a = np.ones([3,4,5,1]) + np.arange(6)
        f = compile_function(pickRange, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4,3,4))
        self.assertAlmostEqual(abs(fa - a[:,:,1:-1,1:-1]).max(), 0)

    def testGetItem3(self):
        def pickLast(a):
            return a[-1]
        a = np.zeros([3,4,1]) + np.arange(5)
        f = compile_function(pickLast, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4))
        self.assertAlmostEqual(abs(fa - 4).max(), 0)

    def testSetItem1(self):
        def set12(a):
            a[1,2] = 0
            return a
        a = np.ones([3,4,5,1]) + np.arange(6)
        f = compile_function(set12, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4,5,6))
        self.assertAlmostEqual(abs(fa[:,:,1,2]).max(), 0)
        diff = fa - a
        diff[:,:,1,2] = 0
        self.assertAlmostEqual(abs(diff).max(), 0)

    def testSetItem2(self):
        def set12(a):
            a[1,2] = 2 * a[1,2].x_p
            return a
        a = np.ones([3,4,5,1]) + np.arange(6)
        f = compile_function(set12, a)
        fa = f(a)
        self.assertEqual(fa.shape, (1,2,5,6))
        self.assertAlmostEqual(abs(fa[:,:,1,2] - a[0,0,1,2] * 2).max(), 0)
        diff = fa - a[0,0]
        diff[:,:,1,2] = 0
        self.assertAlmostEqual(abs(diff).max(), 0)

    def testSetItem3(self):
        def setRange(a):
            b = a.y_p * 0
            b[1:-1,1:-1] = sin(a[2,3])
            return b
        a = np.ones([3,4,5,1]) + np.arange(6)
        f = compile_function(setRange, a)
        fa = f(a)
        self.assertEqual(fa.shape, (1,2,5,6))
        self.assertAlmostEqual(abs(fa[:,:,1:-1,1:-1] \
                             - np.sin(a[0,0,2,3])).max(), 0)
        fa[:,:,1:-1,1:-1] = 0
        self.assertAlmostEqual(abs(fa).max(), 0)

    def testSetItem4(self):
        def setToOnes(a):
            a[1,2:4] = ones(2)
            return a
        a = np.ones([3,4,5,1]) + np.arange(6)
        f = compile_function(setToOnes, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4,5,6))
        self.assertAlmostEqual(abs(fa[:,:,1,2:4] - 1).max(), 0)

    def testSetItem5(self):
        def setToOnes(a):
            b = zeros(4)
            b[1:3] = a[1:3,0] * 2
            a[0,:] = b
            return a
        a = np.ones([3,4,3,4]) + np.arange(4)
        f = compile_function(setToOnes, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4,3,4))
        self.assertAlmostEqual(abs(fa[:,:,0,[0,3]]).max(), 0)

# ---------------------------------------------------------------------------- #

class _TestSumMean(unittest.TestCase):
    def testSum1(self):
        def sum1(a):
            return a.sum()
        a = np.zeros([3,4,3,4]) + np.arange(4)
        f = compile_function(sum1, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4))
        self.assertAlmostEqual(abs(fa - 18).max(), 0)

    def testSum2(self):
        def sum1(a):
            return a.sum(1)
        a = np.zeros([3,4,3,4]) + np.arange(4)
        f = compile_function(sum1, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4,3))
        self.assertAlmostEqual(abs(fa - 6).max(), 0)

    def testMean1(self):
        def mean1(a):
            return a.mean()
        a = np.zeros([3,4,3,4]) + np.arange(4)
        f = compile_function(mean1, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4))
        self.assertAlmostEqual(abs(fa - 1.5).max(), 0)

    def testMean2(self):
        def mean2(a):
            return a.mean(1)
        a = np.zeros([3,4,3,4]) + np.arange(4)
        f = compile_function(mean2, a)
        fa = f(a)
        self.assertEqual(fa.shape, (3,4,3))
        self.assertAlmostEqual(abs(fa - 1.5).max(), 0)

# ============================================================================ #
#                                                                              #
# ============================================================================ #

if __name__ == '__main__':
    unittest.main()

################################################################################
################################################################################
################################################################################
