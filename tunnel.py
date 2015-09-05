import matplotlib
matplotlib.use('agg')
matplotlib.interactive(False)

import sys
import time
import argparse
from pylab import *
from psarray import *

# ---------------------------------------------------------------------------- #
#                                 PROBLEM SET UP                               #
# ---------------------------------------------------------------------------- #

DISS_COEFF = 0.01
gamma, R = 1.4, 287.
T0, p0, M0 = 300., 101325., 0.05

rho0 = p0 / (R * T0)
c0 = sqrt(gamma * R * T0)
u0 = c0 * M0
w0 = np.array([np.sqrt(rho0), np.sqrt(rho0) * u0, 0., p0])

Lx, Ly = 25., 5.
dx = dy = 0.25
dt = dx / u0 * 0.5
Nx, Ny = int(Lx / dx), int(Ly / dy)

x = array2d(Nx, Ny, lambda i,j: (i + 0.5) * dx -0.2 * Lx)
y = array2d(Nx, Ny, lambda i,j: (j + 0.5) * dy -0.2 * Ly)

obstacle = exp(-(x**2 + y**2)**4)

dc = cos((x / Lx + 0.2) * pi)**64

stop

# ---------------------------------------------------------------------------- #
#                        FINITE DIFFERENCE DISCRETIZATION                      #
# ---------------------------------------------------------------------------- #

def diffx(w):
    return (roll(w, -1, axis=0) - roll(w, 1, axis=0)) / (2 * dx)

def diffy(w):
    return (roll(w, -1, axis=1) - roll(w, 1, axis=1)) / (2 * dy)

def dissipation(r, u, dc):
    # conservative, negative definite dissipation applied to r*d(ru)/dt
    def laplace(u):
        return (roll(u, -1, axis=0) + roll(u, 1, axis=0) \
              + roll(u, -1, axis=1) + roll(u, 1, axis=1)) * 0.25 - u
    rho = r * r
    return laplace(dc * rho * laplace(u))

def rhs(w):
    r, ru, rv, p = w[:,:,0], w[:,:,1], w[:,:,2], w[:,:,-1]
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

    one = np.ones(r.shape)
    dissipation_r = dissipation(one, r*r, DISS_COEFF) * c0 / dx
    dissipation_x = dissipation(r, u, DISS_COEFF) * c0 / dx
    dissipation_y = dissipation(r, v, DISS_COEFF) * c0 / dy
    dissipation_p = dissipation(one, p, DISS_COEFF) * c0 / dx

    mass += dissipation_r
    momentum_x += dissipation_x
    momentum_y += dissipation_y
    energy += dissipation_p \
            - (gamma - 1) * (u * dissipation_x + v * dissipation_y)

    rhs_w = zeros(w.shape)
    rhs_w[:,:,0] = 0.5 * mass / r
    rhs_w[:,:,1] = momentum_x / r
    rhs_w[:,:,2] = momentum_y / r
    rhs_w[:,:,-1] = energy

    rhs_w[i_obstacle,j_obstacle,1:3] += 0.1*c0 * w[i_obstacle, j_obstacle, 1:3]
    rhs_w += 0.1*c0 * (w - w0) * dc[:,:,newaxis]

    return rhs_w

def midpoint_res(w1, w0):
    return (w1 - w0) / dt + rhs(0.5 * (w0 + w1))

# ---------------------------------------------------------------------------- #
#                              TESTS FOR CONSERVATION                          #
# ---------------------------------------------------------------------------- #

def conserved(w):
    r, ru, rv, p = w[:,:,0], w[:,:,1], w[:,:,2], w[:,:,-1]
    rho, u, v = r * r, ru / r, rv / r

    mass = rho.sum()
    momentum_x = (rho * u).sum()
    momentum_y = (rho * v).sum()
    energy = (p / (gamma - 1) + 0.5 * ru * ru + 0.5 * rv * rv).sum()
    return mass, momentum_x, momentum_y, energy

def ddt_conserved(w, rhs_w):
    r, ru, rv, p = w[:,:,0], w[:,:,1], w[:,:,2], w[:,:,-1]
    rho, u, v = r * r, ru / r, rv / r

    ddt_rho = -rhs_w[:,:,0] * 2 * r
    ddt_rhou = -rhs_w[:,:,1] * r + 0.5 * u * ddt_rho
    ddt_rhov = -rhs_w[:,:,2] * r + 0.5 * v * ddt_rho
    ddt_p = -rhs_w[:,:,-1]
    ddt_rhou2 = 2 * u * ddt_rhou - u**2 * ddt_rho
    ddt_rhov2 = 2 * v * ddt_rhov - v**2 * ddt_rho

    ddt_mass = ddt_rho.sum()
    ddt_momentum_x = ddt_rhou.sum()
    ddt_momentum_y = ddt_rhov.sum()
    ddt_energy = ddt_p.sum() / (gamma - 1) \
            + 0.5 * ddt_rhou2.sum() + 0.5 * ddt_rhov2.sum()
    return ddt_mass, ddt_momentum_x, ddt_momentum_y, ddt_energy

# ---------------------------------------------------------------------------- #
#                                   MAIN PROGRAM                               #
# ---------------------------------------------------------------------------- #

parser = argparse.ArgumentParser()
parser.add_argument('--restart', type=str, default='')
args = parser.parse_args()

if len(args.restart) == 0:
    w = zeros([Nx, Ny, 4]) + w0
    w[:,:,1] *= 1 + 0.01 * (random.random(w[:,:,1].shape) - 0.5)
else:
    print('restarting from ', args.restart)
    w = load(args.restart)
    assert w.shape == (Nx, Ny, 4)

print(ddt_conserved(w, rhs(w)))

print(conserved(w))

figure(figsize=(18,10))
for iplot in range(5000):
    nStepPerPlot = 10
    for istep in range(nStepPerPlot):
        print(r'<br>')
        w = solve(midpoint_res, w, (w,), rel_tol=1E-9)
        w.obliviate()
        sys.stdout.flush()
        np.save('w{0:06d}'.format(iplot * nStepPerPlot + istep), value(w))
    print(r'<br>')
    print(conserved(w))
    r, ru, rv, p = w[:,:,0], w[:,:,1], w[:,:,2], w[:,:,-1]
    rho, u, v = r * r, ru / r, rv / r
    clf()
    u_range = linspace(-u0, u0 * 2, 100)
    subplot(2,1,1); contourf(x, y, value(u).T, u_range);
    axis('scaled'); colorbar()
    v_range = linspace(-u0, u0, 100)
    subplot(2,1,2); contourf(x, y, value(v).T, v_range);
    axis('scaled'); colorbar()
    savefig('fig{0:06d}.png'.format(iplot))

