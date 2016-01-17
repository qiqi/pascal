from __future__ import division
import sys
import operator
import unittest
import doctest
import dill
from mpi4py import MPI
import numpy as np


#==============================================================================#
#                                                                              #
#==============================================================================#

class WorkerVariable(object):
    '''
    When instances of this class are passed from commander to worker,
    the worker knows that it represents a variable that is already in its
    variables dictionary; the key of the existing variable is stored in key.
    '''
    __is_worker_variable__ = True
    __global_variable_key__ = 0

    def __init__(self, key=None):
        if key is None:
            key = WorkerVariable.__global_variable_key__
            WorkerVariable.__global_variable_key__ += 1
        self.key = key

    def __repr__(self):
        return 'WorkerVariable({0})'.format(repr(self.key))

# ---------------------------------------------------------------------------- #

def is_worker_variable(variable):
    return hasattr(variable, '__is_worker_variable__')

#==============================================================================#
#                                                                              #
#==============================================================================#

class MPI_Worker(object):
    '''
    One instance of this class is created in each worker process.
    All calculations performed by the worker is initiated by
    calling one method of this instance.
    '''
    def __init__(self, i, j, neighbor_ranks):
        self.neighbor_ranks = neighbor_ranks
        assert i.shape == j.shape
        self.i = i
        self.j = j
        z = np.zeros(i.shape)
        self.variables = {'i': i, 'j': j, '_z': z}
        self.custom_funcs = {}

    # -------------------------------------------------------------------- #

    def set_custom_func(self, name, func):
        self.custom_funcs[name] = dill.loads(func)

    # -------------------------------------------------------------------- #

    def func(self, func, args, kwargs, result_var):
        if isinstance(func, str):
            func = self.custom_funcs[func]
        args = self._substitute_args(args)
        kwargs = self._substitute_kwargs(kwargs)
        result = func(*args, **kwargs)
        return self._update_result(result, result_var)

    # -------------------------------------------------------------------- #

    def method(self, variable, method_name, args, kwargs, result_var):
        assert is_worker_variable(variable)
        variable = self.variables[variable.key]
        method = getattr(variable, method_name)
        args = self._substitute_args(args)
        kwargs = self._substitute_kwargs(kwargs)
        result = method(*args, **kwargs)
        return self._update_result(result, result_var)

    # -------------------------------------------------------------------- #

    def _substitute_args(self, args):
        substituted_args = []
        for arg in args:
            if is_worker_variable(arg):
                arg = self.variables[arg.key]
            substituted_args.append(arg)
        return tuple(substituted_args)

    # -------------------------------------------------------------------- #

    def _substitute_kwargs(self, kwargs):
        for kw in kwargs:
            if is_worker_variable(arg):
                kwargs[kw] = self.variables[kwarg[kw].keys]
        return kwargs

    # -------------------------------------------------------------------- #

    def _update_result(self, result, result_var):
        if isinstance(result_var, tuple):
            assert isinstance(result, tuple) and len(result) == len(result_var)
            for res, var in zip(result, result_var):
                self._update_result(res, var)
        elif result_var is not None:
            assert is_worker_variable(result_var)
            assert isinstance(result, np.ndarray)
            assert result.ndim >= 2
            ni, nj = self.i.shape[0] - 2, self.i.shape[1] - 2
            if result.shape[:2] != (ni + 2, nj + 2):
                assert result.shape[:2] == (ni, nj)
                result = self._update_result_neighbor(result)
            self.variables[result_var.key] = result
        else:
            return result

    # -------------------------------------------------------------------- #

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


#==============================================================================#
#                                                                              #
#==============================================================================#

def mpi_worker_main():
    '''
    The function that runs in each MPI worker process.  It creates
    a MPI_Worker instance, and runs a loop to obtain instructions
    from the command instance, perform the instruction via the MPI_Worker
    instance, and return the result to the command instance.
    '''
    command_comm = MPI.Comm.Get_parent()
    first_message = command_comm.recv()
    (i0, i1), (j0, j1), neighbor_ranks = first_message

    i = np.outer(np.arange(i0 - 1, i1 + 1), np.ones(j1 - j0 + 2, int))
    j = np.outer(np.ones(i1 - i0 + 2, int), np.arange(j0 - 1, j1 + 1))
    worker = MPI_Worker(i, j, neighbor_ranks)

    while True:
        next_task_list = command_comm.bcast(None, 0)
        if next_task_list == 'finalize':
            break
        method_name, args = next_task_list
        assert hasattr(worker, method_name), \
               'Worker does not have method named: {1}'.format(method_name)
        worker_method = getattr(worker, method_name)
        command_comm.gather(worker_method(*args), 0)


#==============================================================================#
#                                                                              #
#==============================================================================#

class MPI_Commander(object):
    '''
    Creates a set of MPI worker processes and commands them to various
    tasks through two methods, 'func' and 'method'.  For example,

    >>> comm = MPI_Commander(100, 100, 2, 2)

    >>> i, j = WorkerVariable('i'), WorkerVariable('j')

    >>> i_plus_j = WorkerVariable()

    >>> comm.func(operator.add, (i, j), result_var=i_plus_j)
    [None, None, None, None]

    >>> comm.func(np.shape, (i_plus_j,))
    [(52, 52), (52, 52), (52, 52), (52, 52)]

    >>> comm.method(i_plus_j, 'sum')
    [132496.0, 267696.0, 267696.0, 402896.0]
    '''
    def __init__(self, ni, nj, niProc, njProc):
        self.comm = MPI.COMM_WORLD.Spawn(sys.executable,
                (__file__, 'worker'), niProc * njProc)

        assert self.comm.size == 1, "MPI_Commander is designed to " \
                                    "launch from a single processor"
        iRanges = self._i_ranges(ni, niProc)
        jRanges = self._i_ranges(nj, njProc)

        for i, iRange in enumerate(iRanges):
            for j, jRange in enumerate(jRanges):
                rank = i * njProc + j
                rank_x_m = (i + niProc - 1) % niProc * njProc + j
                rank_x_p = (i + 1) % niProc * njProc + j
                rank_y_m = i * njProc + (j + njProc - 1) % njProc
                rank_y_p = i * njProc + (j + 1) % njProc
                neighbor_ranks = (rank_x_m, rank_x_p, rank_y_m, rank_y_p)

                first_message = (iRange, jRange, neighbor_ranks)
                self.comm.send(first_message, rank)

    # -------------------------------------------------------------------- #

    def __del__(self):
        if self.comm is not None:
            self._broadcast_to_workers('finalize')
            self.comm = None

    # -------------------------------------------------------------------- #

    def set_custom_func(self, name, func):
        args = (name, dill.dumps(func))
        self._broadcast_to_workers(('set_custom_func', args))
        return self._gather_from_workers()

    # -------------------------------------------------------------------- #

    def func(self, func, args=(), kwargs={}, result_var=None):
        args = (func, args, kwargs, result_var)
        self._broadcast_to_workers(('func', args))
        return self._gather_from_workers()

    # -------------------------------------------------------------------- #

    def method(self, variable_key, method_name, args=(), kwargs={},
               result_var=None):
        args = (variable_key, method_name, args, kwargs, result_var)
        self._broadcast_to_workers(('method', args))
        return self._gather_from_workers()

    # -------------------------------------------------------------------- #

    @staticmethod
    def _i_ranges(ni, niProc):
        iRanges = np.around(ni / niProc * np.arange(niProc + 1))
        return tuple((iRanges[i], iRanges[i+1]) for i in range(niProc))

    # -------------------------------------------------------------------- #

    def _broadcast_to_workers(self, message):
        self.comm.bcast(message, MPI.ROOT)

    # -------------------------------------------------------------------- #

    def _gather_from_workers(self):
        return self.comm.gather(None, MPI.ROOT)


#==============================================================================#
#                                                                              #
#==============================================================================#

class TestCustomFunction(unittest.TestCase):
    def testAddOne(self):
        comm = MPI_Commander(8, 8, 2, 2)
        comm.set_custom_func('add_one', lambda x : x + 1)
        i = WorkerVariable('i')
        ip1 = WorkerVariable()
        comm.func('add_one', (i,), result_var=ip1)
        ip1_sum = comm.func(np.sum, (ip1,))
        self.assertAlmostEqual(ip1_sum[0], 90)
        self.assertAlmostEqual(ip1_sum[1], 90)
        self.assertAlmostEqual(ip1_sum[2], 234)
        self.assertAlmostEqual(ip1_sum[3], 234)

    # -------------------------------------------------------------------- #

    def testDoubleTriple(self):
        comm = MPI_Commander(8, 8, 2, 2)
        comm.set_custom_func('double_triple', lambda x : (2 * x, 3 * x))
        j = WorkerVariable('j')
        j_double, j_triple = WorkerVariable(), WorkerVariable()
        comm.func('double_triple', (j,), result_var=(j_double, j_triple))
        j_double_max = comm.func(np.max, (j_double,))
        j_triple_max = comm.func(np.max, (j_triple,))
        self.assertAlmostEqual(j_double_max[0], 8)
        self.assertAlmostEqual(j_double_max[1], 16)
        self.assertAlmostEqual(j_double_max[2], 8)
        self.assertAlmostEqual(j_double_max[3], 16)
        self.assertAlmostEqual(j_triple_max[0], 12)
        self.assertAlmostEqual(j_triple_max[1], 24)
        self.assertAlmostEqual(j_triple_max[2], 12)
        self.assertAlmostEqual(j_triple_max[3], 24)


#==============================================================================#
#                                                                              #
#==============================================================================#

if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'worker':
        mpi_worker_main()
    else:
        doctest.testmod()
        unittest.main()
