import os
import sys
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..'))

from pascal.sa2d_classic import *

def test_heat_midpoint():
    G = grid2d(128, 64, 2)
    f = G.zeros()
    u0 = G.ones() + G.sin(G.i * np.pi / G.nx * 2)

    def heat(u):
        dx = 0.1
        return (u.x_m + u.x_p + u.y_m + u.y_p - 4 * u) / dx**2 + f

    def heatMidpoint(u):
        dt = 0.01
        uh = u + 0.5 * dt * heat(u)
        return u + dt * heat(uh)

    s = Stages(heatMidpoint, u0)
    t0 = time.time()
    n = 100
    for i in range(n):
        u0 = s(u0)
    usum = G.reduce_sum(u0)

    u0 = G.ones() + G.sin(G.i * np.pi / G.nx * 2)
    for i in range(n):
        u0 = heatMidpoint(u0)
    usum1 = G.reduce_sum(u0)
    assert abs(usum - usum1).max() < 1E-12


def test_euler_tunnel():
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

    Ni, Nj = 128, 64
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

    G = grid2d(Ni, Nj, 2)

    x = (G.i + 0.5) * dx - 0.2 * Lx
    y = (G.j + 0.5) * dy - 0.5 * Ly

    obstacle = G.exp(-((x**2 + y**2) / 1)**64)
    fan = 2 * G.cos((x / Lx + 0.2) * np.pi)**64

    n = 1

    w = G.zeros() + w0
    s = Stages(step, w)
    for i in range(n):
        w = s(w)
    # wsum = G.reduce_sum(w)

    # w = G.zeros() + w0
    # for i in range(n):
    #     w = step(w)
    # wsum1 = G.reduce_sum(w)
    # assert abs(wsum - wsum1).max() < 1E-12

# test_euler_tunnel()
