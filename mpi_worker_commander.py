from __future__ import division
from __future__ import unicode_literals
import sys
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
        self.custom_funcs[name] = dill.loads(func)

    # -------------------------------------------------------------------- #

    def func(self, func, args, kwargs, result_var):
        if isinstance(func, type('')):
            func = self.custom_funcs[func]
        elif isinstance(func, bytes):
            func = dill.loads(func)
        args = self._substitute_args(args)
        kwargs = self._substitute_kwargs(kwargs)
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            raise RuntimeError('Error executing function {0} with args {1} ' \
                    'and kwargs {2}'.format(func, args, kwargs))
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
        for kw, arg in kwargs.items():
            if is_worker_variable(arg):
                kwargs[kw] = self.variables[arg.keys]
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

        MPI.COMM_WORLD.Isend(np.array(result[0,:], order='C'), x_m)
        MPI.COMM_WORLD.Isend(np.array(result[-1,:], order='C'), x_p)
        MPI.COMM_WORLD.Isend(np.array(result[:,0], order='C'), y_m)
        MPI.COMM_WORLD.Isend(np.array(result[:,-1], order='C'), y_p)

        x_buffer = np.empty((2,) + result.shape[1:])
        y_buffer = np.empty((2, result.shape[0]) + result.shape[2:])

        rq_x_m = MPI.COMM_WORLD.Irecv(x_buffer[0], x_m)
        rq_x_p = MPI.COMM_WORLD.Irecv(x_buffer[1], x_p)
        rq_y_m = MPI.COMM_WORLD.Irecv(y_buffer[0], y_m)
        rq_y_p = MPI.COMM_WORLD.Irecv(y_buffer[1], y_p)

        ni, nj = result.shape[:2]
        full_result = np.ones((ni + 2, nj + 2) + result.shape[2:])
        full_result[1:-1,1:-1] = result

        MPI.Request.Waitall([rq_x_m, rq_x_p, rq_y_m, rq_y_p])
        full_result[0,1:-1] = x_buffer[0]
        full_result[-1,1:-1] = x_buffer[-1]
        full_result[1:-1,0] = y_buffer[0]
        full_result[1:-1,-1] = y_buffer[-1]
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
                   'Worker does not have method named: {1}'.format(method_name)
            worker_method = getattr(worker, method_name)
            return_val = worker_method(*args)
            if return_result:
                command_comm.gather(return_val, 0)
        except Exception as e:
            if return_result:
                command_comm.gather(e, 0)
            else:
                sys.stderr.write('\nError on MPI_Worker {0}:\n{1}\n'.format(
                    command_comm.rank, traceback.format_exc()))


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
    [132496.0, 267696.0, 267696.0, 402896.0]
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
                rank_x_m = (i + niProc - 1) % niProc * njProc + j
                rank_x_p = (i + 1) % niProc * njProc + j
                rank_y_m = i * njProc + (j + njProc - 1) % njProc
                rank_y_p = i * njProc + (j + 1) % njProc
                neighbor_ranks = (rank_x_m, rank_x_p, rank_y_m, rank_y_p)

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
        args = (name, dill.dumps(func))
        self._broadcast_to_workers(('set_custom_func', args, False))

    # -------------------------------------------------------------------- #

    def func(self, func, args=(), kwargs={},
             result_var=None, return_result=True):
        args = (func, args, kwargs, result_var)
        self._broadcast_to_workers(('func', args, return_result))
        if return_result:
            return self._gather_from_workers()

    # -------------------------------------------------------------------- #

    def func_nonuniform_args(self, func, nonuniform_args=(), kwargs={},
             result_var=None, return_result=True):
        assert len(nonuniform_args) == len(self.iRanges) * len(self.jRanges)
        data = tuple(('func', (func, args, kwargs, result_var), return_result) \
                     for args in nonuniform_args)
        self._scatter_to_workers(data)
        if return_result:
            return self._gather_from_workers()

    # -------------------------------------------------------------------- #

    def method(self, variable_key, method_name, args=(), kwargs={},
               result_var=None, return_result=True):
        args = (variable_key, method_name, args, kwargs, result_var)
        self._broadcast_to_workers(('method', args, return_result))
        if return_result:
            return self._gather_from_workers()

    # -------------------------------------------------------------------- #

    @staticmethod
    def _i_ranges(ni, niProc):
        iRanges = np.around(ni / niProc * np.arange(niProc + 1))
        return tuple((iRanges[i], iRanges[i+1]) for i in range(niProc))

    # -------------------------------------------------------------------- #

    def _broadcast_to_workers(self, message):
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
                raise report
        return reports


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

class TestPassingParamters(unittest.TestCase):
    def testPassingNumpyArray(self):
        comm = MPI_Commander(4, 8, 1, 2)
        z34 = WorkerVariable()
        def make_worker_variable(z, x):
            return x + z.reshape(z.shape + (1,) * x.ndim)
        comm.set_custom_func('make_worker_variable', make_worker_variable)
        comm.func('make_worker_variable', (ZERO, np.zeros([3,4])),
                result_var=z34)
        comm.set_custom_func('get_shape', lambda x : x.shape)
        shape0, shape1 = comm.func('get_shape', (z34,))
        self.assertEqual(shape0, shape1)
        self.assertEqual(shape0, (6, 6, 3, 4))

    def testPassingNonUniformNumpyArray(self):
        comm = MPI_Commander(4, 8, 1, 2)
        z34 = WorkerVariable()
        def make_worker_variable(z, x):
            return x + z.reshape(z.shape + (1,) * x.ndim)
        comm.set_custom_func('make_worker_variable', make_worker_variable)
        args = ((ZERO, np.zeros([3,4])), (ZERO, np.ones([3,4])))
        comm.func_nonuniform_args('make_worker_variable', args, result_var=z34)
        comm.set_custom_func('get_shape', lambda x : x.shape)
        shape0, shape1 = comm.func('get_shape', (z34,))
        self.assertEqual(shape0, shape1)
        self.assertEqual(shape0, (6, 6, 3, 4))
        max0, max1 = comm.func(np.max, (z34,))
        min0, min1 = comm.func(np.min, (z34,))
        self.assertEqual(max0, 0)
        self.assertEqual(min0, 0)
        self.assertEqual(max1, 1)
        self.assertEqual(min1, 1)


#==============================================================================#

class TestFunctions(unittest.TestCase):
    def testNumpyFunsions(self):
        comm = MPI_Commander(4, 8, 1, 2)
        sin_j = WorkerVariable()
        comm.func(np.sin, (J,), result_var=sin_j)
        comm.func(np.copy, (sin_j,), result_var=sin_j)
        sin_j_max = comm.func(np.max, (sin_j,))
        self.assertAlmostEqual(sin_j_max[0], 0.90929742682568171)
        self.assertAlmostEqual(sin_j_max[1], 0.98935824662338179)

    def testPickledNumpyFunsions(self):
        comm = MPI_Commander(4, 8, 1, 2)
        sin_j = WorkerVariable()
        comm.func(dill.dumps(np.sin), (J,), result_var=sin_j)
        comm.func(np.copy, (sin_j,), result_var=sin_j)
        sin_j_max = comm.func(np.max, (sin_j,))
        self.assertAlmostEqual(sin_j_max[0], 0.90929742682568171)
        self.assertAlmostEqual(sin_j_max[1], 0.98935824662338179)

#==============================================================================#
#                                                                              #
#==============================================================================#

if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'worker':
        mpi_worker_main()
    else:
        doctest.testmod()
        unittest.main()
