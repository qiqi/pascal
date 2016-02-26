import os
import sys
import time
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..'))

from pascal.sa2d_classic import *

try:
    nx, nproc = int(sys.argv[1]), int(sys.argv[2])
except:
    print('correct arguments: nx, nproc')
    sys.exit(0)

t0 = time.time()
G = grid2d(nx, nx, nproc)
f = G.zeros()
print('building grid2d: ', time.time() - t0)

def heat(u):
    dx = 0.1
    return (u.x_m + u.x_p + u.y_m + u.y_p - 4 * u) / dx**2 + f

@timestep
def step(u):
    dt = 0.001
    uh = u + 0.5 * dt * heat(u)
    return u + dt * heat(uh)

def raw_step(u):
    dt = 0.001
    uh = u + 0.5 * dt * heat(u)
    return u + dt * heat(uh)

u = G.ones() + G.sin(G.i * np.pi / G.nx * 2)

n = 1000
t0 = time.time()
for i in range(n):
    u = step(u)
print('run stages: ', time.time() - t0)
