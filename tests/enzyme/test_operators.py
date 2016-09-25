import os
import sys
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..', '..'))

import numpy as np
import enzyme

def test_sum_mean():
#if __name__ == '__main__':
    def update(u):
        v = u * enzyme.ones([3,2])
        return v.T.sum(1).sum() + v.transpose().mean(1).mean()

    Ni, Nj, Nk = 8, 4, 3
    G, I = enzyme.decompose(update)
    consts = enzyme.execute(I, np.zeros([Ni,Nj,Nk,0]))
    u0 = np.random.random([Ni, Nj, Nk])
    u1 = enzyme.execute(G, u0).reshape(u0.shape)

    def update(u):
        v = u[:,:,:,np.newaxis,np.newaxis] * np.ones([3,2])
        return v.transpose([0,1,2,4,3]).sum(4).sum(3) + \
               v.transpose([0,1,2,4,3]).mean(4).mean(3)
    u2 = update(u0)
    assert abs(u1 - u2).max() < 1E-10

