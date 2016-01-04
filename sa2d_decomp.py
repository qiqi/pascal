# ============================================================================ #
#                                                                              #
#                    sa2d_decomp.py copyright(c) Qiqi Wang 2015                #
#                                                                              #
# ============================================================================ #

from __future__ import division

import copy as copymodule
import sys
import pickle
import unittest
import operator
import collections
import numpy as np
import theano
import theano.tensor as T
import scipy.optimize


# ============================================================================ #

def _is_like_sa(a):
    '''
    Check attributes of stencil array object
    '''
    if hasattr(a, 'owner'):
        return a.owner is None or hasattr(a.owner, 'access_neighbor')
    else:
        return False


def _infer_context(a):
    if isinstance(a, np.ndarray):
        return np
    else:
        return a.__context__


# ============================================================================ #
#                                  Op  class                                   #
# ============================================================================ #

class Op(object):
    '''
    Perform operations between arrays, and remember whether the operation
    accesses grid neighbors

    Op(operation, inputs)
        operation: a function that takes a list of inputs as arguments
        inputs: a list of stencil array
    '''
    def __init__(self, operation, inputs, access_neighbor=False,
                 dummy_func=np.ones, shape=None):
        self.operation = operation
        self.inputs = copymodule.copy(tuple(inputs))

        produce_dummy = lambda a : dummy_func(a.shape) if _is_like_sa(a) else a
        dummy_inputs = tuple(produce_dummy(a) for a in self.inputs)
        if shape is None:
            shape = operation(*dummy_inputs).shape

        self.access_neighbor = access_neighbor
        self.output = stencil_array(shape, self)

    def perform(self, input_objects):
        assert len(input_objects) == len(self.inputs)
        return self.operation(*input_objects)


# ============================================================================ #
#                             stencil_array class                              #
# ============================================================================ #

class stencil_array(object):
    def __init__(self, shape=(), owner=None):
        self.shape = tuple(shape)
        self.owner = owner

    # --------------------------- properties ------------------------------ #

    @property
    def ndim(self):
        return len(self.shape)

    @property
    def size(self):
        return np.prod(self.shape)

    def __len__(self):
        return 1 if not self.shape else self.shape[0]

    # --------------------------- operations ------------------------------ #

    # asks ndarray to use the __rops__ defined in this class
    __array_priority__ = 100

    def __add__(self, a):
        return Op(operator.add, (self, a)).output

    def __radd__(self, a):
        return Op(operator.add, (a, self)).output

    def __sub__(self, a):
        return Op(operator.sub, (self, a)).output

    def __rsub__(self, a):
        return Op(operator.sub, (a, self)).output

    def __mul__(self, a):
        return Op(operator.mul, (self, a)).output

    def __rmul__(self, a):
        return Op(operator.mul, (a, self)).output

    def __truediv__(self, a):
        return Op(operator.truediv, (self, a)).output

    def __rtruediv__(self, a):
        return Op(operator.truediv, (a, self)).output

    def __pow__(self, a):
        return Op(operator.pow, (self, a)).output

    def __rpow__(self, a):
        return Op(operator.pow, (a, self)).output

    def __neg__(self):
        return Op(operator.neg, (self,)).output

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
            self.x_p = self
            self.x_m = self
            self.y_p = self
            self.y_m = self

    @property
    def x_p(self):
        return Op(lambda x : x.x_p, (self,), access_neighbor=True,
                  dummy_func=self.dummy_func).output

    @property
    def x_m(self):
        return Op(lambda x : x.x_m, (self,), access_neighbor=True,
                  dummy_func=self.dummy_func).output

    @property
    def y_p(self):
        return Op(lambda x : x.y_p, (self,), access_neighbor=True,
                  dummy_func=self.dummy_func).output

    @property
    def y_m(self):
        return Op(lambda x : x.y_m, (self,), access_neighbor=True,
                  dummy_func=self.dummy_func).output

    # ---------------------------- indexing ------------------------------- #

    def __getitem__(self, ind):
        return Op(lambda x : x[copymodule.copy(ind)], (self,)).output

    def __setitem__(self, ind, a):
        copied_self = copymodule.copy(self)
        if self.owner:
            self.owner.output = copied_self

        ind = copymodule.copy(ind)
        def op(x, a):
            x = copymodule.copy(x)
            print(ind, x.shape, a.shape)
            x[ind] = a
            return x
        self.owner = Op(op, (copied_self, a), shape=self.shape)
        self.owner.output = self


# ============================================================================ #
#                             data transformations                             #
# ============================================================================ #

def transpose(x, axes=None):
    axes = copymodule.copy(axes)
    op = lambda x : x.transpose(axes)
    return Op(op, (x,)).output

def reshape(x, shape):
    shape = copymodule.copy(shape)
    op = lambda x : x.reshape(shape)
    return Op(op, (x,)).output

def roll(x, shift, axis=None):
    shift, axis = copymodule.copy(shift), copymodule.copy(axis)
    op = lambda x : _infer_context(x).roll(x, shift, axis)
    return Op(op, (x,)).output

def copy(x):
    op = lambda x : x.copy()
    return Op(op, (x,)).output


# ============================================================================ #
#                            mathematical functions                            #
# ============================================================================ #

def sin(a):
    return Op(lambda x : _infer_context(x).sin(x), (a,)).output

def cos(a):
    return Op(lambda x : _infer_context(x).cos(x), (a,)).output

def exp(a):
    return Op(lambda x : _infer_context(x).exp(x), (a,)).output

def sum(a, axis=None):
    axis = copymodule.copy(axis)
    return Op(lambda x : _infer_context(x).sum(x, axis), (a,)).output

def mean(a, axis=None):
    axis = copymodule.copy(axis)
    return Op(lambda x : _infer_context(x).mean(x, axis), (a,)).output

# ============================================================================ #
#                             built-in source array                            #
# ============================================================================ #

_zero = stencil_array()

def ones(shape=()):
    return _zero + np.ones(shape)

def zeros(shape=()):
    return _zero + np.zeros(shape)

# ============================================================================ #
#                                decomposition                                 #
# ============================================================================ #

class decompose(object):
    '''
    '''
    # TODO: Add comments
    def _build_computational_graph(self, func, inputs):
        if not isinstance(inputs, tuple):
            inputs = (inputs,)

        def _tidy_input(inp):
            if hasattr(inp, 'shape'):
                return stencil_array(inp.shape, None)
            else:
                return stencil_array(np.array(inp).shape, None)

        self.inputs = tuple(map(_tidy_input, inputs))
        self.outputs = func(*self.inputs)

        if not isinstance(self.outputs, tuple):
            self.outputs = (self.outputs,)

    # --------------------------------------------------------------------- #

    def _assign_id_to_variables(self):
        self.variables = []
        def set_variable_id(a):
            if _is_like_sa(a) and not hasattr(a, '_variableId'):
                a._variableId = len(self.variables)
                self.variables.append(a)
                if a.owner:
                    for inp in a.owner.inputs:
                        set_variable_id(inp)
        for out in self.outputs:
            set_variable_id(out)

    # --------------------------------------------------------------------- #

    def _build_linear_program(self):
        '''
        solution: [c, k, g, K]
        c: length n array of integers, the stage in which a variable is created;
        k: length n array of integers, the stage in which a variable is killed;
        g: length n array of 0 and 1's, bareness of array,
           1 indicating it is bare, i.e, has no neighbors upon creation;
           0 indicating it has one layer of neighbor upon creation.
        '''
        A_eq, A_lt, b_eq, b_lt = [], [], [], []

        def add_eq(A_c, A_k, A_g, A_K, b):
            A_eq.append(np.hstack([A_c, A_k, A_g, A_K]))
            b_eq.append(b)

        def add_lt(A_c, A_k, A_g, A_K, b):
            A_lt.append(np.hstack([A_c, A_k, A_g, A_K]))
            b_lt.append(b)

        n = len(self.variables)

        # build bounds
        bounds = [(0, None)] * (2 * n) + [(0, 1)] * n + [(0, None)]

        # build constraints
        z = np.zeros(n)
        e = np.eye(n)

        for a in self.inputs:
            i = a._variableId
            # an input variable is born at Stage 0
            add_eq(e[i], z, z, 0, 0)

        for a in self.outputs:
            i = a._variableId
            # an output variable is killed at Stage K (last stage)
            add_eq(z, e[i], z, -1, 0)

        for a in self.variables:
            i = a._variableId
            # a variable cannot be killed before it is born
            add_lt(e[i], -e[i], z, 0, 0)

            if a.owner:
                for b in a.owner.inputs:
                    if _is_like_sa(b):
                        j = b._variableId
                        # a child cannot be born before its parent is born
                        add_lt(e[j] - e[i], z, z, 0, 0)
                        # a child cannot be born after its parent is killed
                        add_lt(e[i], -e[j], z, 0, 0)
                        if a.owner.access_neighbor:
                            # a bare parent must wait to next stage
                            # to produce any child through neibhor access
                            add_lt(e[j] - e[i], z, e[j] - e[i], 0, -1)
                        else:
                            # a bare parent produces bare children
                            # during its creating stage
                            add_lt(e[j] - e[i], z, e[j] - e[i], 0, 0)
                if a.owner.access_neighbor:
                    # a child born through neighbor access is bare
                    add_eq(z, z, e[i], 0, 1)

        w = np.array([a.size for a in self.variables])
        c = np.hstack([-w, w, z, 0])

        LP = collections.namedtuple('LP', 'c, bounds, A_eq, A_lt, b_eq, b_lt')
        self._linear_program = LP(c, bounds, A_eq, A_lt, b_eq, b_lt)

    # --------------------------------------------------------------------- #

    def _solve_linear_program(self, verbose):
        c, bounds, A_eq, A_lt, b_eq, b_lt = self._linear_program

        if verbose:
            lp = self._linear_program
            lpSize = len(lp.c), len(lp.b_eq) + len(lp.b_lt)
            print('\nDecomposing update formula')
            print('\t{0} variables'.format(len(self.variables)))
            print('\tsolving {0}x{1} linear program'.format(*lpSize))
            sys.stdout.flush()

        opt = {'maxiter': 20000}
        sol = scipy.optimize.linprog(
                c, A_lt, b_lt, A_eq, b_eq, bounds=bounds, options=opt)

        assert all([abs(xi - round(xi)) < 1E-12 for xi in sol.x]), \
               'Linear Program Finished with non-integer results'
        self._linear_program_result = sol

        if verbose:
            K = int(round(sol.x[-1]))
            objective = int(round(np.dot(lp.c, sol.x)))
            print('Decomposed into {0} atomic stages'.format(K+1))
            status = ['Optimality achieved', 'Max iteration reached',
                      'Problem seems infeasible', 'Problems seems unbounded']
            print('\tStatus: ' + status[sol.status])
            print('\tobjective function = {0}'.format(objective))
            print('\tafter {0} iterations'.format(sol.nit))
            sys.stdout.flush()

    # --------------------------------------------------------------------- #

    def _assign_lp_results_to_vars(self):
        self.numStages = int(self._linear_program_result.x[-1]) + 1
        c, k, g = self._linear_program_result.x[:-1].reshape([3,-1])
        assert c.size == len(self.variables)

        for i, a in enumerate(self.variables):
            a = self.variables[i]
            a.createStage = int(round(c[i]))
            a.killStage = int(round(k[i]))
            a.hasNeighbor = (round(g[i]) == 0)

    # --------------------------------------------------------------------- #

    def __init__(self, func, inputs, verbose=True):
        self._build_computational_graph(func, inputs)
        self._assign_id_to_variables()
        self._build_linear_program()
        self._solve_linear_program(verbose)
        self._assign_lp_results_to_vars()

        self.stages = [Stage(self.variables, self.inputs, self.outputs,
                             k, self.numStages) for k in range(self.numStages)]

    # --------------------------------------------------------------------- #

    def __len__(self):
        return len(self.stages)

    def __iter__(self):
        for s in self.stages:
            yield s

    def __getitem__(self, i):
        return self.stages[i]


# ============================================================================ #
#                                atomic stage                                  #
# ============================================================================ #

class Stage(object):
    def __init__(self, variables, globalInputs, globalOutputs, k, K):
        assert k >= 0 and k < K

        isIn = lambda a : a.createStage < k and a.killStage >= k
        isOut = lambda a : a.createStage <= k and a.killStage > k

        self.inputs = tuple(filter(isIn, variables)) \
            if k > 0 else globalInputs
        self.outputs = tuple(filter(isOut, variables)) \
            if k < K - 1 else globalOutputs

        isKSource = lambda a : a.createStage == k and a.owner is None and \
                               a not in globalInputs
        self.sourceVariables = tuple(filter(isKSource, variables))

        isKVar = lambda a : a.createStage == k and a.owner is not None
        self._order_variables(list(filter(isKVar, variables)))

    def _order_variables(self, stage_k_variables):
        self.orderedVariables = []
        while stage_k_variables:
            numRemoved = 0
            for a in stage_k_variables:
                isReady = lambda b : b in self.orderedVariables or \
                                     b in self.inputs or \
                                     b in self.sourceVariables
                if all([isReady(b) for b in a.owner.inputs if _is_like_sa(b)]):
                    self.orderedVariables.append(a)
                    stage_k_variables.remove(a)
                    numRemoved += 1
            assert numRemoved > 0

    # --------------------------------------------------------------------- #

    def __call__(self, input_objects, source_objects=()):
        assert len(input_objects) == len(self.inputs)
        for a, a_obj in zip(self.inputs, input_objects):
            assert not hasattr(a, '_obj')
            a._obj = a_obj

        assert len(source_objects) == len(self.sourceVariables)
        for a, a_obj in zip(self.sourceVariables, source_objects):
            assert not hasattr(a, '_obj')
            a._obj = a_obj

        for a in self.orderedVariables:
            assert not hasattr(a, '_obj')
            assert all([hasattr(b, '_obj') for b in a.owner.inputs \
                        if _is_like_sa(b)])
            extract_obj = lambda b : b._obj if _is_like_sa(b) else b
            input_objects = tuple(extract_obj(b) for b in a.owner.inputs)
            a._obj = a.owner.perform(input_objects)

        assert all([hasattr(a, '_obj') for a in self.outputs])
        output_objects = tuple(a._obj for a in self.outputs)

        for a in self.inputs:
            del a._obj
        for a in self.sourceVariables:
            del a._obj
        for a in self.orderedVariables:
            del a._obj

        return output_objects


# ============================================================================ #
#                                 unit tests                                   #
# ============================================================================ #

class TestSimpleUpdates(unittest.TestCase):
    def test1(self):
        def update(u):
            return u.ndim + 2**u

        Ni, Nj = 4, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        stages = decompose(update, stencil_array())

        self.assertEqual(len(stages), 1)
        stage0 = stages[0]

        u0 = G.i
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - 2**u0
        self.assertAlmostEqual(0, G.reduce_sum(err**2))

    def test2(self):
        def update(u):
            return u.size - 1 / (-u)**3 * 2

        Ni, Nj = 4, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        stages = decompose(update, stencil_array((2,)))

        self.assertEqual(len(stages), 1)
        stage0 = stages[0]

        u0 = G.i + G.ones(2)
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - (2 + 2 / u0**3)
        self.assertAlmostEqual(0, G.reduce_sum((err**2).sum()))

    def testExpCopySumMean(self):
        def update(u):
            return exp(u).copy().sum(0).mean()

        Ni, Nj = 4, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        stages = decompose(update, stencil_array((2,3)))

        self.assertEqual(len(stages), 1)
        stage0 = stages[0]

        u0 = G.i + G.ones((2,3)) + np.arange(3)
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - G.exp(u0).sum(0).mean()
        self.assertAlmostEqual(0, G.reduce_sum((err**2).sum()))

    def testTransposeReshapeRoll(self):
        def update(u):
            return roll(u.transpose([1,0,2]).reshape([3,-1]).T, 1)

        Ni, Nj = 4, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        stages = decompose(update, stencil_array((2,3,4)))

        self.assertEqual(len(stages), 1)
        stage0 = stages[0]

        u0 = G.i + G.ones((2,3,4)) + np.arange(4)
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - G.roll(u0.transpose([1,0,2]).reshape([3,-1]).T, 1)
        self.assertAlmostEqual(0, G.reduce_sum((err**2).sum()))

    def testSetGetItem(self):
        def update(u):
            v = zeros([3,2])
            v[0] = ones(2)
            v[1,0] = u[0]
            v[2] = u.x_p + u.x_m - 2 * u
            return v

        Ni, Nj = 4, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        stages = decompose(update, [0,0])

        self.assertEqual(len(stages), 1)
        stage0 = stages[0]

        self.assertEqual(stage0.sourceVariables, (_zero,))
        source_objects = (G.zeros(()),)

        u0 = G.i + np.arange(2) * 8
        result = stage0((u0,), source_objects)
        self.assertEqual(len(result), 1)
        result = result[0]

        err_0 = result[0] - 1
        err_10 = result[1,0] - u0[0]
        err_11 = result[1,1]
        err_2 = result[2] - (u0.x_p + u0.x_m - 2 * u0)

        self.assertAlmostEqual(0, G.reduce_sum((err_0**2).sum()))
        self.assertAlmostEqual(0, G.reduce_sum((err_10**2).sum()))
        self.assertAlmostEqual(0, G.reduce_sum((err_11**2).sum()))
        self.assertAlmostEqual(0, G.reduce_sum((err_2**2).sum()))


# ============================================================================ #

class TestSingleStage(unittest.TestCase):
    def testHeat(self):
        def heat(u):
            dx, dt = 0.1, 0.01
            return u + dt * (u.x_m + u.x_p + u.y_m + u.y_p - 4 * u) / dx**2

        Ni, Nj = 16, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        heatStages = decompose(heat, stencil_array())

        self.assertEqual(len(heatStages), 1)
        stage0 = heatStages[0]

        u0 = G.ones(())
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - 1
        self.assertAlmostEqual(0, G.reduce_sum(err**2))

        u0 = G.sin(G.i / Ni * np.pi * 2)
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - u0 * (1 - 2 * (1 - np.cos(np.pi * 2 / Ni)))
        self.assertAlmostEqual(0, G.reduce_sum(err**2))

        u0 = G.sin(G.j / Nj * np.pi * 4)
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - u0 * (1 - 2 * (1 - np.cos(np.pi * 4 / Nj)))
        self.assertAlmostEqual(0, G.reduce_sum(err**2))

    def testODE1(self):
        def ode(u):
            dt = 0.1
            return u - dt * sin(u)

        Ni, Nj = 4, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        odeStages = decompose(ode, stencil_array())

        self.assertEqual(len(odeStages), 1)
        stage0 = odeStages[0]

        u0 = G.i
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - (G.i - 0.1 * G.sin(G.i))
        self.assertAlmostEqual(0, G.reduce_sum(err**2))

    def testODE2(self):
        def ode(u):
            dt = 0.1
            return u - dt * cos(u) / len(u)

        Ni, Nj = 4, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        odeStages = decompose(ode, stencil_array())

        self.assertEqual(len(odeStages), 1)
        stage0 = odeStages[0]

        u0 = G.i
        result = stage0((u0,))
        self.assertEqual(len(result), 1)
        result = result[0]
        err = result - (G.i - 0.1 * G.cos(G.i))
        self.assertAlmostEqual(0, G.reduce_sum(err**2))


# ============================================================================ #

class TestMultiStage(unittest.TestCase):
    def testHeat(self):
        def heatMidpoint(u):
            dx, dt = 0.1, 0.01
            uh = u + 0.5 * dt * (u.x_m + u.x_p + u.y_m + u.y_p - 4 * u) / dx**2
            return u + dt * (uh.x_m + uh.x_p + uh.y_m + uh.y_p - 4 * uh) / dx**2

        Ni, Nj = 16, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        heatStages = decompose(heatMidpoint, stencil_array())

        self.assertEqual(len(heatStages), 2)
        stage0, stage1 = heatStages

        u0 = G.sin(G.i / Ni * np.pi * 2)
        result = stage1(stage0((u0,)))
        self.assertEqual(len(result), 1)
        result = result[0]

        dudt = 2 * (1 - np.cos(np.pi * 2 / Ni))
        err = result - u0 * (1 - dudt + dudt**2 / 2)
        self.assertAlmostEqual(G.reduce_sum(err**2), 0)

    def testKuramotoSivashinskyRk4(self):
        def ks_dudt(u):
            dx = 0.1
            lu = (u.x_m + u.x_p + u.y_m + u.y_p - 4 * u) / dx**2
            llu = (lu.x_m + lu.x_p + lu.y_m + lu.y_p - 4 * u) / dx**2
            ux = (u.x_m - u.x_p) / dx
            return -llu - lu - ux * u

        def ks_rk4(u0):
            dt = 0.01
            du0 = dt * ks_dudt(u0)
            du1 = dt * ks_dudt(u0 + 0.5 * du0)
            du2 = dt * ks_dudt(u0 + 0.5 * du1)
            du3 = dt * ks_dudt(u0 + du2)
            return u0 + (du0 + 2 * du1 + 2 * du2 + du3) / 6

        Ni, Nj = 16, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        ksStages = decompose(ks_rk4, stencil_array())

        self.assertEqual(len(ksStages), 8)

        inp = (G.sin(G.i / Ni * np.pi * 2),)
        for i in range(8):
            inp = ksStages[i](inp)

        self.assertEqual(len(inp), 1)


# ============================================================================ #

class TestTheano(unittest.TestCase):
    @staticmethod
    def ij_np(i0, i1, j0, j1):
        return np.outer(np.arange(i0, i1), np.ones(j1 - j0, int)), \
               np.outer(np.ones(i1 - i0, int), np.arange(j0, j1))

    def testHeat(self):
        def heatMidpoint(u):
            dx, dt = 0.1, 0.01
            uh = u + 0.5 * dt * (u.x_m + u.x_p + u.y_m + u.y_p - 4 * u) / dx**2
            return u + dt * (uh.x_m + uh.x_p + uh.y_m + uh.y_p - 4 * uh) / dx**2

        import sa2d_theano
        heatStages = decompose(heatMidpoint, stencil_array())

        stage0, stage1 = heatStages

        Ni, Nj = 8, 8
        i, j = self.ij_np(-1, Ni+1, -1, Nj+1)
        u0 = np.sin(i / Ni * np.pi * 2)
        compiled_stage0 = sa2d_theano.compile(stage0, (u0,))
        stage0_out = compiled_stage0(u0)

        stage1_in = []
        for a, val in zip(stage0.outputs, stage0_out):
            if a.hasNeighbor:
                stage1_in.append(val)
            else:
                val_with_nbr = np.zeros((Ni + 2, Nj + 2) + val.shape[2:])
                val_with_nbr[1:-1,1:-1] = val
                val_with_nbr[0,1:-1] = val[-1,:]
                val_with_nbr[-1,1:-1] = val[0,:]
                val_with_nbr[1:-1,0] = val[:,-1]
                val_with_nbr[1:-1,-1] = val[:,0]
                stage1_in.append(val_with_nbr)

        stage1_in = tuple(stage1_in)
        compiled_stage1 = sa2d_theano.compile(stage1, stage1_in)
        stage1_out = compiled_stage1(*stage1_in)
        self.assertEqual(len(stage1_out), 1)
        u1 = stage1_out[0]

        dudt = 2 * (1 - np.cos(np.pi * 2 / Ni))
        err = u1 - u0[1:-1,1:-1] * (1 - dudt + dudt**2 / 2)

        self.assertAlmostEqual(0, np.abs(err).max())

# ============================================================================ #
#                                                                              #
# ============================================================================ #

if __name__ == '__main__':
    import sa2d_single_thread
    unittest.main()

################################################################################
################################################################################
################################################################################
