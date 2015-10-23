################################################################################
#                                                                              #
#           tunnel.py copyright 2015 Qiqi Wang (qiqi.wang@gmail.com)           #
#                                                                              #
################################################################################

import pdb
import sys
import time
import numpy as np
import psarray_local as psarray

# ---------------------------------------------------------------------------- #
#                                 PROBLEM SET UP                               #
# ---------------------------------------------------------------------------- #

DISS_COEFF = 0.005
gamma, R = 1.4, 287.
T0, p0, M0 = 300., 101325., 0.25

rho0 = p0 / (R * T0)
c0 = np.sqrt(gamma * R * T0)
u0 = c0 * M0
Q0 = np.array([np.sqrt(rho0), np.sqrt(rho0) * u0, 0., 0., p0])

Lx, Ly, Lz = 40., 10., 2.
dx = dy = dz = 0.125
dt = dx / c0 * 0.5

grid = psarray.grid2d(int(Lx / dx), int(Ly / dy))
Nz = int(Lz / dz)

x = (grid.i + 0.5) * dx - 0.2 * Lx
y = (grid.j + 0.5) * dy - 0.5 * Ly

obstacle = grid.exp(-((x**2 + (y - 0.01)**2) / 1)**64)

fan = 4 * grid.cos((x / Lx + 0.2) * np.pi)**64

nPrintsPerPlot, nStepPerPrint = 400, 5

# ---------------------------------------------------------------------------- #
#                        FINITE DIFFERENCE DISCRETIZATION                      #
# ---------------------------------------------------------------------------- #

def diffx(w):
    return (w.x_p - w.x_m) / (2 * dx)

def diffy(w):
    return (w.y_p - w.y_m) / (2 * dy)

def diffz(w):
    return (grid.roll(w,-1,axis=0) - grid.roll(w,1,axis=0)) / (2 * dz)

def dissipation(r, u, dc):
    # conservative, negative definite dissipation applied to r*d(ru)/dt
    laplace = lambda u : (u.x_p + u.x_m + u.y_p + u.y_m \
            + grid.roll(u,-1,axis=0) + grid.roll(u,1,axis=0)) / 6. - u
    return laplace(dc * r * r * laplace(u))

def rhs(Q):
    r, ru, rv, rw, p = Q.T
    u, v, w = ru / r, rv / r, rw / r

    mass = diffx(r * ru) + diffy(r * rv) + diffz(r * rw)
    momentum_x = (diffx(ru*ru) + (r*ru) * diffx(u)) / 2.0 \
               + (diffy(rv*ru) + (r*rv) * diffy(u)) / 2.0 \
               + (diffz(rw*ru) + (r*rw) * diffz(u)) / 2.0 \
               + diffx(p)
    momentum_y = (diffx(ru*rv) + (r*ru) * diffx(v)) / 2.0 \
               + (diffy(rv*rv) + (r*rv) * diffy(v)) / 2.0 \
               + (diffz(rw*rv) + (r*rw) * diffz(v)) / 2.0 \
               + diffy(p)
    momentum_z = (diffx(ru*rw) + (r*ru) * diffx(w)) / 2.0 \
               + (diffy(rv*rw) + (r*rv) * diffy(w)) / 2.0 \
               + (diffz(rw*rw) + (r*rw) * diffz(w)) / 2.0 \
               + diffz(p)
    energy = gamma * (diffx(p * u) + diffy(p * v) + diffz(p * w)) \
           - (gamma - 1) * (u * diffx(p) + v * diffy(p) + w * diffz(p))

    one = grid.ones(r.shape)
    # dissipation_x = dissipation(r, u, DISS_COEFF) * c0 / dx
    # dissipation_y = dissipation(r, v, DISS_COEFF) * c0 / dy
    # dissipation_z = dissipation(r, w, DISS_COEFF) * c0 / dz
    dissipation_p = dissipation(one, p, DISS_COEFF) * c0 / min(dx,dy,dz)

    # momentum_x += dissipation_x
    # momentum_y += dissipation_y
    # momentum_z += dissipation_z
    energy += dissipation_p #- (gamma - 1) * (u * dissipation_x + \
                            #                 v * dissipation_y + \
                            #                 w * dissipation_z)

    rhs_Q = grid.zeros(Q.shape)
    rhs_Q[:,0] = 0.5 * mass / r
    rhs_Q[:,1] = momentum_x / r
    rhs_Q[:,2] = momentum_y / r
    rhs_Q[:,3] = momentum_z / r
    rhs_Q[:,-1] = energy

    rhs_Q[:,1:-1] += 0.1 * c0 * obstacle * Q[:,1:-1]
    rhs_Q += 0.1 * c0 * (Q - Q0) * fan

    return rhs_Q


def force(Q):
    return grid.reduce_sum(0.1 * c0 * obstacle * Q[:,1:-1]).sum(0) * (dx*dy*dz)


@psarray.psc_compile
def step(Q):
    dQ0 = -dt * rhs(Q)
    dQ1 = -dt * rhs(Q + 0.5 * dQ0)
    dQ2 = -dt * rhs(Q + 0.5 * dQ1)
    dQ3 = -dt * rhs(Q + dQ2)
    return Q + (dQ0 + dQ3) / 6 + (dQ1 + dQ2) / 3


# ---------------------------------------------------------------------------- #
#                              TESTS FOR CONSERVATION                          #
# ---------------------------------------------------------------------------- #

def conserved(Q):
    r, ru, rv, rw, p = Q.T
    rho, u, v, w = r * r, ru / r, rv / r, rw / r

    mass = grid.reduce_sum(rho).sum()
    momentum_x = grid.reduce_sum(rho * u).sum()
    momentum_y = grid.reduce_sum(rho * v).sum()
    momentum_z = grid.reduce_sum(rho * w).sum()
    energy = grid.reduce_sum(p / (gamma - 1) \
           + 0.5 * ru * ru + 0.5 * rv * rv + 0.5 * rw * rw).sum()
    return mass, momentum_x, momentum_y, momentum_z, energy

def ddt_conserved(Q, rhs_Q):
    r, ru, rv, rw, p = Q.T
    rho, u, v, w = r * r, ru / r, rv / r, rw / r

    ddt_rho = -rhs_Q[:,0] * 2 * r
    ddt_rhou = -rhs_Q[:,1] * r + 0.5 * u * ddt_rho
    ddt_rhov = -rhs_Q[:,2] * r + 0.5 * v * ddt_rho
    ddt_rhow = -rhs_Q[:,3] * r + 0.5 * w * ddt_rho
    ddt_p = -rhs_Q[:,-1]
    ddt_rhou2 = 2 * u * ddt_rhou - u**2 * ddt_rho
    ddt_rhov2 = 2 * v * ddt_rhov - v**2 * ddt_rho
    ddt_rhow2 = 2 * w * ddt_rhow - w**2 * ddt_rho

    ddt_mass = grid.reduce_sum(ddt_rho).sum()
    ddt_momentum_x = grid.reduce_sum(ddt_rhou).sum()
    ddt_momentum_y = grid.reduce_sum(ddt_rhov).sum()
    ddt_momentum_z = grid.reduce_sum(ddt_rhow).sum()
    ddt_energy = grid.reduce_sum(ddt_p / (gamma - 1) + \
                             0.5 * (ddt_rhou2 + ddt_rhov2 + ddt_rhow2)).sum()
    return ddt_mass, ddt_momentum_x, ddt_momentum_y, ddt_momentum_z, ddt_energy



# ---------------------------------------------------------------------------- #
#                                 TESTS PROBLEM                                #
# ---------------------------------------------------------------------------- #

if __name__ == '__main__':
    obstacle *= 0
    fan *= 0
    # DISS_COEFF = 0.0

    Q = (grid.ones([Nz,5]) + 0.01 * grid.random([Nz,5])) * Q0
    Q[:,1:-1] += 0.01 * (grid.random([Nz,3]) - 0.5) * Q0[1]
    conserved_0 = np.array(conserved(Q))
    print(np.array(ddt_conserved(Q, rhs(Q))))
    for eps in [1E-10, 1E-9, 1E-8, 1E-7, 1E-6, 1E-5, 1E-4, 1E-3]:
        conserved_1 = np.array(conserved(Q - eps * rhs(Q)))
        print((conserved_1 - conserved_0) / eps)


################################################################################
################################################################################
################################################################################
