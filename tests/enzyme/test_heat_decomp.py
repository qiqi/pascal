import os
import sys
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..', '..'))

import numpy as np
import enzyme

def test_heat_midpoint():
    im, ip = enzyme.im, enzyme.ip
    jm, jp = enzyme.jm, enzyme.jp
    km, kp = enzyme.km, enzyme.kp
    def heat_midpoint(u):
        dx, dt = 0.1, 0.01
        uh = u + 0.5 * dt / dx**2 * (im(u) + ip(u) - 2 * u +
                                     jm(u) + jp(u) - 2 * u +
                                     km(u) + kp(u) - 2 * u)
        return u + dt / dx**2 * (im(uh) + ip(uh) - 2 * uh +
                                 jm(uh) + jp(uh) - 2 * uh +
                                 km(uh) + kp(uh) - 2 * uh)
    Ni, Nj, Nk = 8, 4, 3
    u0 = np.random.random([Ni, Nj, Nk])
    G1, G2 = enzyme.decompose(heat_midpoint)
    u1 = enzyme.execute((G1, G2), u0)
    im, ip = lambda u : np.roll(u,1,0), lambda u : np.roll(u,-1,0)
    jm, jp = lambda u : np.roll(u,1,1), lambda u : np.roll(u,-1,1)
    km, kp = lambda u : np.roll(u,1,2), lambda u : np.roll(u,-1,2)
    u2 = heat_midpoint(u0)
    assert abs(u1 - u2).max() < 1E-10
