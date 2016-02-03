from __future__ import division, print_function
from __future__ import unicode_literals
import pickle
import uuid
import time

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
                stage_in = stage_out

        if len(outputs) == 1:
            return outputs[0]
        else:
            return outputs

# G = grid2d(128, 64, 2)
# f = G.zeros()
# u0 = G.ones() + G.sin(G.i * np.pi / G.nx * 2)
# 
# def heat(u):
#     dx = 0.1
#     return (u.x_m + u.x_p + u.y_m + u.y_p - 4 * u) / dx**2 + f
# 
# def heatMidpoint(u):
#     dt = 0.01
#     uh = u + 0.5 * dt * heat(u)
#     return u + dt * heat(uh)
# 
# s = Stages(heatMidpoint, u0)
# t0 = time.time()
# n = 1000
# for i in range(n):
#     u0 = s(u0)
# usum = G.reduce_sum(u0)
# print((time.time() - t0) / n * 1E6)

if __name__ == '__main__':
    DISS_COEFF = 0.0025
    gamma, R = 1.4, 287.
    T0, p0, M0 = 300., 101325., 0.25

    rho0 = p0 / (R * T0)
    c0 = np.sqrt(gamma * R * T0)
    u0 = c0 * M0
    w0 = np.array([np.sqrt(rho0), np.sqrt(rho0) * u0, 0., p0])

    Lx, Ly = 40., 10.
    dx = dy = 0.05
    dt = dx / c0 * 0.5

    Ni, Nj = 128, 64
    G = grid2d(Ni, Nj, 2)

    x = (G.i + 0.5) * dx - 0.2 * Lx
    y = (G.j + 0.5) * dy - 0.5 * Ly

    obstacle = G.exp(-((x**2 + y**2) / 1)**64)
    fan = 2 * G.cos((x / Lx + 0.2) * np.pi)**64

    def diffx(w):
        return (w.x_p - w.x_m) / (2 * dx)

    def diffy(w):
        return (w.y_p - w.y_m) / (2 * dy)

    def dissipation(r, u, dc):
        # conservative, negative definite dissipation applied to r*d(ru)/dt
        laplace = lambda u: (u.x_p + u.x_m + u.y_p + u.y_m) * 0.25 - u
        return laplace(dc * r * r * laplace(u))

    def rhs(w):
        r, ru, rv, p = w
        u, v = ru / r, rv / r

        mass = diffx(r * ru) + diffy(r * rv)
        momentum_x = (diffx(ru*ru) + (r*ru) * diffx(u)) / 2.0 \
                   + (diffy(rv*ru) + (r*rv) * diffy(u)) / 2.0 \
                   + diffx(p)
        momentum_y = (diffx(ru*rv) + (r*ru) * diffx(v)) / 2.0 \
                   + (diffy(rv*rv) + (r*rv) * diffy(v)) / 2.0 \
                   + diffy(p)
        energy = gamma * (diffx(p * u) + diffy(p * v)) \
               - (gamma - 1) * (u * diffx(p) + v * diffy(p))

        one = infer_context(w).ones(r.shape)
        dissipation_x = dissipation(r, u, DISS_COEFF) * c0 / dx
        dissipation_y = dissipation(r, v, DISS_COEFF) * c0 / dy
        dissipation_p = dissipation(one, p, DISS_COEFF) * c0 / dx

        momentum_x += dissipation_x
        momentum_y += dissipation_y
        energy += dissipation_p \
                - (gamma - 1) * (u * dissipation_x + v * dissipation_y)

        rhs_w = infer_context(w).zeros(w.shape)
        rhs_w[0] = 0.5 * mass / r
        rhs_w[1] = momentum_x / r
        rhs_w[2] = momentum_y / r
        rhs_w[-1] = energy

        rhs_w[1:3] += 0.1 * c0 * obstacle * w[1:3]
        rhs_w += 0.1 * c0 * (w - w0) * fan

        return rhs_w

    def step(w):
        dw0 = -dt * rhs(w)
        dw1 = -dt * rhs(w + 0.5 * dw0)
        dw2 = -dt * rhs(w + 0.5 * dw1)
        dw3 = -dt * rhs(w + dw2)
        return w + (dw0 + dw3) / 6 + (dw1 + dw2) / 3

    w = G.zeros() + w0
    s = Stages(step, w)
    t0 = time.time()
    n = 1000
    for i in range(n):
        w = s(w)
    wsum = G.reduce_sum(w)
    print((time.time() - t0) / n * 1E6)
