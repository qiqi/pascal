################################################################################
#                                                                              #
#        commander.py copyright(c) Qiqi Wang 2015 (qiqi.wang@gmail.com)        #
#                                                                              #
################################################################################

import os

import numpy as np
from mpi4py import MPI

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
        file_path = os.path.split(os.path.abspath(__file__))[0]
        cmd = os.path.join(file_path, worker, 'main')
        print(cmd)
        assert os.path.exists(cmd)
        self.comm = MPI.COMM_WORLD.Spawn(cmd, (), niProc * njProc)

        assert self.comm.size == 1, "MPI_Commander is designed to " \
                                    "launch from a single processor"
        self.iRanges = self._i_ranges(ni, niProc)
        self.jRanges = self._i_ranges(nj, njProc)

        for i, iRange in enumerate(self.iRanges):
            for j, jRange in enumerate(self.jRanges):
                rank = i * njProc + j
                rank_i_m = (i + niProc - 1) % niProc * njProc + j
                rank_i_p = (i + 1) % niProc * njProc + j
                rank_j_m = i * njProc + (j + njProc - 1) % njProc
                rank_j_p = i * njProc + (j + 1) % njProc
                neighbor_ranks = (rank_i_m, rank_i_p, rank_j_m, rank_j_p)

                worker_global_const = np.array([
                    iRange[0], iRange[1], jRange[0], jRange[1],
                    rank_i_m, rank_i_p, rank_j_m, rank_j_p
                ], np.uint64)
                self.comm.Send(worker_global_const, rank)

    # -------------------------------------------------------------------- #

    @staticmethod
    def _i_ranges(ni, niProc):
        iRanges = np.array(np.around(ni / niProc * np.arange(niProc + 1)), int)
        return tuple((iRanges[i], iRanges[i+1]) for i in range(niProc))

    # -------------------------------------------------------------------- #

    def send_job(self, stages, num_steps, inputs):
        pass

    def send_trivial_job(self, stages, num_steps, inputs):
        pass

    # -------------------------------------------------------------------- #

    def dismiss(self):
        if self.comm is not None:
            self.comm.Barrier()
            self.comm = None

    # -------------------------------------------------------------------- #

    def __del__(self):
        self.dismiss()


def test_classic_mpi():
    comm = MPI_Commander('classic_mpi', 10, 10, 2, 2)
    comm.dismiss()

if __name__ == '__main__':
    test_classic_mpi()
