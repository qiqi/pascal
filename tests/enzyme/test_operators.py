import os
import sys
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..', '..'))

import numpy as np
import enzyme

def test_sum():
    def update(u):
        v = u * enzyme.ones([3,2])
        return v.sum(1).sum()

    Ni, Nj, Nk = 8, 4, 3
    u0 = np.random.random([Ni, Nj, Nk])
    G = enzyme.decompose(update)
    u1 = enzyme.execute(G, u0)

    def update(u):
        v = u[:,:,:,np.newaxis,np.newaxis] * np.ones([3,2])
        return v.sum(4).sum(3)
    u2 = update(u0)
    assert abs(u1 - u2).max() < 1E-10
