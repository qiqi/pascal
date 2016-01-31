from __future__ import division, print_function
from __future__ import unicode_literals
import pickle
import uuid

import numpy as np

from sa2d_mpi import grid2d, stencil_array, _is_like_sa
import sa2d_decomp
import sa2d_theano
import mpi_worker_commander as commander


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

        decomp_inputs = tuple(sa2d_decomp.stencil_array(inp.shape)
                              for inp in mpi_inputs)
        self.stages = sa2d_decomp.decompose(func, decomp_inputs)
        theano_stages = compile_stages(self.stages, mpi_inputs)

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
            stage_in = (stage_in +
                        [s._reference._var for s in stage.sourceValues])

            if k < n_stages - 1:
                out_shapes = [(stage.output_size_no_nbr,)]
                if stage.output_size_has_nbr:
                    out_shapes.append((stage.output_size_has_nbr,))
            else:
                out_shapes = [out.shape for out in stage.outputs]

            stage_out, outputs = [], []
            for shape in out_shapes:
                var = commander.WorkerVariable()
                out = self.grid._array(var, shape)
                stage_out.append(var)
                outputs.append(out)

            self.grid._commander.func(
                    stage_name,
                    stage_in,
                    result_var=stage_out,
                    return_result=False)

            if k < len(self.stages) - 1:
                print(outputs)
                stage_in = stage_out

        if len(outputs) == 1:
            return outputs[0]
        else:
            return outputs

G = grid2d(32, 16, 2)
f = G.zeros()
u0 = G.ones() + G.sin(G.i * np.pi / G.nx * 2)

def heat(u):
    dx = 0.1
    return (u.x_m + u.x_p + u.y_m + u.y_p - 4 * u) / dx**2 + f

def heatMidpoint(u):
    dt = 0.01
    uh = u + 0.5 * dt * heat(u)
    return u + dt * heat(uh)

s = Stages(heatMidpoint, u0)
u1 = s(u0)
