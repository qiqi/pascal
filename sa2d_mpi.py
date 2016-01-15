from __future__ import division
import sys
from mpi4py import MPI
import numpy as np


class SA2d_MPI_Worker_Variable(object):
    def __init__(self, key):
        self.key = key


class SA2d_MPI_Worker(object):
    def __init__(self, i, j, neighbor_ranks):
        self.i, self.j = i, j
        self.neighbor_ranks = neighbor_ranks
        self.variables = {}

    def _combine_args(self, args):
        combined_args = []
        for arg in args
            if isinstance(arg, SA2d_MPI_Worker_Variable):
                arg = self.variables[arg.key]
            combined_args.append(arg)
        return tuple(combined_args)

    def _combine_kwargs(self, kwargs):
        for kw in kwargs:
            if isinstance(kwargs[kw], SA2d_MPI_Worker_Variable):
                kwargs[kw] = self.variables[kwarg[kw].keys]
        return kwargs

    def _update_result(self, result, result_key):
        if isinstance(result_key, tuple):
            assert isinstance(result, tuple) and len(result) == len(result_key)
            for r, k in zip(result, result_key):
                self._update_result(r, k)
        elif result_key:
            assert isinstance(result, np.ndarray)
            assert result.ndim >= 2
            ni, nj = self.i.shape[0] - 2, self.i.shape[1] - 2
            if result.shape[:2] != (ni + 2, nj + 2):
                assert result.shape[:2] == (ni, nj)
                result = self._update_result_neighbor(result)
            self.variables[result_key] = result
        else:
            return result

    def _update_result_neighbor(self, result):
        x_m, x_p, y_m, y_p = self.neighbor_ranks

        MPI.COMM_WORLD.Isend(result[0,:], x_m)
        MPI.COMM_WORLD.Isend(result[-1,:], x_p)
        MPI.COMM_WORLD.Isend(result[:,0], y_m)
        MPI.COMM_WORLD.Isend(result[:,-1], y_p)

        ni, nj = result.shape[:2]
        full_result = np.ones((ni + 2, nj + 2) + result.shape[2:])
        full_result[1:-1,1:-1] = result

        MPI.COMM_WORLD.Recv(full_result[0,1:-1], x_m)
        MPI.COMM_WORLD.Recv(full_result[-1,1:-1], x_p)
        MPI.COMM_WORLD.Recv(full_result[1:-1,0], y_m)
        MPI.COMM_WORLD.Recv(full_result[1:-1,-1], y_p)

        return full_result

    def func(self, func, args, kwargs, result_key):
        args = self._combine_args(args)
        kwargs = self._combine_kwargs(kwargs)
        result = func(*args, **kwargs)
        return self._update_result(result, result_key)

    def method(self, variable_key, method_name, args, kwargs, result_key):
        variable = self.variables[variable_key]
        method = getattr(variable, method_name)
        args = self._combine_args(args)
        kwargs = self._combine_kwargs(kwargs)
        result = method(*args, **kwargs)
        return self._update_result(result, result_key)


def mpi_worker_main():
    first_message = command_comm.recv()
    command_rank, (i0, i1), (j0, j1), neighbor_ranks = first_message

    i = np.outer(np.arange(i0 - 1, i1 + 1), np.ones(j1 - j0 + 2, int))
    j = np.outer(np.ones(i1 - i0 + 2, int), np.arange(j0 - 1, j1 + 1))
    worker = SA2d_MPI_Worker(i, j, neighbor_ranks)

    while True:
        next_task_list = command_comm.bcast(None, command_rank)
        if next_task_list is None:
            break
        method_name, args, kwargs = next_task_list
        worker_method = getattr(worker, method_name)
        command_comm.gather(worker_method(*args, **kwargs), command_rank)


class SA2d_MPI_Commander(object):
    def __init__(self, ni, nj, niProc, niProc):
        self.comm = MPI.COMM_WORLD.Spawn(sys.executable,
                (__file__, 'worker'), niProc * njProc)

        assert self.comm.size == niProc * njProc + 1
        assert self.comm.rank == 0

        iRanges = self._i_ranges(ni, niProc)
        jRanges = self._i_ranges(nj, njProc)

        for i, iRange in enumerate(niProc):
            for j, jRange in enumerate(njProc):
                rank = i * njProc + j + 1
                rank_x_m = (i + niProc - 1) % niProc * njProc + j + 1
                rank_x_p = (i + 1) % niProc * njProc + j + 1
                rank_y_m = i * njProc + (j + njProc - 1) % njProc + 1
                rank_y_p = i * njProc + (j + 1) % njProc + 1
                neighbor_ranks = (rank_x_m, rank_x_p, rank_y_m, rank_y_p) + 1

                first_message = (self.comm.rank, iRange, jRange, neighbor_ranks)
                self.comm.send(first_message, rank)


    @staticmethod
    def _i_ranges(ni, niProc):
        iRanges = np.array(np.around(ni / niProc * np.arange(niProc + 1)), int)
        return tuple((iRanges[i], iRanges[i+1]) for i in range(ni))

    def _bcast(self, message):
        self.comm.bcast(message, self.comm.rank)

    def _gather(self):
        return self.comm.gather(None, self.comm.rank)

    def __del__(self):
        self._bcast(None)

    def func(self, func, args, kwargs, result_key):
        args = (func, args, kwargs, result_key)
        self._bcast(('func', args))
        return self._gather()

    def method(self, variable_key, method_name, args, kwargs, result_key):
        args = (variable_key, method_name, args, kwargs, result_key)
        self._bcast(('method', args))
        return self._gather()


if __name__ == '__main__':
    if sys.argv[1:] == ('worker',):
        mpi_worker_main()
    else:
