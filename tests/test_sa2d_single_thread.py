import os
import sys
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..'))

from pascal.sa2d_single_thread import *

# ============================================================================ #

class _OpTest(unittest.TestCase):
    def __init__(self, *args, **kargs):
        unittest.TestCase.__init__(self, *args, **kargs)
        self.G = grid2d(8,8)

    def _testOp(self, func, x_shp):
        x = self.G.ones(x_shp)
        y0 = func(x)
        y1 = psc_compile(func)(x)
        self.assertAlmostEqual(0, np.abs((y0 - y1)._data).sum())


class _MathOps(_OpTest):
    def testAdd(self):
        self._testOp(lambda x: 1 + x, 3)
        self._testOp(lambda x: x + 1, 3)

        self._testOp(lambda x: x + np.ones(3), 3)
        self._testOp(lambda x: np.ones(3) + x, 3)
        self._testOp(lambda x: np.ones([4,2,3]) + x + np.ones([3]), [2,3])

        G = self.G
        self._testOp(lambda x: x + G.ones(3), 3)
        self._testOp(lambda x: G.ones(3) + x, 3)
        self._testOp(lambda x: G.ones([4,2,3]) + x + G.ones([3]), [2,3])

    def testSub(self):
        self._testOp(lambda x: 1 - x, 3)
        self._testOp(lambda x: x - 1, 3)

        self._testOp(lambda x: x - np.ones(3), 3)
        self._testOp(lambda x: np.ones(3) - x, 3)
        self._testOp(lambda x: np.ones([4,2,3]) - x - np.ones([3]), [2,3])

        G = self.G
        self._testOp(lambda x: x - G.ones(3), 3)
        self._testOp(lambda x: G.ones(3) - x, 3)
        self._testOp(lambda x: G.ones([4,2,3]) - x - G.ones([3]), [2,3])

    def testMul(self):
        self._testOp(lambda x: 1 * x, 3)
        self._testOp(lambda x: x * 1, 3)

        self._testOp(lambda x: x * np.ones(3), 3)
        self._testOp(lambda x: np.ones(3) * x, 3)
        self._testOp(lambda x: np.ones([4,2,3]) * x * np.ones([3]), [2,3])

        G = self.G
        self._testOp(lambda x: x * G.ones(3), 3)
        self._testOp(lambda x: G.ones(3) * x, 3)
        self._testOp(lambda x: G.ones([4,2,3]) * x * G.ones([3]), [2,3])

    def testDiv(self):
        self._testOp(lambda x: 1 / x, 3)
        self._testOp(lambda x: x / 1, 3)

        self._testOp(lambda x: x / np.ones(3), 3)
        self._testOp(lambda x: np.ones(3) / x, 3)
        self._testOp(lambda x: np.ones([4,2,3]) / x / np.ones([3]), [2,3])

        G = self.G
        self._testOp(lambda x: x / G.ones(3), 3)
        self._testOp(lambda x: G.ones(3) / x, 3)
        self._testOp(lambda x: G.ones([4,2,3]) / x / G.ones([3]), [2,3])

        a = G.ones(())
        self._testOp(lambda x: x / a, 3)
        self._testOp(lambda x: a / x, 3)
        self._testOp(lambda x: (a / x) / x, 3)

    def testPow(self):
        self._testOp(lambda x: x ** x, 3)
        self._testOp(lambda x: 2 ** x, 3)
        self._testOp(lambda x: x ** 2, 3)
        self._testOp(lambda x: np.ones(3) ** x, 3)
        self._testOp(lambda x: x ** np.ones(3), 3)

    def testUnivariate(self):
        G = self.G
        def test01(x):
            x += G.log(x) + G.sin(x) * G.sum(x) - G.mean(x) + G.mean(x,0)
            x[0] = 1
            return x
        self._testOp(test01, 3)

    def testSumMean(self):
        self._testOp(lambda x: x.sum(), 3)
        self._testOp(lambda x: x.sum(), (3, 4))
        self._testOp(lambda x: x.sum(axis=0), (3, 4))
        self._testOp(lambda x: x.sum(axis=1), (3, 4))
        self._testOp(lambda x: x.sum(axis=[0,1]), (3, 4))
        self._testOp(lambda x: x.mean(), 3)
        self._testOp(lambda x: x.mean(), (3, 4))
        self._testOp(lambda x: x.mean(axis=0), (3, 4))
        self._testOp(lambda x: x.mean(axis=1), (3, 4))
        self._testOp(lambda x: x.mean(axis=[0,1]), (3, 4))

    def testReshapeReduce(self):
        G = self.G
        self._testOp(lambda x: x.reshape(12), (3, 4))
        self._testOp(lambda x: x + G.reduce_sum(x), (3, 4))
        self._testOp(lambda x: x.copy() - G.reduce_mean(x), (3, 4))


class _Indexing(_OpTest):
    def testGet(self):
        self._testOp(lambda x: x[2], (3,))
        self._testOp(lambda x: x[:], (3,))
        self._testOp(lambda x: x[:,0], (3, 4))
        self._testOp(lambda x: x[:,:2], (3, 4))
        self._testOp(lambda x: x[:-2,2:2:2], (3, 4))
        self._testOp(lambda x: x[:,np.newaxis] * x[np.newaxis,:], (4,))
        self._testOp(lambda x: x[np.newaxis,:-2,2:2:2], (3, 4))
        self._testOp(lambda x: x[:-2,np.newaxis,2:2:2], (3, 4))


class _Transforms(_OpTest):
    def testTranspose(self):
        self._testOp(lambda x: x.T, 2)
        self._testOp(lambda x: x.T, (2, 4))
        self._testOp(lambda x: x.T, (2, 3, 4))
        self._testOp(lambda x: x.transpose([2,0,1]), (2, 3, 4))

    def testRoll(self):
        self._testOp(lambda x: self.G.roll(x,1), (3, 4))
        self._testOp(lambda x: self.G.roll(x,-2), (3, 4))
        self._testOp(lambda x: self.G.roll(x,1,0), (3, 4))
        self._testOp(lambda x: self.G.roll(x,-2,1), (3, 4))

class _Misc(_OpTest):
    def testSizes(self):
        G = self.G
        x = G.zeros([3,4])
        self.assertEqual(x.size, 12)
        self.assertEqual(len(x), 3)

    def testRandom(self):
        x = self.G.random((10,2))
        self.assertEqual(x.shape, (10,2))

    def testPowerClass(self):
        class PowerClass(object):
            __array_priority__ = 10000000
            __add__ = lambda self, a: 1
            __rmul__ = lambda self, a: 2
            __truediv__ = lambda self, a: 3
            __rtruediv__ = lambda self, a: 4
            __pow__ = lambda self, a: 5
            __rpow__ = lambda self, a: 6

        a = PowerClass()
        b = self.G.ones(3)
        self.assertEqual(a + b, 1)
        self.assertEqual(b + a, 1)
        self.assertEqual(a - b, 1)
        self.assertEqual(a * b, 2)
        self.assertEqual(b * a, 2)
        self.assertEqual(a / b, 3)
        self.assertEqual(b / a, 4)
        self.assertEqual(a ** b, 5)
        self.assertEqual(b ** a, 6)

class _Adjoint(_OpTest):
    def testSimple(self):
        x = self.G.ones(3) * 2
        a = self.G.ones(3) * 5

        f = psc_compile(lambda x: x * x)
        g = f.adjoint(a, x)
        self.assertAlmostEqual(0, np.linalg.norm((g - a * x * 2)._data))

        f = psc_compile(lambda x: self.G.exp(x))
        g = f.adjoint(a, x)
        self.assertAlmostEqual(0, np.linalg.norm((g - a * self.G.exp(x))._data))


class _DoubleCompile(_OpTest):
    def testDC(self):
        f = psc_compile(lambda x: x * x)
        g = psc_compile(lambda x: f(x * x) ** 2)
        x = g(self.G.ones(3))
        self.assertEqual(x.shape, (3,))


class _SaveLoad(_OpTest):
    def testSL(self):
        x = self.G.ones(3)
        x.save('test')
        y = self.G.load('test.npy')
        self.assertAlmostEqual(self.G.reduce_sum((x - y)**2).sum(), 0)
        os.remove('test.npy')


class _Euler(_OpTest):
    def testTunnel(self):
        # ------------------------------------------------------------ #
        #                        PROBLEM SET UP                        #
        # ------------------------------------------------------------ #

        DISS_COEFF = 0.0025
        gamma, R = 1.4, 287.
        T0, p0, M0 = 300., 101325., 0.25

        rho0 = p0 / (R * T0)
        c0 = np.sqrt(gamma * R * T0)
        u0 = c0 * M0
        w0 = np.array([np.sqrt(rho0), np.sqrt(rho0) * u0, 0., p0])

        Lx, Ly = 40., 10.
        dx = dy = 0.05
        dt = dx / c0 * 0.5

        grid = grid2d(int(Lx / dx), int(Ly / dy))

        x = (grid.i + 0.5) * dx - 0.2 * Lx
        y = (grid.j + 0.5) * dy - 0.5 * Ly

        obstacle = grid.exp(-((x**2 + y**2) / 1)**64)

        fan = 2 * grid.cos((x / Lx + 0.2) * np.pi)**64

        nPrintsPerPlot, nStepPerPrint = 400, 5

        # ------------------------------------------------------------ #
        #                FINITE DIFFERENCE DISCRETIZATION              #
        # ------------------------------------------------------------ #

        def diffx(w):
            return (w.x_p - w.x_m) / (2 * dx)

        def diffy(w):
            return (w.y_p - w.y_m) / (2 * dy)

        def dissipation(r, u, dc):
            # conservative, negative definite dissipation applied to r*d(ru)/dt
            laplace = lambda u: (u.x_p + u.x_m + u.y_p + u.y_m) * 0.25 - u
            return laplace(dc * r * r * laplace(u))

        def rhs(w):
            r, ru, rv, p = w
            u, v = ru / r, rv / r

            mass = diffx(r * ru) + diffy(r * rv)
            momentum_x = (
                    (diffx(ru*ru) + (r*ru) * diffx(u)) / 2.0 +
                    (diffy(rv*ru) + (r*rv) * diffy(u)) / 2.0
                    ) + diffx(p)
            momentum_y = (
                    (diffx(ru*rv) + (r*ru) * diffx(v)) / 2.0 +
                    (diffy(rv*rv) + (r*rv) * diffy(v)) / 2.0
                    ) + diffy(p)
            energy = (
                    gamma * (diffx(p * u) + diffy(p * v)) -
                    (gamma - 1) * (u * diffx(p) + v * diffy(p))
                    )

            one = grid.ones(r.shape)
            dissipation_x = dissipation(r, u, DISS_COEFF) * c0 / dx
            dissipation_y = dissipation(r, v, DISS_COEFF) * c0 / dy
            dissipation_p = dissipation(one, p, DISS_COEFF) * c0 / dx

            momentum_x += dissipation_x
            momentum_y += dissipation_y
            energy += (
                    dissipation_p -
                    (gamma - 1) * (u * dissipation_x + v * dissipation_y)
                    )

            rhs_w = grid.zeros(w.shape)
            rhs_w[0] = 0.5 * mass / r
            rhs_w[1] = momentum_x / r
            rhs_w[2] = momentum_y / r
            rhs_w[-1] = energy

            rhs_w[1:3] += 0.1 * c0 * obstacle * w[1:3]
            rhs_w += 0.1 * c0 * (w - w0) * fan

            return rhs_w

        def step(w):
            dw0 = -dt * rhs(w)
            dw1 = -dt * rhs(w + 0.5 * dw0)
            dw2 = -dt * rhs(w + 0.5 * dw1)
            dw3 = -dt * rhs(w + dw2)
            return w + (dw0 + dw3) / 6 + (dw1 + dw2) / 3

        w0 = grid.ones(4)
        w1 = step(w0)
        w1_theano = psc_compile(step)(w0)
        self.assertAlmostEqual(0, np.abs((w1 - w1_theano)._data).sum())

################################################################################
################################################################################
################################################################################
