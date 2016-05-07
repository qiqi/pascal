import os
import sys
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..'))

import numpy
import enzyme

im, ip = enzyme.im, enzyme.ip
def heatMidpoint(u):
    dx, dt = 0.1, 0.01
    uh = u + 0.5 * dt / dx**2 * (im(u) + ip(u) - 2 * u)
    return u + dt / dx**2 * (im(uh) + ip(uh) - 2 * uh)

Ni, Nj, Nk = 8, 4, 3
u0 = numpy.random.random([Ni, Nj, Nk])

G1, G2 = enzyme.decompose(heatMidpoint, verbose='visualize')

u1 = enzyme.execute((G1, G2), u0)

im, ip = lambda u : numpy.roll(u,1,0), lambda u : numpy.roll(u,-1,0)
u2 = heatMidpoint(u0)

assert abs(u1 - u2).max() < 1E-6
