################################################################################
#                                                                              #
#        commander.py copyright(c) Qiqi Wang 2015 (qiqi.wang@gmail.com)        #
#                                                                              #
################################################################################

import os
import sys
import time

import numpy as np
from mpi4py import MPI

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '../..'))

import pascal.workers
from pascal.sa2d_generate_c import decompose_function, stencil_array

import pascal.sa2d_single_thread

class MPI_Commander(object):
    '''
    Creates a set of MPI worker processes and commands them to various
    tasks through two methods, 'func' and 'method'.  For example,

    >>> comm = MPI_Commander(100, 100, 2, 2)

    >>> i_plus_j = WorkerVariable()

    >>> comm.func(operator.add, (I, J), result_var=i_plus_j)
    [None, None, None, None]

    >>> comm.func(np.shape, (i_plus_j,))
    [(52, 52), (52, 52), (52, 52), (52, 52)]

    >>> comm.method(i_plus_j, 'sum')
    [132496, 267696, 267696, 402896]

    >>> comm.delete_variable(i_plus_j)
    '''
    def __init__(self, worker, ni, nj, niProc, njProc):
        self.worker = getattr(pascal.workers, worker)
        self.ni = int(ni)
        self.nj = int(nj)
        file_path = os.path.split(os.path.abspath(__file__))[0]
        cmd = os.path.join(file_path, worker, 'main')
        self.comm = MPI.COMM_WORLD.Spawn(cmd, (), niProc * njProc)

        assert self.comm.size == 1, "MPI_Commander is designed to " \
                                    "launch from a single processor"
        i_ranges = self._i_ranges(ni, niProc)
        j_ranges = self._i_ranges(nj, njProc)

        self.i_slices = []
        self.j_slices = []

        for i, i_range in enumerate(i_ranges):
            for j, j_range in enumerate(j_ranges):
                rank = i * njProc + j
                rank_i_m = (i + niProc - 1) % niProc * njProc + j
                rank_i_p = (i + 1) % niProc * njProc + j
                rank_j_m = i * njProc + (j + njProc - 1) % njProc
                rank_j_p = i * njProc + (j + 1) % njProc
                neighbor_ranks = (rank_i_m, rank_i_p, rank_j_m, rank_j_p)

                self.i_slices.append(slice(i_range[0], i_range[1]))
                self.j_slices.append(slice(j_range[0], j_range[1]))

                worker_global_const = np.array([
                    i_range[0], i_range[1], j_range[0], j_range[1],
                    rank_i_m, rank_i_p, rank_j_m, rank_j_p
                ], np.uint64)
                self.comm.Send(worker_global_const, rank)

    # -------------------------------------------------------------------- #

    @staticmethod
    def _i_ranges(ni, niProc):
        i_ranges = np.array(np.around(ni / niProc * np.arange(niProc + 1)), int)
        return tuple((i_ranges[i], i_ranges[i+1]) for i in range(niProc))

    # -------------------------------------------------------------------- #

    def _send_inputs(self, inputs):
        tiled_inputs = []
        for i, j in zip(self.i_slices, self.j_slices):
            tiled_inputs.append(inputs[i, j])
        self.comm.Scatter(np.ravel(tiled_inputs), None, MPI.ROOT)

    def _recv_outputs(self, shape):
        outputs = np.empty(shape, np.float32)
        self.comm.Gather(None, outputs, MPI.ROOT)

    def process_job(self, stages, num_steps, inputs):
        max_vars = max(s.downstream_values[0].size for s in stages)
        num_inputs = stages[0].upstream_values[0].size
        binary = self.worker.build(stages)
        job = np.array([
            max_vars, num_inputs, num_steps, len(binary)
        ], np.uint64)
        self.comm.Bcast(job, MPI.ROOT)
        self.comm.Bcast(np.frombuffer(binary, np.uint8), MPI.ROOT)
        inputs = np.array(inputs, np.float32)
        assert inputs.shape[:2] == (self.ni, self.nj)
        assert inputs.size == self.ni * self.nj * num_inputs
        self._send_inputs(inputs)
        self._recv_outputs(inputs.shape)

    # -------------------------------------------------------------------- #

    def dismiss(self):
        if self.comm is not None:
            self.comm.Bcast(np.zeros(4, np.uint64), MPI.ROOT)
            self.comm.Barrier()
            self.comm = None

    # -------------------------------------------------------------------- #

    def __del__(self):
        self.dismiss()


def test_classic_mpi():
    n = 100
    comm = MPI_Commander('classic_mpi', n, n, 2, 2)
    def heat(w):
        return w.i_p + w.i_m - 2 * w
    def step(w):
        return w + heat(w + 0.5 * heat(w))
    # G = pascal.sa2d_single_thread.grid2d(n, n)
    # w = G.zeros()
    # t0 = time.time()
    # for i in range(1000):
    #     w = step(w)
    # print('Single thread: ', time.time() - t0)
    t0 = time.time()
    stages = decompose_function(step, stencil_array())
    comm.process_job(stages, 1000, np.zeros([n,n]))
    print('Time =', time.time() - t0)
    comm.dismiss()

if __name__ == '__main__':
    test_classic_mpi()
