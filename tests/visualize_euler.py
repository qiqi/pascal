import os
import sys
import time
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..'))

from pascal.sa2d_decomp import *
from pascal.operators import infer_context

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

    0.1 * c0 * obstacle
    rhs_w[1:3] += 0.1 * c0 * obstacle * w[1:3]
    rhs_w += 0.1 * c0 * (w - w0) * fan

    return rhs_w

def step(w):
    dw0 = -dt * rhs(w)
    dw1 = -dt * rhs(w + 0.5 * dw0)
    dw2 = -dt * rhs(w + 0.5 * dw1)
    dw3 = -dt * rhs(w + dw2)
    return w + (dw0 + dw3) / 6 + (dw1 + dw2) / 3

x = (builtin.I + 0.5) * dx - 0.2 * Lx
y = (builtin.J + 0.5) * dy - 0.5 * Ly

obstacle = exp(-((x**2 + y**2) / 1)**64)
fan = 2 * cos((x / Lx + 0.2) * np.pi)**64

stages = decompose_function(step, stencil_array((4,)), 'visualize')

from pascal.workers.commander import MPI_Commander
n = 100
comm = MPI_Commander('classic_mpi', n, n, 2, 2)
comm.process_job(stages, 100, np.zeros([n,n,4]))
comm.dismiss()
