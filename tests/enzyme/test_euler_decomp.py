import os
import sys
import subprocess
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..', '..'))

# vis_bin = os.path.join(my_path, '../../bin/quarkflowvis')
# graph_outfile = os.path.join(my_path, 'euler_rk4.comp_graph')
# dot_outfile = os.path.join(my_path, 'euler_rk4.dot')

import numpy as np
import enzyme

def test_euler_rk4():
    DISS_COEFF = 0.0025
    gamma, R = 1.4, 287.
    T0, p0, M0 = 300., 101325., 0.25

    rho0 = p0 / (R * T0)
    c0 = np.sqrt(gamma * R * T0)
    u0 = c0 * M0
    W0 = np.array([np.sqrt(rho0), np.sqrt(rho0) * u0, 0., 0., p0])

    Lx, Ly, Lz = 40., 10., 5.
    dx = dy = dz = 0.05
    dt = dx / c0 * 0.5

    Ni, Nj, Nk = 8, 4, 2

    x = (enzyme.builtin.I + 0.5) * dx - 0.2 * Lx
    y = (enzyme.builtin.J + 0.5) * dy - 0.5 * Ly
    z = (enzyme.builtin.K + 0.5) * dz - 0.5 * Lz

    obstacle = enzyme.exp(-((x**2 + y**2 + z**2) / 1)**64)
    fan = 2 * (enzyme.cos((x / Lx + 0.2) * np.pi)**64 +
               enzyme.sin((y / Ly) * np.pi)**64)

    im, ip = enzyme.im, enzyme.ip
    jm, jp = enzyme.jm, enzyme.jp
    km, kp = enzyme.km, enzyme.kp
    ones, zeros = enzyme.ones, enzyme.zeros

    def diffx(w):
        return (ip(w) - im(w)) / (2 * dx)

    def diffy(w):
        return (jp(w) - jm(w)) / (2 * dy)

    def diffz(w):
        return (kp(w) - km(w)) / (2 * dz)

    def dissipation(r, u, dc):
        # conservative, negative definite dissipation applied to r*d(ru)/dt
        laplace = lambda u: (ip(u) + im(u) +
                             jp(u) + jm(u) +
                             jp(u) + jm(u)) / 6. - u
        return laplace(dc * r * r * laplace(u))

    def assemble_rhs(mass, momentum_x, momentum_y, momentum_z, energy, w):
        rhs_w = zeros(w.shape)
        rhs_w[0] = mass
        rhs_w[1] = momentum_x
        rhs_w[2] = momentum_y
        rhs_w[3] = momentum_z
        rhs_w[-1] = energy

        rhs_w[1:3] += 0.1 * c0 * obstacle * w[1:3]
        rhs_w += 0.1 * c0 * (w - W0) * fan
        return rhs_w

    def distribute_w(w):
        return w

    def rhs(w):
        r, rux, ruy, ruz, p = distribute_w(w)
        ux, uy, uz = rux / r, ruy / r, ruz / r

        mass = diffx(r * rux) + diffy(r * ruy) + diffz(r * ruz)
        momentum_x = (diffx(rux*rux) + (r*rux) * diffx(ux)) / 2.0 \
                   + (diffy(ruy*rux) + (r*ruy) * diffy(ux)) / 2.0 \
                   + (diffy(ruz*rux) + (r*ruz) * diffz(ux)) / 2.0 \
                   + diffx(p)
        momentum_y = (diffx(rux*ruy) + (r*rux) * diffx(uy)) / 2.0 \
                   + (diffy(ruy*ruy) + (r*ruy) * diffy(uy)) / 2.0 \
                   + (diffy(ruz*ruy) + (r*ruz) * diffz(uy)) / 2.0 \
                   + diffy(p)
        momentum_z = (diffx(rux*ruz) + (r*rux) * diffx(uz)) / 2.0 \
                   + (diffy(ruy*ruz) + (r*ruy) * diffy(uz)) / 2.0 \
                   + (diffy(ruz*ruz) + (r*ruz) * diffz(uz)) / 2.0 \
                   + diffz(p)
        energy = gamma * (diffx(p * ux) + diffy(p * uy) + diffz(p * uz)) \
               - (gamma - 1) * (ux * diffx(p) + uy * diffy(p) + uz * diffz(p))

        one = ones(r.shape)
        dissipation_x = dissipation(r, ux, DISS_COEFF) * c0 / dx
        dissipation_y = dissipation(r, uy, DISS_COEFF) * c0 / dy
        dissipation_z = dissipation(r, uz, DISS_COEFF) * c0 / dz
        dissipation_p = dissipation(one, p, DISS_COEFF) * c0 / dx

        momentum_x += dissipation_x
        momentum_y += dissipation_y
        momentum_z += dissipation_z
        energy += dissipation_p \
                - (gamma - 1) * (ux * dissipation_x +
                                 uy * dissipation_y +
                                 uz * dissipation_z)

        return assemble_rhs(0.5 * mass / r,
                            momentum_x / r,
                            momentum_y / r,
                            momentum_z / r, energy, w)

    def step(w):
        dw0 = -dt * rhs(w)
        dw1 = -dt * rhs(w + 0.5 * dw0)
        dw2 = -dt * rhs(w + 0.5 * dw1)
        dw3 = -dt * rhs(w + dw2)
        return w + (dw0 + dw3) / 6 + (dw1 + dw2) / 3

    w0 = np.random.random([Ni, Nj, Nk, 5])
    stages = enzyme.decompose(step, enzyme.stencil_array(5),
                              comp_graph_output_file=None)
    w1 = enzyme.execute(stages, w0)

    I, J, K = np.meshgrid(range(Ni), range(Nj), range(Nk), indexing='ij')
    x = (I + 0.5) * dx - 0.2 * Lx
    y = (J + 0.5) * dy - 0.5 * Ly

    obstacle = np.exp(-((x**2 + y**2) / 1)**64)
    fan = 2 * (np.cos((x / Lx + 0.2) * np.pi)**64 +
               np.sin((y / Ly) * np.pi)**64)

    im, ip = lambda u : np.roll(u,1,0), lambda u : np.roll(u,-1,0)
    jm, jp = lambda u : np.roll(u,1,1), lambda u : np.roll(u,-1,1)
    km, kp = lambda u : np.roll(u,1,2), lambda u : np.roll(u,-1,2)
    ones, zeros = np.ones, np.zeros

    def assemble_rhs(mass, momentum_x, momentum_y, momentum_z, energy, w):
        rhs_w = zeros(w.shape)
        rhs_w[:,:,:,0] = mass
        rhs_w[:,:,:,1] = momentum_x
        rhs_w[:,:,:,2] = momentum_y
        rhs_w[:,:,:,3] = momentum_z
        rhs_w[:,:,:,-1] = energy

        rhs_w[:,:,:,1] += 0.1 * c0 * obstacle * w[:,:,:,1]
        rhs_w[:,:,:,2] += 0.1 * c0 * obstacle * w[:,:,:,2]
        rhs_w[:,:,:,3] += 0.1 * c0 * obstacle * w[:,:,:,3]
        rhs_w += 0.1 * c0 * (w - W0) * fan[:,:,:,np.newaxis]
        return rhs_w

    def distribute_w(w):
        return np.rollaxis(w, 3)

    w2 = step(w0)
    assert abs(w1 - w2).max() < 1E-6

    # assert os.path.exists(vis_bin)
    # assert os.path.exists(graph_outfile)
    # subprocess.call([vis_bin, graph_outfile, dot_outfile])
    # assert os.path.exists(dot_outfile)
    # assert os.path.exists(dot_outfile + '.pdf')
