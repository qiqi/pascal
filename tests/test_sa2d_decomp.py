import os
import sys
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..'))

from pascal.sa2d_decomp import *
from pascal import sa2d_single_thread
from pascal import sa2d_theano

# ============================================================================ #

class _TestMisc(unittest.TestCase):
    def testPrint(self):
        a = stencil_array()
        b = a * 2
        print(a, b)

    def testPowerClass(self):
        class PowerClass(object):
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
            v[2] = u.x_p + u.x_m - 2 * u
            return v

        G = sys.modules[__name__]
        stages = decompose_function(update, [0,0])

        self.assertEqual(len(stages), 1)
        stage0 = stages[0]

        self.assertEqual(stage0.triburary_values, [G_ZERO])

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
            return u + dt * (u.x_m + u.x_p + u.y_m + u.y_p - 4 * u) / dx**2

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
            uh = u + 0.5 * dt * (u.x_m + u.x_p + u.y_m + u.y_p - 4 * u) / dx**2
            return u + dt * (uh.x_m + uh.x_p + uh.y_m + uh.y_p - 4 * uh) / dx**2

        G = sys.modules[__name__]
        heatStages = decompose_function(heatMidpoint, stencil_array())

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
            lu = (u.x_m + u.x_p + u.y_m + u.y_p - 4 * u) / dx**2
            llu = (lu.x_m + lu.x_p + lu.y_m + lu.y_p - 4 * u) / dx**2
            ux = (u.x_m - u.x_p) / dx
            return -llu - lu - ux * u

        def ks_rk4(u0):
            dt = 0.01
            du0 = dt * ks_dudt(u0)
            du1 = dt * ks_dudt(u0 + 0.5 * du0)
            du2 = dt * ks_dudt(u0 + 0.5 * du1)
            du3 = dt * ks_dudt(u0 + du2)
            return u0 + (du0 + 2 * du1 + 2 * du2 + du3) / 6

        ks_stages = decompose_function(ks_rk4, stencil_array())

        self.assertEqual(len(ks_stages), 8)

        Ni, Nj = 16, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        u0 = G.sin(G.i / Ni * np.pi * 2)
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

def ij_np(i0, i1, j0, j1):
    return np.outer(np.arange(i0, i1), np.ones(j1 - j0, int)), \
           np.outer(np.ones(i1 - i0, int), np.arange(j0, j1))

def compile_stage(stage, upstream_arrays, triburary_arrays,
                  unstack_input, stack_output):
    theano_inputs = [a.value for a in upstream_arrays + triburary_arrays]
    downstream_arrays = stage(upstream_arrays, triburary_arrays)
    theano_outputs = [a.value for a in downstream_arrays]
    print([a.shape for a in downstream_arrays])
    return sa2d_theano.compile(theano_inputs, theano_outputs)

def update_nbr(no_nbr):
    assert no_nbr.ndim == 3
    Ni, Nj = no_nbr.shape[:2]
    new_nbr = np.zeros((Ni+2, Nj+2, no_nbr.shape[2]))
    new_nbr[1:-1,1:-1] = no_nbr
    new_nbr[0,1:-1] = no_nbr[-1,:]
    new_nbr[-1,1:-1] = no_nbr[0,:]
    new_nbr[1:-1,0] = no_nbr[:,-1]
    new_nbr[1:-1,-1] = no_nbr[:,0]
    return new_nbr

def run_stages(stages, u0, triburary_numpy_dict):
    upstream_numpy_values = [u0]
    triburary_sa_dict = dict((key, sa2d_theano.numpy_to_sa(val))
                          for key, val in triburary_numpy_dict.items())
    for k, stage in enumerate(stages):
        print('Compiling and running atomic stage {0}'.format(k))
        upstream_arrays = list(map(sa2d_theano.numpy_to_sa,
                                   upstream_numpy_values))
        triburary_arrays = [triburary_sa_dict[s]
                            for s in stage.triburary_values]
        theano_function = compile_stage(
                stage, upstream_arrays, triburary_arrays,
                k > 0, k < len(stages)-1)

        triburary_numpy_values = [triburary_numpy_dict[s]
                               for s in stage.triburary_values]
        numpy_inputs = tuple(upstream_numpy_values + triburary_numpy_values)
        downstream_numpy_values = theano_function(*numpy_inputs)
        if k == len(stages) - 1:
            return downstream_numpy_values
        upstream_numpy_values = list(downstream_numpy_values)
        upstream_numpy_values[0] = update_nbr(downstream_numpy_values[0])


# ---------------------------------------------------------------------------- #

class _TestTheano(unittest.TestCase):
    def testHeat(self):
        f = stencil_array()

        def heat(u):
            dx = 0.1
            return (u.x_m + u.x_p + u.y_m + u.y_p - 4 * u) / dx**2 + f

        def heatMidpoint(u):
            dt = 0.01
            return u + dt * heat(u)

        heatStages = decompose_function(heatMidpoint, stencil_array())

        Ni, Nj = 8, 8
        i, j = ij_np(-1, Ni+1, -1, Nj+1)
        u0 = np.sin(i / Ni * np.pi * 2)
        f0 = u0 * 0

        u1, = run_stages(heatStages, u0, {f.value: f0})

        dudt = 2 * (1 - np.cos(np.pi * 2 / Ni))
        err = u1 - u0[1:-1,1:-1] * (1 - dudt)

        self.assertAlmostEqual(0, np.abs(err).max())

    def testHeatTwoStage(self):
        f = stencil_array()

        def heat(u):
            dx = 0.1
            return (u.x_m + u.x_p + u.y_m + u.y_p - 4 * u) / dx**2 + f

        def heatMidpoint(u):
            dt = 0.01
            uh = u + 0.5 * dt * heat(u)
            return u + dt * heat(uh)

        heatStages = decompose_function(heatMidpoint, stencil_array())

        Ni, Nj = 8, 8
        i, j = ij_np(-1, Ni+1, -1, Nj+1)
        u0 = np.sin(i / Ni * np.pi * 2)
        f0 = u0 * 0

        u1, = run_stages(heatStages, u0, {f.value: f0, G_ZERO: f0})

        dudt = 2 * (1 - np.cos(np.pi * 2 / Ni))
        err = u1 - u0[1:-1,1:-1] * (1 - dudt + dudt**2 / 2)

        self.assertAlmostEqual(0, np.abs(err).max())

    def testKuramotoSivashinskyRk4(self):
        f = stencil_array()

        def ks_dudt(u):
            dx = 0.1
            lu = (u.x_m + u.x_p + u.y_m + u.y_p - 4 * u) / dx**2
            llu = (lu.x_m + lu.x_p + lu.y_m + lu.y_p - 4 * u) / dx**2
            ux = (u.x_m - u.x_p) / dx
            return -llu - lu - ux * u + f

        def ks_rk4(u0):
            dt = 0.01
            du0 = dt * ks_dudt(u0)
            du1 = dt * ks_dudt(u0 + 0.5 * du0)
            du2 = dt * ks_dudt(u0 + 0.5 * du1)
            du3 = dt * ks_dudt(u0 + du2)
            return u0 + (du0 + 2 * du1 + 2 * du2 + du3) / 6

        ksStages = decompose_function(ks_rk4, stencil_array())

        Ni, Nj = 8, 8
        i, j = ij_np(-1, Ni+1, -1, Nj+1)
        u0 = np.sin(i / Ni * np.pi * 2)
        f0 = u0 * 0

        u1, = run_stages(ksStages, u0, {f.value: f0, G_ZERO: f0})


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

        x = (G.i + 0.5) * dx - 0.2 * Lx
        y = (G.j + 0.5) * dy - 0.5 * Ly

        obstacle = G.exp(-((x**2 + y**2) / 1)**64)
        fan = 2 * G.cos((x / Lx + 0.2) * np.pi)**64

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
        for stage in stages:
            if stage.triburary_values:
                inp = stage(inp, [z])
            else:
                inp = stage(inp)
            if len(inp) > 1:
                assert len(inp) == 2
                n0, n1 = outp[0].size, outp[1].size
                inp = zeros(n0 + n1)
                inp[:n0] = outp[0]
                inp[n0:] = outp[1]
                inp = [inp]

        result, = inp
        err = result - step(w0)
        self.assertAlmostEqual(G.reduce_sum(err**2).sum(), 0)

    def testTunnelRk4Theano(self):

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

        Ni, Nj = 8, 8

        i, j = stencil_array(), stencil_array()
        x = (i + 0.5) * dx - 0.2 * Lx
        y = (j + 0.5) * dy - 0.5 * Ly

        obstacle = exp(-((x**2 + y**2) / 1)**64)
        fan = 2 * cos((x / Lx + 0.2) * np.pi)**64

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
            momentum_x = (diffx(ru*ru) + (r*ru) * diffx(u)) / 2.0 \
                       + (diffy(rv*ru) + (r*rv) * diffy(u)) / 2.0 \
                       + diffx(p)
            momentum_y = (diffx(ru*rv) + (r*ru) * diffx(v)) / 2.0 \
                       + (diffy(rv*rv) + (r*rv) * diffy(v)) / 2.0 \
                       + diffy(p)
            energy = gamma * (diffx(p * u) + diffy(p * v)) \
                   - (gamma - 1) * (u * diffx(p) + v * diffy(p))

            one = ones(r.shape)
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

        w0 = np.zeros([Ni+2, Nj+2, 4]) + \
             np.array([np.sqrt(rho0), np.sqrt(rho0) * u0, 0., p0])
        z = np.zeros([Ni+2, Nj+2])
        i0, j0 = np.zeros([2, Ni+2, Nj+2])

        u1, = run_stages(stages, w0, {G_ZERO: z, i.value: i0, j.value: j0})
        self.assertEqual(u1.shape, (Ni, Nj, 4))


################################################################################
################################################################################
################################################################################
