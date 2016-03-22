###############################################################################
#                                                                              #
#       sa2d_decomp.py copyright(c) Qiqi Wang 2015 (qiqi.wang@gmail.com)       #
#                                                                              #
################################################################################

import copy as copymodule
import builtins
import sys
import time
import pickle
import unittest
import operator
import collections

import numpy as np
import theano
import theano.tensor as T
import pulp
import graphviz

from . import operators
from .operators import infer_context
from .sa2d_decomp_value import _is_like_sa_value, stencil_array_value

GLOBAL_MAX_STAGES = -128

# ============================================================================ #

def _is_like_sa(a):
    '''
    Check if object has a stencil array value
    '''
    return hasattr(a, 'value') and _is_like_sa_value(a.value)

# ============================================================================ #
#                          stencil array variable                              #
# ============================================================================ #

class stencil_array(object):

    __context__ = sys.modules[__name__]

    def __init__(self, init=()):
        if _is_like_sa_value(init):
            self.value = init
        else:
            shape = init
            self.value = stencil_array_value(shape)

    def __repr__(self):
        return 'Variable holding {0}'.format(self.value)

    # --------------------------- properties ------------------------------ #

    @property
    def shape(self):
        return self.value.shape

    @property
    def ndim(self):
        return self.value.ndim

    @property
    def size(self):
        return self.value.size

    def __len__(self):
        return len(self.value)

    # --------------------------- operations ------------------------------ #

    # asks ndarray to use the __rops__ defined in this class
    __array_priority__ = 3000

    def __add__(self, a):
        if hasattr(a, '__array_priority__') and \
                a.__array_priority__ > self.__array_priority__:
            return a.__add__(self)
        a = a.value if _is_like_sa(a) else a
        return stencil_array(operators.add(self.value, a).output)

    def __radd__(self, a):
        return self.__add__(a)

    def __sub__(self, a):
        if hasattr(a, '__array_priority__') and \
                a.__array_priority__ > self.__array_priority__:
            return a.__rsub__(self)
        a = a.value if _is_like_sa(a) else a
        return stencil_array(operators.sub(self.value, a).output)

    def __rsub__(self, a):
        a = a.value if _is_like_sa(a) else a
        return stencil_array(operators.sub(a, self.value).output)

    def __mul__(self, a):
        if hasattr(a, '__array_priority__') and \
                a.__array_priority__ > self.__array_priority__:
            return a.__rmul__(self)
        a = a.value if _is_like_sa(a) else a
        return stencil_array(operators.mul(self.value, a).output)

    def __rmul__(self, a):
        return self.__mul__(a)

    def __truediv__(self, a):
        if hasattr(a, '__array_priority__') and \
                a.__array_priority__ > self.__array_priority__:
            return a.__rtruediv__(self)
        a = a.value if _is_like_sa(a) else a
        return stencil_array(operators.truediv(self.value, a).output)

    def __rtruediv__(self, a):
        a = a.value if _is_like_sa(a) else a
        return stencil_array(operators.truediv(a, self.value).output)

    def __pow__(self, a):
        if hasattr(a, '__array_priority__') and \
                a.__array_priority__ > self.__array_priority__:
            return a.__rpow__(self)
        a = a.value if _is_like_sa(a) else a
        return stencil_array(operators.pow(self.value, a).output)

    def __rpow__(self, a):
        a = a.value if _is_like_sa(a) else a
        return stencil_array(operators.pow(a, self.value).output)

    def __neg__(self):
        return stencil_array(operators.neg(self.value).output)

    # ------------------------- math functions ---------------------------- #

    def sum(self, axis=None):
        return sum(self, axis)

    def mean(self, axis=None):
        return mean(self, axis)

    # ------------------------- transformations --------------------------- #

    @property
    def T(self):
        return transpose(self)

    def transpose(self, axes=None):
        return transpose(self, axes)

    def reshape(self, shape):
        return reshape(self, shape)

    def copy(self):
        return copy(self)

    # ------------------------ neighbor access -------------------------- #
    @staticmethod
    class dummy_func(object):
        def __init__(self, shape):
            self.shape = shape
            self.i_p = self
            self.i_m = self
            self.j_p = self
            self.j_m = self

    @property
    def i_p(self):
        return stencil_array(operators.i_p(self.value).output)

    @property
    def i_m(self):
        return stencil_array(operators.i_m(self.value).output)

    @property
    def j_p(self):
        return stencil_array(operators.j_p(self.value).output)

    @property
    def j_m(self):
        return stencil_array(operators.j_m(self.value).output)

    # ---------------------------- indexing ------------------------------- #

    def __getitem__(self, ind):
        return stencil_array(operators.getitem(self.value, ind).output)

    def __setitem__(self, ind, a):
        a = a.value if _is_like_sa(a) else np.array(a, float)
        owner = operators.setitem(self.value, ind, a)
        assert self.shape == owner.output.shape
        self.value = owner.output


# ============================================================================ #
#                             data transformations                             #
# ============================================================================ #

def transpose(x, axes=None):
    assert _is_like_sa(x)
    return stencil_array(operators.transpose(x.value, axes).output)

def reshape(x, shape):
    assert _is_like_sa(x)
    return stencil_array(operators.reshape(x.value, shape).output)

def roll(x, shift, axis=None):
    assert _is_like_sa(x)
    return stencil_array(operators.roll(x.value, shift, axis).output)

def copy(x):
    assert _is_like_sa(x)
    return stencil_array(x.value)


# ============================================================================ #
#                            mathematical functions                            #
# ============================================================================ #

def sin(a):
    assert _is_like_sa(a)
    return stencil_array(operators.sin(a.value).output)

def cos(a):
    assert _is_like_sa(a)
    return stencil_array(operators.cos(a.value).output)

def exp(a):
    assert _is_like_sa(a)
    return stencil_array(operators.exp(a.value).output)

def sum(a, axis=None):
    assert _is_like_sa(a)
    return stencil_array(operators.sum(a.value, axis).output)

def mean(a, axis=None):
    assert _is_like_sa(a)
    n = np.ravel(np.ones(a.shape, int).sum(axis))[0]
    return sum(a) / n

# ============================================================================ #
#                             built-in source array                            #
# ============================================================================ #

class builtin:
    ZERO = stencil_array_value()

def ones(shape=()):
    return stencil_array(builtin.ZERO) + np.ones(shape)

def zeros(shape=()):
    return stencil_array(builtin.ZERO) + np.zeros(shape)


# ============================================================================ #
#                                decomposition                                 #
# ============================================================================ #

_LP = collections.namedtuple('LP', 'c, bounds, A_eq, A_le, b_eq, b_le')
_LPRes = collections.namedtuple('LPRes', 'x, obj, status')

# ---------------------------------------------------------------------------- #

def _build_linear_program(all_values, upstream_values, downstream_values):
    '''
    solution: [c, k, g, K]
    c: length n array of integers, the stage in which a value is created;
    k: length n array of integers, the stage in which a value is killed;
    g: length n array of 0 and 1's, bareness of array,
       1 indicating it is bare, i.e, has no neighbors upon creation;
       0 indicating it has one layer of neighbor upon creation.
    '''
    def add_eq(A_c, A_k, A_g, A_K, b):
        A_eq.append(np.hstack([A_c, A_k, A_g, A_K]))
        b_eq.append(b)

    def add_le(A_c, A_k, A_g, A_K, b):
        A_le.append(np.hstack([A_c, A_k, A_g, A_K]))
        b_le.append(b)

    n = len(all_values)
    A_eq, A_le, b_eq, b_le = [], [], [], []
    # build bounds
    non_negative = (0, GLOBAL_MAX_STAGES)
    bounds = [non_negative] * (2 * n) + [(0, 1)] * n + [non_negative]
    # build constraints
    z = np.zeros(n)
    e = np.eye(n)
    for a in upstream_values:
        i = a._valueId
        # an input value is born at Stage 0
        add_eq(e[i], z, z, 0, 0)
    for a in downstream_values:
        i = a._valueId
        # an output value is killed at Stage K (last stage)
        add_eq(z, e[i], z, -1, 0)
    for a in all_values:
        i = a._valueId
        # a value cannot be killed before it is born
        add_le(e[i], -e[i], z, 0, 0)
        if a.owner:
            for b in a.owner.inputs:
                if _is_like_sa_value(b):
                    assert b in all_values
                    j = b._valueId
                    # a child cannot be born before its parent is born
                    add_le(e[j] - e[i], z, z, 0, 0)
                    # a child cannot be born after its parent is killed
                    add_le(e[i], -e[j], z, 0, 0)
                    if a.owner.access_neighbor:
                        # a bare parent must wait to next stage
                        # to produce any child through neibhor access
                        add_le(e[j] - e[i], z, e[j] - e[i], 0, -1)
                    else:
                        # a bare parent produces bare children
                        # during its creating stage
                        add_le(e[j] - e[i], z, e[j] - e[i], 0, 0)
            if a.owner.access_neighbor:
                # a child born through neighbor access is bare
                add_eq(z, z, e[i], 0, 1)
    w = np.array([a.size for a in all_values])
    c = np.hstack([-w, w, z, 0])
    return _LP(np.array(c, float), np.array(bounds, float),
               np.array(A_eq, float), np.array(A_le, float),
               np.array(b_eq, float), np.array(b_le, float))

# ---------------------------------------------------------------------------- #

def _solve_linear_program_glpk(linear_program, verbose):
    c, bounds, A_eq, A_le, b_eq, b_le = linear_program
    lp = pulp.LpProblem("Decomposition", pulp.LpMinimize)
    # add the variables
    x = []
    for i, (l, u) in enumerate(bounds):
        if u == GLOBAL_MAX_STAGES:
            x.append(pulp.LpVariable('x'+str(i), l, None))
        else:
            x.append(pulp.LpVariable('x'+str(i), l, u))
    # specify the objective
    assert len(x) == len(c)
    # lp += builtins.sum(c[i] * x[i] for i in range(len(x)))
    lp += pulp.LpAffineExpression([(x[i], c[i]) for i in range(len(x))])
    # add the constraints
    for i in range(b_le.size):
        j, = A_le[i].nonzero()
        # lp += builtins.sum(A_le[i, jj] * x[jj] for jj in j) <= b_le[i]
        expr = pulp.LpAffineExpression([(x[jj], A_le[i, jj]) for jj in j])
        lp += pulp.LpConstraint(expr, pulp.LpConstraintLE, rhs=b_le[i])
    for i in range(b_eq.size):
        j, = A_eq[i].nonzero()
        # lp += builtins.sum(A_eq[i, jj] * x[jj] for jj in j) == b_eq[i]
        expr = pulp.LpAffineExpression([(x[jj], A_eq[i, jj]) for jj in j])
        lp += pulp.LpConstraint(expr, pulp.LpConstraintEQ, rhs=b_eq[i])
    # solve with GLPK
    s = pulp.GLPK(mip=0, msg=int(verbose > 1))
    s.actualSolve(lp)
    # extract solution
    x = [pulp.value(xi) for xi in x]
    assert all([abs(xi - round(xi)) < 1E-12 for xi in x]), \
           'Linear Program Finished with non-integer results'
    x = np.array(np.around(x), int)
    objective = int(round(pulp.value(lp.objective)))
    status = pulp.LpStatus[lp.status]
    return _LPRes(x, objective, status)

# ---------------------------------------------------------------------------- #

def _solve_linear_program(linear_program, verbose):
    if verbose:
        lpSize = (len(linear_program.c),
                  len(linear_program.b_eq) + len(linear_program.b_le))
        print('\nDecomposing update formula')
        print('\tsolving {0}x{1} linear program'.format(*lpSize))
        sys.stdout.flush()
        t0 = time.time()
    res = _solve_linear_program_glpk(linear_program, verbose==True)
    if verbose:
        print('Decomposed into {0} atomic stages'.format(res.x[-1] + 1))
        print('\tobjective function = {0}'.format(res.obj))
        print('\tstatus: ' + res.status)
        print('\ttime: {0:f}'.format(time.time() - t0))
        sys.stdout.flush()
    return res

# ---------------------------------------------------------------------------- #

def _assign_lp_results_to_values(lp_result, values):
    c, k, g = lp_result.x[:-1].reshape([3,-1])
    assert c.size == len(values)
    assert g.max() <= 1
    for i, a in enumerate(values):
        a = values[i]
        a.create_stage = int(round(c[i]))
        a.kill_stage = int(round(k[i]))
        a.has_neighbor = (round(g[i]) == 0)
    num_stages = int(lp_result.x[-1]) + 1
    return num_stages

# ---------------------------------------------------------------------------- #

def visualize_graph(filename, upstream_values, downstream_values,
                    view=True, color=None):
    sorted_values = list(copymodule.copy(upstream_values))
    unsorted_values, triburary_values = discover_values(
            upstream_values, downstream_values)
    sort_values(sorted_values, unsorted_values)
    assert unsorted_values == []
    dot = graphviz.Digraph(graph_attr={'rankdir': 'LR'})
    for i, v in enumerate(triburary_values + sorted_values):
        argv = {}
        if v in upstream_values + downstream_values:
            argv['shape'] = 'doublecircle'
        if v in triburary_values:
            argv['shape'] = 'square'
        dot.node(str(i), **argv)
        v._valueId = i
        if hasattr(v, 'owner') and v.owner:
            for inp in v.owner.inputs:
                if _is_like_sa_value(inp):
                    argv = {}
                    if v.owner.access_neighbor:
                        argv['penwidth'] = '15'
                    if hasattr(v, 'create_stage'):
                        argv['colorscheme'] = 'set19'
                        argv['color'] = str(v.create_stage + 1)
                    elif color is not None:
                        argv['colorscheme'] = 'set19'
                        argv['color'] = str(color + 1)
                    dot.edge(str(inp._valueId), str(i), **argv)
    for v in triburary_values + sorted_values:
        del v._valueId
    dot.render(filename, view=view)

# ---------------------------------------------------------------------------- #

def decompose(upstream_values, downstream_values, verbose=True):
    values, triburary_values = discover_values(
            upstream_values, downstream_values)
    all_values = (list(values) +
                  list(triburary_values) +
                  list(upstream_values))
    for i, v in enumerate(all_values):
        v._valueId = i
    lp = _build_linear_program(all_values, upstream_values, downstream_values)
    lp_res = _solve_linear_program(lp, verbose)
    for v in all_values:
        del v._valueId
    if verbose == 'visualize':
        visualize_graph('input.gv', upstream_values, downstream_values, False)
    num_stages = _assign_lp_results_to_values(lp_res, all_values)
    if verbose == 'visualize':
        visualize_graph('color.gv', upstream_values, downstream_values, False)
    # create each atomic stage from its upstream and downstream values
    stages = []
    stage_upstream = list(upstream_values)
    for k in range(1, num_stages):
        stage_downstream = [v for v in all_values
                            if v.create_stage < k and v.kill_stage >= k]
        stages.append(AtomicStage(stage_upstream, stage_downstream))
        stage_upstream = stage_downstream
    stage_downstream = list(downstream_values)
    stages.append(AtomicStage(stage_upstream, stage_downstream))
    # stack inter-stage values for more efficient halo exchange
    for k in range(num_stages - 1):
        stages[k] = stack_downstream(stages[k])
    for k in range(1, num_stages):
        stages[k] = stack_upstream(stages[k])
    if verbose == 'visualize':
        for k, s in enumerate(stages):
            visualize_graph('decomp_{0}.gv'.format(k),
                            s.upstream_values, s.downstream_values, False, k)
    return stages

# ---------------------------------------------------------------------------- #

def decompose_function(func, inputs, verbose=True):
    if not isinstance(inputs, (tuple, list)):
        inputs = (inputs,)

    def _tidy_input(inp):
        if hasattr(inp, 'shape'):
            return stencil_array(inp.shape)
        else:
            return stencil_array(np.array(inp).shape)

    inputs = tuple(map(_tidy_input, inputs))
    upstream_values = tuple(inp.value for inp in inputs)
    outputs = func(*inputs)
    if not isinstance(outputs, tuple):
        outputs = (outputs,)
    downstream_values = tuple(out.value for out in outputs)
    return decompose(upstream_values, downstream_values, verbose)


# ============================================================================ #
#                                atomic stage                                  #
# ============================================================================ #

def discover_values(upstream_values, downstream_values):
    discovered_values = []
    discovered_triburary_values = []
    def discover_values_from(v):
        if not hasattr(v, 'owner'):
            return
        if v in upstream_values:
            return
        if v.owner is None:
            if v not in discovered_triburary_values:
                discovered_triburary_values.append(v)
        elif v not in discovered_values:
            discovered_values.append(v)
            for v_inp in v.owner.inputs:
                discover_values_from(v_inp)
    for v in downstream_values:
        discover_values_from(v)
    return discovered_values, discovered_triburary_values

def sort_values(sorted_values, unsorted_values):
    def is_computable(v):
        return (not _is_like_sa_value(v) or
                v in sorted_values or
                v.owner is None)
    while len(unsorted_values):
        removed_any = False
        for v in unsorted_values:
            if all([is_computable(v_inp) for v_inp in v.owner.inputs]):
                unsorted_values.remove(v)
                sorted_values.append(v)
                removed_any = True
        if not removed_any:
            return

class AtomicStage(object):
    def __init__(self, upstream_values, downstream_values):
        sorted_values = copymodule.copy(upstream_values)
        unsorted_values, self.triburary_values = discover_values(
                upstream_values, downstream_values)
        sort_values(sorted_values, unsorted_values)
        assert unsorted_values == []
        self.upstream_values = sorted_values[:len(upstream_values)]
        self.sorted_values = sorted_values[len(upstream_values):]
        self.downstream_values = copymodule.copy(downstream_values)

    def __call__(self, upstream_values, triburary_values=[]):
        upstream_values = list(upstream_values)
        triburary_values = list(triburary_values)
        # _tmp attributes are assigned to inputs
        values = self.upstream_values + self.triburary_values
        tmp_values = upstream_values + triburary_values
        assert len(values) == len(tmp_values)
        for v, v_tmp in zip(values, tmp_values):
            assert not hasattr(v, '_tmp')
            v._tmp = v_tmp
        # _tmp attributes are computed to each value
        _tmp = lambda v : v._tmp if _is_like_sa_value(v) else v
        for v in self.sorted_values:
            assert not hasattr(v, '_tmp')
            inputs_tmp = [_tmp(v_inp) for v_inp in v.owner.inputs]
            v._tmp = v.owner.perform(inputs_tmp)
        # _tmp attributes are extracted from outputs then deleted from all
        downstream_values = tuple(v._tmp for v in self.downstream_values)
        values += self.sorted_values
        for v in values:
            del v._tmp
        return downstream_values

def stack_upstream(stage):
    upstream_total_size = builtins.sum(
            [v.size for v in stage.upstream_values])
    stacked_upstream_array = stencil_array((upstream_total_size,))
    stacked_upstream_value = stacked_upstream_array.value
    # split stacked upstream array
    upstream_arrays = []
    i_ptr = 0
    for v in stage.upstream_values:
        array_slice = stacked_upstream_array[i_ptr:i_ptr+v.size]
        upstream_arrays.append(array_slice.reshape(v.shape))
        i_ptr += v.size
    # construct stage based on stacked upstream values
    triburary_arrays = [stencil_array(v) for v in stage.triburary_values]
    downstream_arrays = stage(upstream_arrays, triburary_arrays)
    downstream_values = [a.value for a in downstream_arrays]
    return AtomicStage([stacked_upstream_value], downstream_values)

def stack_downstream(stage):
    downstream_total_size = builtins.sum(
            [v.size for v in stage.downstream_values])
    stacked_downstream_array = zeros((downstream_total_size,))
    i_ptr = 0
    for v in stage.downstream_values:
        downstream_array_slice = stencil_array(v).reshape((v.size,))
        stacked_downstream_array[i_ptr:i_ptr+v.size] = downstream_array_slice
        i_ptr += v.size
    return AtomicStage(stage.upstream_values, [stacked_downstream_array.value])

################################################################################
################################################################################
################################################################################
