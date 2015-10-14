import argparse
import pylab
import histstack

from tunnel3d import *

parser = argparse.ArgumentParser()
parser.add_argument('nStart', type=int)
parser.add_argument('nEnd', type=int)
args = parser.parse_args()

if args.nStart == 0:
    Q = grid.zeros([Nz, 5]) + Q0
    Q[:] *= 1 + 0.01 * (grid.random() - 0.5)
else:
    Q = grid.load('Q{0:06d}.npy'.format(args.nStart))
    assert Q.shape == (grid.Nx, grid.Ny, Nz, 5)

pylab.figure(figsize=(16,9))
for iplot in range(200):
    for iprint in range(nPrintsPerPlot):
        for istep in range(nStepPerPrint):
            Q = step(Q)
        print('%f %f %f' % tuple(force(Q)))
        sys.stdout.flush()

    Q.save('Q{0:06d}.npy'.format(iplot))

    r, ru, rv, rw, p = Q.T
    rho, u, v, w = r * r, ru / r, rv / r, rw / r
    clf()

    u_range = linspace(-u0, u0 * 2, 100)
    pylab.subplot(2,1,1)
    pylab.contourf(x._data.T, y._data.T, u[0]._data.T, u_range, extend='both')
    pylab.axis('scaled'); pylab.colorbar()

    v_range = linspace(-u0, u0, 100)
    pylab.subplot(2,1,2)
    pylab.contourf(x._data.T, y._data.T, v[0]._data.T, v_range, extend='both')
    pylab.axis('scaled'); pylab.colorbar()

    savefig('fig{0:06d}.png'.format(iplot))

