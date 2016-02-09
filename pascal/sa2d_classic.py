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


def compile_stages(stages, inputs):
    make_np = lambda shape : np.empty((3, 3) + shape)
    if _is_like_sa(inputs):
        inputs = [inputs]
    stage_in = [make_np(inp.shape) for inp in inputs]

    compiled_stages = []

    for k, stage in enumerate(stages):
        n_input = len(stage_in)
        stage_in = stage_in + [make_np(s.shape) for s in stage.sourceValues]

        def stage_func(stage_in):
            in_obj, src_obj = stage_in[:n_input], stage_in[n_input:]
            if k > 0:
                in_obj = stage.unstack_input(*tuple(in_obj))
            out_obj = stage(in_obj, src_obj)
            if k < len(stages) - 1:
                out_obj = stage.stack_output(out_obj)
            return out_obj

        compiled_stage = sa2d_theano.compile(stage_func, stage_in)
        compiled_stages.append(compiled_stage)

        if k < len(stages) - 1:
            inp_shape = (stage.output_size_no_nbr,)
            stage_in = [make_np(inp_shape)]
            if stage.output_size_has_nbr:
                inp_shape = (stage.output_size_has_nbr,)
                stage_in.append(make_np(inp_shape))

    return compiled_stages


class Stages(object):
    def __init__(self, func, mpi_inputs):
        if _is_like_sa(mpi_inputs):
            mpi_inputs = [mpi_inputs]
        self.grid = mpi_inputs[0].grid

        self.G_ZERO = self.grid.zeros()

        decomp_inputs = tuple(sa2d_decomp.stencil_array(inp.shape)
                              for inp in mpi_inputs)
        t0 = time.time()
        self.stages = sa2d_decomp.decompose(func, decomp_inputs)
        print('decompose takes ', time.time() - t0)
        theano_stages = compile_stages(self.stages, mpi_inputs)
        print('compile takes ', time.time() - t0)

        common_name = str(uuid.uuid1())
        n_stages = len(theano_stages)
        self.stage_names = [common_name + '[' + str(i) + ']'
                            for i in range(n_stages)]
        for stage_name, stage in zip(self.stage_names, theano_stages):
            self.grid._commander.set_custom_func(stage_name, stage)

    def __call__(self, mpi_inputs):
        if _is_like_sa(mpi_inputs):
            mpi_inputs = [mpi_inputs]
        stage_in = [inp._var for inp in mpi_inputs]

        n_stages = len(self.stages)
        for k in range(n_stages):
            stage_name = self.stage_names[k]
            stage = self.stages[k]

            n_input = len(stage_in)
            for s in stage.sourceValues:
                if hasattr(s, '_reference'):
                    stage_in.append(s._reference._var)
                else:
                    assert s is sa2d_decomp.G_ZERO
                    stage_in.append(self.G_ZERO._var)

            if k < n_stages - 1:
                out_shapes = [(stage.output_size_no_nbr,)]
                if stage.output_size_has_nbr:
                    out_shapes.append((stage.output_size_has_nbr,))
            else:
                out_shapes = [out.shape for out in stage.outputs]

            stage_out_previous = stage_out if k > 0 else []
            stage_out, outputs = [], []
            for shape in out_shapes:
                var = commander.WorkerVariable()
                stage_out.append(var)
                if k == n_stages - 1:
                    out = self.grid._array(var, shape)
                    outputs.append(out)

            self.grid._commander.func(
                    stage_name,
                    stage_in,
                    result_var=stage_out,
                    return_result=False)

            # delete outputs of previous stage
            for var in stage_out_previous:
                self.grid._commander.delete_variable(var)

            if k < len(self.stages) - 1:
                stage_in = copy.copy(stage_out)
                for var in stage_in:
                    if hasattr(var, '_reference'): del var._reference

        if len(outputs) == 1:
            return outputs[0]
        else:
            return outputs

################################################################################
################################################################################
################################################################################
