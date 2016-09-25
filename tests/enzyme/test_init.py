import os
import sys
import time
import subprocess
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..', '..'))

vis_bin = os.path.join(my_path, '../../bin/quarkflowvis')
graph_outfile = os.path.join(my_path, 'stages.comp_graph')
init_outfile = os.path.join(my_path, 'init.comp_graph')
graph_dot_file = os.path.join(my_path, 'stages.dot')
init_dot_file = os.path.join(my_path, 'init.dot')

import numpy as np
import enzyme

#if __name__ == '__main__':
def test_heat_midpoint():
    im, ip = enzyme.im, enzyme.ip
    jm, jp = enzyme.jm, enzyme.jp
    km, kp = enzyme.km, enzyme.kp
    I = enzyme.builtin.I
    f = enzyme.sin(I)
    print(I, f, f.ndim, f.size, len(f), 1+f, 1-f, 1/f, 2**f, f.copy())
    def heat_midpoint(u):
        dx, dt = 0.1, 0.01
        return u + 0.5 * dt / dx**2 * (im(u) + ip(u) - 2 * u) + dt * f
    Ni, Nj, Nk = 8, 4, 3
    u0 = np.random.random([Ni, Nj, Nk])
    stages, init = enzyme.decompose(heat_midpoint,
                                    comp_graph_output_file=graph_outfile,
                                    init_graph_output_file=init_outfile)
    u1 = enzyme.execute(stages, u0, init).reshape(u0.shape)

    im, ip = lambda u : np.roll(u,1,0), lambda u : np.roll(u,-1,0)
    I = np.arange(Ni)[:,np.newaxis,np.newaxis] + np.zeros([Ni,Nj,Nk])
    f = np.sin(I)
    u2 = heat_midpoint(u0)
    assert abs(u1 - u2).max() < 1E-10

    assert os.path.exists(vis_bin)
    assert os.path.exists(graph_outfile)
    assert os.path.exists(init_outfile)
    subprocess.call([sys.executable, vis_bin, graph_outfile, graph_dot_file])
    subprocess.call([sys.executable, vis_bin, init_outfile, init_dot_file])
    assert os.path.exists(graph_dot_file)
    assert os.path.exists(init_dot_file)
