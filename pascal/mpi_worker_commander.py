################################################################################
#                                                                              #
#  mpi_worker_commander.py copyright(c) Qiqi Wang 2015 (qiqi.wang@gmail.com)   #
#                                                                              #
################################################################################

import os
import sys
import time
import types
import numbers
import doctest
import unittest
import operator
import traceback
import dill

import numpy as np
import theano
import theano.tensor as T
from mpi4py import MPI

sys.setrecursionlimit(50000)  # for pickling big theano functions

_DEBUG_MODE_ = False # force all calls to return to commander

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
#                          predefined worker variables                         #
#==============================================================================#

ZERO = WorkerVariable('_z')
I = WorkerVariable('i')
J = WorkerVariable('j')

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
        name = str(name)
        func = dill.loads(func)
        if isinstance(func, types.CodeType):
            func = types.FunctionType(func, globals(), name)
        self.custom_funcs[name] = func

    # -------------------------------------------------------------------- #

    def func(self, func, args, kwargs, result_var):
        if isinstance(func, str):
            func = self.custom_funcs[func]
        elif isinstance(func, bytes):
            func = dill.loads(func)
        args = self._substitute_args(args)
        kwargs = self._substitute_kwargs(kwargs)
        try:
            result = func(*args, **kwargs)
            return self._update_result(result, result_var)
        except Exception as e:
            raise RuntimeError('Error executing function {0} with args {1} ' \
                    'and kwargs {2}'.format(func, args, kwargs))

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

    def delete_variable(self, variable):
        assert is_worker_variable(variable)
        del self.variables[variable.key]

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
        for kw, arg in kwargs.items():
            if is_worker_variable(arg):
                kwargs[kw] = self.variables[arg.keys]
        return kwargs

    # -------------------------------------------------------------------- #

    def _update_result(self, result, result_var):
        if result_var is None:
            return result
        elif is_worker_variable(result_var):
            assert isinstance(result, np.ndarray)
            assert result.ndim >= 2
            ni, nj = self.i.shape[0] - 2, self.i.shape[1] - 2
            if result.shape[:2] != (ni + 2, nj + 2):
                assert result.shape[:2] == (ni, nj)
                result = self._update_result_neighbor(result)
            self.variables[result_var.key] = result
        else:
            for res, var in zip(result, result_var):
                self._update_result(res, var)

    # -------------------------------------------------------------------- #

    def _update_result_neighbor(self, result):
        i_m, i_p, j_m, j_p = self.neighbor_ranks
        i_fwd, i_bwd, j_fwd, j_bwd = 0, 1, 2, 3

        MPI.COMM_WORLD.Isend(np.array(result[0,:], order='C'), i_m, i_bwd)
        MPI.COMM_WORLD.Isend(np.array(result[-1,:], order='C'), i_p, i_fwd)
        MPI.COMM_WORLD.Isend(np.array(result[:,0], order='C'), j_m, j_bwd)
        MPI.COMM_WORLD.Isend(np.array(result[:,-1], order='C'), j_p, j_fwd)

        i_buffer = np.empty((2,) + result.shape[1:])
        j_buffer = np.empty((2, result.shape[0]) + result.shape[2:])

        rq_i_m = MPI.COMM_WORLD.Irecv(i_buffer[0], i_m, i_fwd)
        rq_i_p = MPI.COMM_WORLD.Irecv(i_buffer[1], i_p, i_bwd)
        rq_j_m = MPI.COMM_WORLD.Irecv(j_buffer[0], j_m, j_fwd)
        rq_j_p = MPI.COMM_WORLD.Irecv(j_buffer[1], j_p, j_bwd)

        ni, nj = result.shape[:2]
        full_result = np.ones((ni + 2, nj + 2) + result.shape[2:])
        full_result[1:-1,1:-1] = result

        MPI.Request.Waitall([rq_i_m, rq_i_p, rq_j_m, rq_j_p])
        full_result[0,1:-1] = i_buffer[0]
        full_result[-1,1:-1] = i_buffer[1]
        full_result[1:-1,0] = j_buffer[0]
        full_result[1:-1,-1] = j_buffer[1]
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
        next_task_list = command_comm.bcast(None)
        if next_task_list == 'finalize':
            command_comm.Barrier()
            break
        elif next_task_list == 'scatter':
            next_task_list = command_comm.scatter(None)
        try:
            method_name, args, return_result = next_task_list
            assert hasattr(worker, method_name), \
                   'Worker does not have method named: {0}'.format(method_name)
            worker_method = getattr(worker, method_name)
            return_val = worker_method(*args)
            if return_result:
                command_comm.gather(return_val, 0)
        except Exception as e:
            if return_result:
                e.traceback = traceback.format_exc()
                command_comm.gather(e, 0)
            else:
                sys.stderr.write('\nError on MPI_Worker {0}:{1}\n{2}\n'.format(
                    command_comm.rank, e, traceback.format_exc()))
                sys.stdout.write('\nError on MPI_Worker {0}:{1}\n{2}\n'.format(
                    command_comm.rank, e, traceback.format_exc()))


#==============================================================================#
#                                                                              #
#==============================================================================#

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
    def __init__(self, ni, nj, niProc, njProc):
        self.comm = MPI.COMM_WORLD.Spawn(sys.executable,
                (__file__, 'worker'), niProc * njProc)

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

                first_message = (iRange, jRange, neighbor_ranks)
                self.comm.send(first_message, rank)

    # -------------------------------------------------------------------- #

    def dismiss(self):
        if self.comm is not None:
            self._broadcast_to_workers('finalize')
            self.comm.Barrier()
            self.comm = None

    # -------------------------------------------------------------------- #

    def __del__(self):
        self.dismiss()

    # -------------------------------------------------------------------- #

    def set_custom_func(self, name, func):
        if isinstance(func, types.FunctionType):
            func = dill.dumps(func.__code__, protocol=dill.HIGHEST_PROTOCOL)
        elif not isinstance(func, bytes):
            func = dill.dumps(func, protocol=dill.HIGHEST_PROTOCOL)
        self._broadcast_to_workers(('set_custom_func', (name, func), False))

    # -------------------------------------------------------------------- #

    def func(self, func, args=(), kwargs={},
             result_var=None, return_result=True):
        args = (func, args, kwargs, result_var)
        ret_res = return_result or _DEBUG_MODE_
        self._broadcast_to_workers(('func', args, ret_res))
        if ret_res:
            res = self._gather_from_workers()
            return res if return_result else None

    # -------------------------------------------------------------------- #

    def func_nonuniform_args(self, func, nonuniform_args=(), kwargs={},
             result_var=None, return_result=True):
        assert len(nonuniform_args) == len(self.iRanges) * len(self.jRanges)
        ret_res = return_result or _DEBUG_MODE_
        data = tuple(('func', (func, args, kwargs, result_var), ret_res) \
                     for args in nonuniform_args)
        self._scatter_to_workers(data)
        if ret_res:
            res = self._gather_from_workers()
            return res if return_result else None

    # -------------------------------------------------------------------- #

    def method(self, variable, method_name, args=(), kwargs={},
               result_var=None, return_result=True):
        args = (variable, method_name, args, kwargs, result_var)
        ret_res = return_result or _DEBUG_MODE_
        self._broadcast_to_workers(('method', args, ret_res))
        if ret_res:
            res = self._gather_from_workers()
            return res if return_result else None

    # -------------------------------------------------------------------- #

    def delete_variable(self, variable):
        args = (variable,)
        self._broadcast_to_workers(('delete_variable', args, False))

    # -------------------------------------------------------------------- #

    @staticmethod
    def _i_ranges(ni, niProc):
        iRanges = np.array(np.around(ni / niProc * np.arange(niProc + 1)), int)
        return tuple((iRanges[i], iRanges[i+1]) for i in range(niProc))

    # -------------------------------------------------------------------- #

    def _broadcast_to_workers(self, message):
        if self.comm:
            self.comm.bcast(message, MPI.ROOT)

    def _scatter_to_workers(self, messages):
        self.comm.bcast('scatter', MPI.ROOT)
        self.comm.scatter(messages, root=MPI.ROOT)

    # -------------------------------------------------------------------- #

    def _gather_from_workers(self):
        reports = self.comm.gather(None, MPI.ROOT)
        for report in reports:
            if isinstance(report, BaseException):
                print(report)
                print(report.traceback)
                raise report
        return reports


#==============================================================================#
#                                                                              #
#==============================================================================#

if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'worker':
        my_path = os.path.dirname(os.path.abspath(__file__))
        sys.path.append(os.path.join(my_path, '..'))
        mpi_worker_main()

################################################################################
################################################################################
################################################################################
