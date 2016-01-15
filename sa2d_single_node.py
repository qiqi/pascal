from __future__ import division
import multiprocessing
import numpy as np
import fast_pipe


class SA2d_Single_Node_Worker_Variable(object):
    def __init__(self, key):
        self.key = key


class SA2d_Single_Node_Worker(object):
    '''
    This class runs in worker processes
    '''
    def __init__(self, i, j, neighbor_pipes):
        self.i, self.j = i, j
        self.neighbor_pipes = neighbor_pipes
        self.variables = {}

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

    # ------------------------------------------------------------------- #

    def _combine_args(self, args):
        combined_args = []
        for arg in args
            if isinstance(arg, SA2d_Single_Node_Worker_Variable):
                arg = self.variables[arg.key]
            combined_args.append(arg)
        return tuple(combined_args)

    def _combine_kwargs(self, kwargs):
        for kw in kwargs:
            if isinstance(kwargs[kw], SA2d_Single_Node_Worker_Variable):
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
        ni, nj = result.shape[:2]
        full_result = np.ones((ni + 2, nj + 2) + result.shape[2:])

        x_m, x_p, y_m, y_p = self.neighbor_pipes
        x_m.exchange(result[0,:],  full_result[0,1:-1])
        x_p.exchange(result[-1,:], full_result[-1,1:-1])
        y_m.exchange(result[:,0],  full_result[1:-1,0])
        y_p.exchange(result[:,-1], full_result[1:-1,-1])

        full_result[1:-1,1:-1] = result
        return full_result


def process_target(iRange, jRange, command_pipe, neighbor_pipes):
    (i0, i1), (j0, j1) = iRange, jRange
    i = np.outer(np.arange(i0 - 1, i1 + 1), np.ones(j1 - j0 + 2, int))
    j = np.outer(np.ones(i1 - i0 + 2, int), np.arange(j0 - 1, j1 + 1))
    worker = SA2d_Single_Node_Worker(i, j, neighbor_pipes)

    while True:
        next_task_list = command_pipe.recv()
        if next_task_list is None:
            break
        func_name, args, kwargs = next_task_list
        func = getattr(worker, func_name)
        command_pipe.send(func(*args, **kwargs))


class SA2d_Single_Node_Middleman(object):
    def __init__(self, ni, nj, niProc, niProc):
        iRanges = self._i_ranges(ni, niProc)
        jRanges = self._i_ranges(nj, njProc)

        pipes, procs = [], []
        for i in range(ni):
            pipes.append([])
            procs.append([])
            for j in range(ni):
                p0, p1 = multiprocessing.Pipe()
                args = (iRange, jRange, p1, neighbor_pipes)
                proc = multiprocessing.Process(target=process_target, args=args)
                proc.start()

                pipes[-1].append(p0)
                procs[-1].append(proc)
        self.pipes = np.array(pipes)
        self.procs = np.array(procs)

    @staticmethod
    def _i_ranges(ni, niProc):
        iRanges = np.array(np.around(ni / niProc * np.arange(niProc + 1)), int)
        return tuple((iRanges[i], iRanges[i+1]) for i in range(ni))

    def __del__(self):
        for p in self.pipes.ravel():
            p.send(None)
        for p in self.procs.ravel():
            p.join()

    def func(self, func, args, kwargs, result_key):
        args = (func, args, kwargs, result_key)
        self.command_pipe.send('func', args)

    def method(self, variable_key, method_name, args, kwargs, result_key):
        args = (variable_key, method_name, args, kwargs, result_key)
        self.command_pipe.send('method', args)
