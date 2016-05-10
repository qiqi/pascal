import os
import sys
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..', '..'))

import numpy as np
import enzyme

def test_heat_midpoint():
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

    x = (enzyme.builtin.I + 0.5) * dx - 0.2 * Lx
    y = (enzyme.builtin.J + 0.5) * dy - 0.5 * Ly

    obstacle = enzyme.exp(-((x**2 + y**2) / 1)**64)
    fan = 2 * enzyme.cos((x / Lx + 0.2) * np.pi)**64

    im, ip = enzyme.im, enzyme.ip
    jm, jp = enzyme.jm, enzyme.jp
    km, kp = enzyme.km, enzyme.kp
    ones, zeros = enzyme.ones, enzyme.zeros

    def diffx(w):
        return (ip(w) - im(w)) / (2 * dx)

    def diffy(w):
        return (jp(w) - jm(w)) / (2 * dy)

    def dissipation(r, u, dc):
        # conservative, negative definite dissipation applied to r*d(ru)/dt
        laplace = lambda u: (ip(u) + im(u) + jp(u) + jm(u)) * 0.25 - u
        return laplace(dc * r * r * laplace(u))

    def assenble_rhs(mass, momentum_x, momentum_y, energy, w):
        rhs_w = zeros(w.shape)
        rhs_w[0] = mass
        rhs_w[1] = momentum_x
        rhs_w[2] = momentum_y
        rhs_w[-1] = energy

        rhs_w[1:3] += 0.1 * c0 * obstacle * w[1:3]
        rhs_w += 0.1 * c0 * (w - w0) * fan
        return rhs_w

    def distribute_w(w):
        return w

    def rhs(w):
        r, ru, rv, p = distribute_w(w)
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

        return assenble_rhs(0.5 * mass / r,
                            momentum_x / r,
                            momentum_y / r, energy, w)

    def step(w):
        dw0 = -dt * rhs(w)
        dw1 = -dt * rhs(w + 0.5 * dw0)
        dw2 = -dt * rhs(w + 0.5 * dw1)
        dw3 = -dt * rhs(w + dw2)
        return w + (dw0 + dw3) / 6 + (dw1 + dw2) / 3

    Ni, Nj, Nk = 8, 4, 3
    u0 = np.random.random([Ni, Nj, Nk, 4])
    stages = enzyme.decompose(step, enzyme.stencil_array(4))
    u1 = enzyme.execute(stages, u0)

    I, J, K = np.meshgrid(range(Ni), range(Nj), range(Nk), indexing='ij')
    x = (I + 0.5) * dx - 0.2 * Lx
    y = (J + 0.5) * dy - 0.5 * Ly

    obstacle = np.exp(-((x**2 + y**2) / 1)**64)
    fan = 2 * np.cos((x / Lx + 0.2) * np.pi)**64

    im, ip = lambda u : np.roll(u,1,0), lambda u : np.roll(u,-1,0)
    jm, jp = lambda u : np.roll(u,1,1), lambda u : np.roll(u,-1,1)
    km, kp = lambda u : np.roll(u,1,2), lambda u : np.roll(u,-1,2)
    ones, zeros = np.ones, np.zeros

    def assenble_rhs(mass, momentum_x, momentum_y, energy, w):
        rhs_w = zeros(w.shape)
        rhs_w[:,:,:,0] = mass
        rhs_w[:,:,:,1] = momentum_x
        rhs_w[:,:,:,2] = momentum_y
        rhs_w[:,:,:,-1] = energy

        rhs_w[:,:,:,1] += 0.1 * c0 * obstacle * w[:,:,:,1]
        rhs_w[:,:,:,2] += 0.1 * c0 * obstacle * w[:,:,:,2]
        rhs_w += 0.1 * c0 * (w - w0) * fan[:,:,:,np.newaxis]
        return rhs_w

    def distribute_w(w):
        return np.rollaxis(w, 3)

    u2 = step(u0)
    assert abs(u1 - u2).max() < 1E-6
