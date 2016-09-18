import os
import sys
import subprocess
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..', '..'))

import numpy as np
import enzyme

def test_euler2d_rk4():
    dx = dy   = 0.05
    xSquares  = 2;
    ySquares  = 1;
    n         = 128
    Nx        =  n * xSquares
    Ny        =  n * ySquares
    Lx = dx * Nx;
    Ly = dy * Ny;

    constants = 2

    DISS_COEFF = 0.0025
    gamma, R = 1.4, 287.
    T0, p0, M0 = 300., 101325., 0.25

    rho0 = p0 / (R * T0)
    c0 = np.sqrt(gamma * R * T0)
    u0 = c0 * M0
    W0 = np.array([np.sqrt(rho0), np.sqrt(rho0) * u0, 0., p0])
    dt = dx / c0 * 0.5
    consts = enzyme.getConstants([2])
    obstacle = consts[0]
    fan      = consts[1]

    im, ip = enzyme.im, enzyme.ip
    jm, jp = enzyme.jm, enzyme.jp
    ones, zeros = enzyme.ones, enzyme.zeros

    def diffx(w):
        return (ip(w) - im(w)) / (2 * dx)

    def diffy(w):
        return (jp(w) - jm(w)) / (2 * dy)

    def dissipation(r, u, dc):
        # conservative, negative definite dissipation applied to r*d(ru)/dt
        laplace = lambda u: (ip(u) + im(u) +
                             jp(u) + jm(u)) / 4. - u
        return laplace(dc * r * r * laplace(u))

    def assemble_rhs(mass, momentum_x, momentum_y, energy, w):
        rhs_w = zeros(w.shape)
        rhs_w[0] = mass
        rhs_w[1] = momentum_x
        rhs_w[2] = momentum_y
        rhs_w[-1] = energy

        rhs_w[1:2] += 0.1 * c0 * obstacle * w[1:2]
        rhs_w += 0.1 * c0 * (w - W0) * fan
        return rhs_w

    def distribute_w(w):
        return w

    def rhs(w):
        r, rux, ruy, p = distribute_w(w)
        ux, uy = rux / r, ruy / r

        mass = diffx(r * rux) + diffy(r * ruy) 
        momentum_x = (diffx(rux*rux) + (r*rux) * diffx(ux)) / 2.0 \
                   + (diffy(ruy*rux) + (r*ruy) * diffy(ux)) / 2.0 \
                   + diffx(p)
        momentum_y = (diffx(rux*ruy) + (r*rux) * diffx(uy)) / 2.0 \
                   + (diffy(ruy*ruy) + (r*ruy) * diffy(uy)) / 2.0 \
                   + diffy(p)
        energy = gamma * (diffx(p * ux) + diffy(p * uy) ) \
               - (gamma - 1) * (ux * diffx(p) + uy * diffy(p) )

        one = ones(r.shape)
        dissipation_x = dissipation(r, ux, DISS_COEFF) * c0 / dx
        dissipation_y = dissipation(r, uy, DISS_COEFF) * c0 / dy
        dissipation_p = dissipation(one, p, DISS_COEFF) * c0 / dx

        momentum_x += dissipation_x
        momentum_y += dissipation_y
        energy += dissipation_p \
                - (gamma - 1) * (ux * dissipation_x +
                                 uy * dissipation_y )

        return assemble_rhs(0.5 * mass / r,
                            momentum_x / r,
                            momentum_y / r,
                            energy, w)
    def init(u):
        
        x = (enzyme.builtin.I + 0.5) * dx - 0.2 * Lx
        y = (enzyme.builtin.J + 0.5) * dy - 0.5 * Ly

        obstacle = enzyme.exp(-(x*x + ((y-.25)*(y-.25))/.1)**8)
        fan = 2 * (enzyme.cos((x / Lx + 0.2) * np.pi)**64 +
                   enzyme.sin((y / Ly) * np.pi)**64)

        u[0] = np.sqrt(rho0)
        u[1] = np.sqrt(rho0) * u0
        u[2] = 0.
        u[3] = p0
        u[4] = obstacle
        u[5] = fan

        return u

    def step(w):
        dw0 = -dt * rhs(w)
        dw1 = -dt * rhs(w + 0.5 * dw0)
        dw2 = -dt * rhs(w + 0.5 * dw1)
        dw3 = -dt * rhs(w + dw2)
        return w + (dw0 + dw3) / 6 + (dw1 + dw2) / 3

    initialization = enzyme.decompose(init, enzyme.stencil_array(6),
                                      comp_graph_output_file=None)
    stages = enzyme.decompose(step, enzyme.stencil_array(4),
                              comp_graph_output_file=None)
    enzyme.execute(initialization,stages, constants , n , xSquares , ySquares)

test_euler2d_rk4()
