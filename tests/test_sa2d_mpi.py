import gc
import os
import sys
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..'))

from pascal.sa2d_mpi import *
from pascal import sa2d_single_thread
from pascal import sa2d_decomp

# ============================================================================ #

class TestGridLife(unittest.TestCase):
    def testDelete(self):
        G = grid2d(16, 8, 2)
        del G

    def testGarbageCollection(self):
        G = grid2d(16, 8, 2)
        a = G.ones(3)
        b = G.ones((1,3))
        c = a + b
        del a, b, c, G
        gc.collect()

# ---------------------------------------------------------------------------- #

class TestOperation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.G = grid2d(32, 16, 2)

    @classmethod
    def tearDownClass(cls):
        cls.G.delete()

    def testLogMean(self):
        a = self.G.ones()
        b = self.G.log(a)
        b2_sum = self.G.reduce_sum((b ** 2))
        self.assertAlmostEqual(b2_sum, 0)

    def testSinSum(self):
        a = np.pi + self.G.zeros()
        b = self.G.sin(a)
        b2_sum = self.G.reduce_sum((b ** 2))
        self.assertAlmostEqual(b2_sum, 0)

    def testTransposeCopy(self):
        a = 1 - self.G.zeros([2,3,4])
        b = a.T
        self.assertEqual(len(b), 4)
        self.assertEqual(b.size, 24)
        self.assertAlmostEqual(self.G.reduce_mean(b.sum(2).mean()), 2)
        self.assertAlmostEqual(self.G.reduce_mean(b.sum([1,2]).mean()), 6)
        c = a.copy().transpose([0,2,1])
        self.assertEqual(len(c), 2)
        self.assertEqual(c.size, 24)
        self.assertAlmostEqual(self.G.reduce_mean(c.mean(2).sum()), 8)
        self.assertAlmostEqual(self.G.reduce_mean(c.mean([1,2]).sum()), 2)

    def testRoll(self):
        a = self.G.zeros([2,1]) + np.arange(3) + 3 * np.arange(2)[:,np.newaxis]
        b = self.G.roll(a, 1).reshape(6)
        self.assertEqual(self.G.reduce_mean(b[0]), 5)
        self.assertEqual(self.G.reduce_mean(b[1]), 0)
        c = self.G.roll(a, 1, axis=1)
        self.assertEqual(self.G.reduce_mean(c[0,0]), 2)
        self.assertEqual(self.G.reduce_mean(c[0,1]), 0)
        self.assertEqual(self.G.reduce_mean(c[1,0]), 5)
        self.assertEqual(self.G.reduce_mean(c[1,1]), 3)

# ---------------------------------------------------------------------------- #

class TestReduction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.G = grid2d(32, 16, 2)

    @classmethod
    def tearDownClass(cls):
        cls.G.delete()

    def testReduceSum(self):
        a = 1 / self.G.ones()
        a_sum = self.G.reduce_sum(a)
        self.assertEqual(a_sum, 32 * 16)

    def testReduceMean(self):
        a = self.G.ones()
        a_mean = self.G.reduce_mean(a)
        self.assertEqual(a_mean, 1)

    def testPrint(self):
        a = 10 ** self.G.ones()
        self.assertTrue(isinstance(repr(a), str))

    def testSaveLoad(self):
        a = self.G.ones()
        a.save('_tmp.npy')
        b = self.G.load('_tmp.npy')
        os.unlink('_tmp.npy')
        self.assertEqual(self.G.reduce_sum((a - b)**2), 0)

# ---------------------------------------------------------------------------- #

class InteractWithDecomp(unittest.TestCase):
    def testOp(self):
        b = sa2d_decomp.stencil_array()
        with grid2d(8,4,2) as G:
            a = G.ones()
            c = a + b
            self.assertTrue(isinstance(c, sa2d_decomp.stencil_array))
            c = a - b
            self.assertTrue(isinstance(c, sa2d_decomp.stencil_array))
            c = a * b
            self.assertTrue(isinstance(c, sa2d_decomp.stencil_array))
            c = a / b
            self.assertTrue(isinstance(c, sa2d_decomp.stencil_array))
            c = a ** b
            self.assertTrue(isinstance(c, sa2d_decomp.stencil_array))
            c = b / a
            self.assertTrue(isinstance(c, sa2d_decomp.stencil_array))
            c = b ** a
            self.assertTrue(isinstance(c, sa2d_decomp.stencil_array))


# ---------------------------------------------------------------------------- #

class CompareSerialMPI(unittest.TestCase):
    def testEuler(self):
        DISS_COEFF = 0.0025
        gamma, R = 1.4, 287.
        T0, p0, M0 = 300., 101325., 0.25

        rho0 = p0 / (R * T0)
        c0 = np.sqrt(gamma * R * T0)
        u0 = c0 * M0
        w0 = np.array([np.sqrt(rho0), np.sqrt(rho0) * u0, 0., p0])

        Lx, Ly = 40., 10.
        dx = dy = 0.25
        dt = dx / c0 * 0.5

        def EulerSteps(grid):
            # ------------------------------------------------------------ #
            #                        PROBLEM SET UP                        #
            # ------------------------------------------------------------ #

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
                # conservative, negative definite dissipation
                # applied to r*d(ru)/dt
                laplace = lambda u: (u.x_p + u.x_m + u.y_p + u.y_m) * 0.25 - u
                return laplace(dc * r * r * laplace(u))

            def rhs(w):
                r, ru, rv, p = w
                u, v = ru / r, rv / r

                mass = diffx(r * ru) + diffy(r * rv)
                momentum_x = (diffx(ru*ru) + (r*ru) * diffx(u)) / 2.0 \
                           + (diffy(rv*ru) + (r*rv) * diffy(u)) / 2.0 \
                           + diffx(p)
                momentum_y = (diffx(ru*rv) + (r*ru) * diffx(v)) / 2.0 \
                           + (diffy(rv*rv) + (r*rv) * diffy(v)) / 2.0 \
                           + diffy(p)
                energy = gamma * (diffx(p * u) + diffy(p * v)) \
                       - (gamma - 1) * (u * diffx(p) + v * diffy(p))

                one = grid.ones(r.shape)
                dissipation_x = dissipation(r, u, DISS_COEFF) * c0 / dx
                dissipation_y = dissipation(r, v, DISS_COEFF) * c0 / dy
                dissipation_p = dissipation(one, p, DISS_COEFF) * c0 / dx

                momentum_x += dissipation_x
                momentum_y += dissipation_y
                energy += dissipation_p \
                        - (gamma - 1) * (u * dissipation_x + v * dissipation_y)

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

            w0 = grid.zeros()
            w0 += np.array([np.sqrt(rho0), np.sqrt(rho0) * u0, 0., p0])
            w1 = step(w0)
            return w1

        with grid2d(int(Lx / dx), int(Ly / dy), 3) as grid:
            w1 = EulerSteps(grid)
            w1_mpi = grid.gather_all_data(w1)

        grid_serial = sa2d_single_thread.grid2d(int(Lx / dx), int(Ly / dy))
        w1 = EulerSteps(grid_serial)
        w1_serial = w1._data

        self.assertAlmostEqual(np.abs(w1_mpi - w1_serial).max(), 0)

################################################################################
################################################################################
################################################################################
