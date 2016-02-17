################################################################################
#                                                                              #
#      sa2d_classic.py copyright(c) Qiqi Wang 2016 (qiqi.wang@gmail.com)       #
#                                                                              #
################################################################################

import pickle
import uuid
import time
import copy

import numpy as np

from pascal import mpi_worker_commander as commander
from pascal import sa2d_decomp
from pascal import sa2d_theano
from pascal import sa2d_mpi
from pascal.sa2d_mpi import grid2d, stencil_array, _is_like_sa, infer_context

class MpiStage(object):
    def __init__(self, stage, grid):
        '''
        Takes sa2d_decomp.AtomicStage as input, compile theano function,
        and send it via commander
        '''
        self.grid = grid
        self.upstream_values = stage.upstream_values
        self.triburary_values = stage.triburary_values
        self.downstream_values = stage.downstream_values
        theano_function = self._compile_theano_function(stage)
        self.stage_name = str(uuid.uuid1())
        grid._commander.set_custom_func(self.stage_name, theano_function)
        self._G_ZERO = grid.zeros()

    def _compile_theano_function(self, stage):
        upstream_arrays = [sa2d_theano.stencil_array(None, v.shape, True)
                           for v in self.upstream_values]
        triburary_arrays = [sa2d_theano.stencil_array(None, v.shape, True)
                            for v in self.triburary_values]
        theano_inputs = [a.value for a in upstream_arrays + triburary_arrays]
        downstream_arrays = stage(upstream_arrays, triburary_arrays)
        theano_outputs = [a.value for a in downstream_arrays]
        return sa2d_theano.compile(theano_inputs, theano_outputs)

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

def decompose_function(func, mpi_inputs, verbose=True):
    grid = mpi_inputs[0].grid
    stages = sa2d_decomp.decompose_function(func, mpi_inputs, verbose)
    return [MpiStage(s, grid) for s in stages]

################################################################################
################################################################################
################################################################################
