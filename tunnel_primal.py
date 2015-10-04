import matplotlib
matplotlib.use('agg')
matplotlib.interactive(False)

import pdb
import sys
import time
import argparse
from pylab import *

from tunnel import *


parser = argparse.ArgumentParser()
parser.add_argument('--restart', type=str, default='')
args = parser.parse_args()

if len(args.restart) == 0:
    w = grid.zeros([4]) + w0
    w[:] *= 1 + 0.01 * (grid.random() - 0.5)
else:
    print('restarting from ', args.restart)
    w = load(args.restart)
    assert w.shape == (Nx, Ny, 4)

figure(figsize=(28,10))
for iplot in range(5000):
    nPrintsPerPlot = 500
    for iprint in range(nPrintsPerPlot):
        nStepPerPrint = 20
        for istep in range(nStepPerPrint):
            w = step(w)
        print('%f %f' % tuple(force(w)))
        sys.stdout.flush()
    w.save('w{0:06d}.npy'.format(iplot))
    r, ru, rv, p = w
    rho, u, v = r * r, ru / r, rv / r
    clf()
    u_range = linspace(-u0, u0 * 2, 100)
    subplot(2,1,1); contourf(x._data.T, y._data.T, u._data.T,
            u_range, extend='both')
    axis('scaled'); colorbar()
    v_range = linspace(-u0, u0, 100)
    subplot(2,1,2); contourf(x._data.T, y._data.T, v._data.T,
            v_range, extend='both')
    axis('scaled'); colorbar()
    savefig('fig{0:06d}.png'.format(iplot))

