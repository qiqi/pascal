################################################################################
#                                                                              #
#      sa2d_classic.py copyright(c) Qiqi Wang 2016 (qiqi.wang@gmail.com)       #
#                                                                              #
################################################################################

import uuid
import time
import copy
import multiprocessing

import dill
import numpy as np

from pascal import mpi_worker_commander as commander
from pascal import sa2d_decomp
from pascal import sa2d_theano
from pascal import sa2d_mpi
from pascal.sa2d_mpi import grid2d, stencil_array, _is_like_sa, infer_context

def compile_stage(pickled_stage):
    stage = dill.loads(pickled_stage)
    upstream_arrays = [sa2d_theano.stencil_array(None, v.shape, True)
                       for v in stage.upstream_values]
    triburary_arrays = [sa2d_theano.stencil_array(None, v.shape, True)
                        for v in stage.triburary_values]
    theano_inputs = [a.value for a in upstream_arrays + triburary_arrays]
    downstream_arrays = stage(upstream_arrays, triburary_arrays)
    theano_outputs = [a.value for a in downstream_arrays]
    theano_function = sa2d_theano.compile(theano_inputs, theano_outputs)
    return dill.dumps(theano_function)

class Stage(object):
    def __init__(self, stage, compiled_function, grid):
        '''
        Takes sa2d_decomp.AtomicStage as input, compile theano function,
        and send it via commander
        '''
        self.upstream_values = stage.upstream_values
        self.triburary_values = stage.triburary_values
        self.downstream_values = stage.downstream_values
        self.grid = grid
        self.stage_name = str(uuid.uuid1())
        grid._commander.set_custom_func(self.stage_name, compiled_function)
        self._G_ZERO = grid.zeros()

    def _reference(self, v):
        if hasattr(v, '_reference'):
            return v._reference
        else:
            assert v is sa2d_decomp.G_ZERO
            return self._G_ZERO

    def __call__(self, mpi_inputs):
        '''
        return mpi_outputs
        '''
        if _is_like_sa(mpi_inputs):
            mpi_inputs = [mpi_inputs]
        inputs = (list(mpi_inputs) +
                  [self._reference(v) for v in self.triburary_values])
        outputs = [self.grid._array(commander.WorkerVariable(), v.shape)
                   for v in self.downstream_values]
        self.grid._commander.func(
                self.stage_name,
                [a._var for a in inputs],
                result_var=[a._var for a in outputs],
                return_result=False)
        return outputs

def decompose_function(func, mpi_inputs, verbose=True, num_procs=None):
    grid = mpi_inputs[0].grid
    stages = sa2d_decomp.decompose_function(func, mpi_inputs, verbose)
    pickled_stages = map(dill.dumps, stages)
    pool = multiprocessing.Pool(4)
    compiled_stages = pool.map(compile_stage, pickled_stages)
    # compiled_stages = [compile_stage(s) for s in pickled_stages]
    return [Stage(s, f, grid) for s, f in zip(stages, compiled_stages)]

################################################################################
################################################################################
################################################################################
