import os
import sys
import unittest
mj_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(mj_path, '..'))

from pascal.sa2d_decomp import *
from pascal.operators import infer_context
from pascal import sa2d_single_thread

# ============================================================================ #

class _TestMisc(unittest.TestCase):
    def testPrint(self):
        a = stencil_array()
        b = a * 2
        repr(a), repr(b)

    def testPowerClass(self):
        class PowerClass(object):
            shape = (1,)
            __array_priority__ = 10000000
            __add__ = lambda self, a: 1
            __rmul__ = lambda self, a: 2
            __truediv__ = lambda self, a: 3
            __rtruediv__ = lambda self, a: 4
            __pow__ = lambda self, a: 5
            __rpow__ = lambda self, a: 6
            __sub__ = lambda self, a: 7
            __rsub__ = lambda self, a: 8

        a = PowerClass()
        b = stencil_array()
        self.assertEqual(a + b, 1)
        self.assertEqual(b + a, 1)
        self.assertEqual(a - b, 7)
        self.assertEqual(b - a, 8)
        self.assertEqual(a * b, 2)
        self.assertEqual(b * a, 2)
        self.assertEqual(a / b, 3)
        self.assertEqual(b / a, 4)
        self.assertEqual(a ** b, 5)
        self.assertEqual(b ** a, 6)

# ============================================================================ #

class _TestSimpleUpdates(unittest.TestCase):
    def test1(self):
        def update(u):
            return u.ndim + 2**u

        Ni, Nj = 4, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        stages = decompose_function(update, stencil_array())

        self.assertEqual(len(stages), 1)
        stage0 = stages[0]

        u0 = G.i
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - update(u0)
        self.assertAlmostEqual(0, G.reduce_sum(err**2))

    def test2(self):
        def update(u):
            return u.size - 1 / (-u)**3 * 2

        Ni, Nj = 4, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        stages = decompose_function(update, stencil_array((2,)))

        self.assertEqual(len(stages), 1)
        stage0 = stages[0]

        u0 = G.i + G.ones(2)
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - update(u0)
        self.assertAlmostEqual(0, G.reduce_sum((err**2).sum()))

    def testExpCopySumMean(self):
        def update(u):
            return G.exp(u).copy().sum(0).mean()

        G = sys.modules[__name__]
        stages = decompose_function(update, stencil_array((2,3)))

        self.assertEqual(len(stages), 1)
        stage0 = stages[0]

        Ni, Nj = 4, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        u0 = G.i + G.ones((2,3)) + np.arange(3)
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - update(u0)
        self.assertAlmostEqual(0, G.reduce_sum((err**2).sum()))

    def testTransposeReshapeRoll(self):
        def update(u):
            return G.roll(u.transpose([1,0,2]).reshape([3,-1]).T, 1)

        G = sys.modules[__name__]
        stages = decompose_function(update, stencil_array((2,3,4)))

        self.assertEqual(len(stages), 1)
        stage0 = stages[0]

        Ni, Nj = 4, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        u0 = G.i + G.ones((2,3,4)) + np.arange(4)
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - update(u0)
        self.assertAlmostEqual(0, G.reduce_sum((err**2).sum()))

    def testSetGetItem(self):
        def update(u):
            v = G.zeros([3,2])
            v[0] = G.ones(2)
            v[1,0] = u[0]
            v[2] = u.i_p + u.i_m - 2 * u
            return v

        G = sys.modules[__name__]
        stages = decompose_function(update, np.zeros(2))

        self.assertEqual(len(stages), 1)
        stage0 = stages[0]

        self.assertEqual(stage0.triburary_values, [builtin_values.ZERO])

        Ni, Nj = 4, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        u0 = G.i + np.arange(2) * 8

        result = stage0((u0,), (G.zeros(),))
        self.assertEqual(len(result), 1)
        result = result[0]

        err = result - update(u0)
        self.assertAlmostEqual(0, G.reduce_sum((err**2).sum()))

# ============================================================================ #

class _TestSingleStage(unittest.TestCase):
    def testHeat(self):
        def heat(u):
            dx, dt = 0.1, 0.01
            return u + dt * (u.i_m + u.i_p + u.j_m + u.j_p - 4 * u) / dx**2

        G = sys.modules[__name__]
        heatStages = decompose_function(heat, stencil_array())

        self.assertEqual(len(heatStages), 1)
        stage0 = heatStages[0]

        Ni, Nj = 16, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        u0 = G.ones(())
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - 1
        self.assertAlmostEqual(0, G.reduce_sum(err**2))

        u0 = G.sin(G.i / Ni * np.pi * 2)
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - heat(u0)
        self.assertAlmostEqual(0, G.reduce_sum(err**2))

        u0 = G.sin(G.j / Nj * np.pi * 4)
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - heat(u0)
        self.assertAlmostEqual(0, G.reduce_sum(err**2))

    def testODE1(self):
        def ode(u):
            dt = 0.1
            return u - dt * G.sin(u)

        G = sys.modules[__name__]
        odeStages = decompose_function(ode, stencil_array())

        self.assertEqual(len(odeStages), 1)
        stage0 = odeStages[0]

        Ni, Nj = 4, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        u0 = G.i
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - ode(u0)
        self.assertAlmostEqual(0, G.reduce_sum(err**2))

    def testODE2(self):
        def ode(u):
            dt = 0.1
            return u - dt * G.cos(u) / len(u)

        G = sys.modules[__name__]
        odeStages = decompose_function(ode, stencil_array())

        self.assertEqual(len(odeStages), 1)
        stage0 = odeStages[0]

        Ni, Nj = 4, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        u0 = G.i
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - ode(u0)
        self.assertAlmostEqual(0, G.reduce_sum(err**2))


# ============================================================================ #

class _TestMultiStage(unittest.TestCase):
    def testHeat(self):
        def heatMidpoint(u):
            dx, dt = 0.1, 0.01
            uh = u + 0.5 * dt * (u.i_m + u.i_p + u.j_m + u.j_p - 4 * u) / dx**2
            return u + dt * (uh.i_m + uh.i_p + uh.j_m + uh.j_p - 4 * uh) / dx**2

        G = sys.modules[__name__]
        heatStages = decompose_function(heatMidpoint, stencil_array(),
                                        verbose='visualize')

        self.assertEqual(len(heatStages), 2)
        stage0, stage1 = heatStages

        Ni, Nj = 16, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        u0 = G.sin(G.i / Ni * np.pi * 2)

        result = stage1(stage0([u0], [G.zeros()]))
        self.assertEqual(len(result), 1)
        result = result[0]

        err = result - heatMidpoint(u0)
        self.assertAlmostEqual(G.reduce_sum(err**2), 0)

    def testKuramotoSivashinskyRk4(self):
        def ks_dudt(u):
            dx = 0.1
            lu = (u.i_m + u.i_p + u.j_m + u.j_p - 4 * u) / dx**2
            llu = (lu.i_m + lu.i_p + lu.j_m + lu.j_p - 4 * u) / dx**2
            ux = (u.i_m - u.i_p) / dx
            return -llu - lu - ux * u

        def ks_rk4(u0):
            dt = 0.0001
            du0 = dt * ks_dudt(u0)
            du1 = dt * ks_dudt(u0 + 0.5 * du0)
            du2 = dt * ks_dudt(u0 + 0.5 * du1)
            du3 = dt * ks_dudt(u0 + du2)
            return u0 + (du0 + 2 * du1 + 2 * du2 + du3) / 6.

        ks_stages = decompose_function(ks_rk4, stencil_array())

        self.assertEqual(len(ks_stages), 8)

        Ni, Nj = 16, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        u0 = G.sin(G.i * np.pi / Ni * 2)
        inp = (u0,)
        for i in range(8):
            if ks_stages[i].triburary_values:
                inp = ks_stages[i](inp, [G.zeros()])
            else:
                inp = ks_stages[i](inp)
        result, = inp
        err = result - ks_rk4(u0)
        self.assertAlmostEqual(G.reduce_sum(err**2), 0)

# ============================================================================ #

class _TestEuler(unittest.TestCase):
    def testTunnelRk4(self):

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

        Ni, Nj = 16, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)

        x = (builtin.I + 0.5) * dx - 0.2 * Lx
        y = (builtin.J + 0.5) * dy - 0.5 * Ly

        obstacle = exp(-((x**2 + y**2) / 1)**64)
        fan = 2 * cos((x / Lx + 0.2) * np.pi)**64

        def diffx(w):
            return (w.i_p - w.i_m) / (2 * dx)

        def diffy(w):
            return (w.j_p - w.j_m) / (2 * dy)

        def dissipation(r, u, dc):
            # conservative, negative definite dissipation applied to r*d(ru)/dt
            laplace = lambda u: (u.i_p + u.i_m + u.j_p + u.j_m) * 0.25 - u
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

            one = infer_context(w).ones(r.shape)
            dissipation_x = dissipation(r, u, DISS_COEFF) * c0 / dx
            dissipation_y = dissipation(r, v, DISS_COEFF) * c0 / dy
            dissipation_p = dissipation(one, p, DISS_COEFF) * c0 / dx

            momentum_x += dissipation_x
            momentum_y += dissipation_y
            energy += dissipation_p \
                    - (gamma - 1) * (u * dissipation_x + v * dissipation_y)

            rhs_w = infer_context(w).zeros(w.shape)
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

        stages = decompose_function(step, stencil_array((4,)))
        self.assertEqual(len(stages), 8)

        w0 = G.zeros(4) + np.array([np.sqrt(rho0), np.sqrt(rho0) * u0, 0., p0])
        inp = (w0,)
        z = G.zeros(())
        triburary_values = {builtin_values.I: G.i,
                            builtin_values.J: G.j,
                            builtin_values.ZERO: G.zeros()}
        for stage in stages:
            inp = stage(inp, triburary_values)
        result, = inp

        x = (G.i + 0.5) * dx - 0.2 * Lx
        y = (G.j + 0.5) * dy - 0.5 * Ly

        obstacle = G.exp(-((x**2 + y**2) / 1)**64)
        fan = 2 * G.cos((x / Lx + 0.2) * np.pi)**64

        err = result - step(w0)
        self.assertAlmostEqual(G.reduce_sum(err**2).sum(), 0)

################################################################################
################################################################################
################################################################################
