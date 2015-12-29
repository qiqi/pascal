# ============================================================================ #
#                                                                              #
#                    sa2d_decomp.py copyright(c) Qiqi Wang 2015                #
#                                                                              #
# ============================================================================ #

import copy as copymodule
import unittest
import operator
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


def _infer_module(a):
    if isinstance(a, np.ndarray):
        return np
    else:
        return a._module


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
                 dummy_func=np.ones):
        self.operation = operation
        self.inputs = copymodule.copy(tuple(inputs))

        produce_dummy = lambda a : dummy_func(a.shape) if _is_like_sa(a) else a
        dummy_inputs = tuple(produce_dummy(a) for a in self.inputs)
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
        return self.shape[0]

    # --------------------------- operations ------------------------------ #

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

    def __div__(self, a):
        return self.__truediv__(a)

    def __rdiv__(self, a):
        return self.__rtruediv__(a)

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

        self.owner = Op(lambda x, a : x.__setitem__(ind, a), (copied_self, a))
        self.shape = self.owner.result.shape
        self.owner.output = self


# ============================================================================ #
#                             data transformations                             #
# ============================================================================ #

def transpose(x, axes=None):
    axes = copymodule.copy(axes)
    return Op(lambda x : _infer_module(x).transpose(x, axes)).output

def reshape(x, shape):
    shape = copymodule.copy(shape)
    return Op(lambda x : _infer_module(x).reshape(x, shape)).output

def roll(x, shift, axis=None):
    shift, axis = copymodule.copy(shift), copymodule.copy(axis)
    return Op(lambda x : _infer_module(x).roll(x, shift, axis)).output

def copy(a):
    shape = copymodule.copy(shape)
    return Op(lambda x : _infer_module(x).copy(x, shape)).output


# ============================================================================ #
#                            mathematical functions                            #
# ============================================================================ #

def sin(a):
    return Op(lambda x : _infer_module(x).sin(x), (a,)).output

def cos(a):
    mod = a._module
    return Op(lambda x : _infer_module(x).cos(x), (a,)).output

def exp(a):
    mod = a._module
    return Op(lambda x : _infer_module(x).exp(x), (a,)).output

def sum(a, axis=None):
    pass #TODO

def mean(a, axis=None):
    pass #TODO

# ============================================================================ #
#                              source sa arrays                                #
# ============================================================================ #

i = stencil_array()
j = stencil_array()
_zero = stencil_array()

source_arrays = (i, j, _zero)

def ones(shape=()):
    return _zero + np.ones(shape)

def zeros(shape=()):
    return _zero + np.zeros(shape)

# ============================================================================ #
#                                decomposition                                 #
# ============================================================================ #

class decompose(object):
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
        A_eq, A_lt, b_eq, b_lt = [], [], [], []

        def add_eq(A_c, A_k, A_g, A_K, b):
            A_eq.append(hstack([A_c, A_k, A_g, A_K]))
            b_eq.append(b)

        def add_lt(A_c, A_k, A_g, A_K, b):
            A_lt.append(hstack([A_c, A_k, A_g, A_K]))
            b_lt.append(b)

        # build constraints
        n = len(self.variables)
        z = np.zeros(n)
        e = np.eye(n)

        for a in self.inputs:
            i = a._variableId
            add_eq(e[i], z, z, 0, 0)

        for a in self.outputs:
            i = a._variableId
            add_eq(z, e[i], z, -1, 0)

        for a in self.variables:
            i = a._variableId
            add_lt(e[i], -e[i], z, 0, 0)
            add_lt(z, z, -e[i], 0, 0)
            add_lt(z, z, e[i], 0, 1)

            if a.owner:
                for b in a.owner.inputs:
                    if _is_like_sa(b):
                        j = b._variableId
                        add_lt(e[j] - e[i], z, z, 0, 0)
                        add_lt(e[i], -e[j], z, 0, 0)
                        if a.owner.access_neighbor:
                            add_lt(e[j] - e[i], z, e[j] - e[i], 0, -1)
                        else:
                            add_lt(e[j] - e[i], z, e[j] - e[i], 0, 0)
                if a.owner.access_neighbor:
                    add_eq(z, z, e[i], 0, 1)

        w = np.array([a.size for a in self.variables])
        c = np.hstack([-w, w, z, 0])

        self._linear_program = c, A_eq, A_lt, b_eq, b_lt

    # --------------------------------------------------------------------- #

    def _solve_linear_program(self):
        c, A_eq, A_lt, b_eq, b_lt = self._linear_program
        self._linear_program_result = \
                scipy.optimize.linprog(c, A_lt, b_lt, A_eq, b_eq)
        assert self._linear_program_result.success

    # --------------------------------------------------------------------- #

    def _assign_lp_results_to_vars(self):
        self.numStages = int(self._linear_program_result.x[-1]) + 1
        c, k, g = self._linear_program_result.x[:-1].reshape([3,-1])
        assert c.size == len(self.variables)
        for i, a in enumerate(self.variables):
            a = self.variables[i]
            a.createStage = c[i]
            a.killStage = k[i]
            a.hasNeighbor = (g[i] == 0)

    # --------------------------------------------------------------------- #

    def __init__(self, func, inputs, source_objects):
        self._build_computational_graph(func, inputs)
        self._assign_id_to_variables()
        self._build_linear_program()
        self._solve_linear_program()
        self._assign_lp_results_to_vars()

        self.stages = [Stage(self.variables, self.inputs, self.outputs,
                             k, self.numStages, source_objects) \
                       for k in range(self.numStages)]

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
    def __init__(self, variables, globalInputs, globalOutputs,
            k, K, source_objects):
        assert k >= 0 and k < K
        assert len(source_objects) == len(source_arrays)

        self.source_objects = tuple(source_objects)

        isIn = lambda a : a.createStage < k and a.killStage >= k
        isOut = lambda a : a.createStage <= k and a.killStage > k

        self.inputs = tuple(filter(isIn, variables)) \
            if k > 0 else globalInputs
        self.outputs = tuple(filter(isOut, variables)) \
            if k < K - 1 else globalOutputs

        isK = lambda a : a.createStage == k and a.owner
        remainingVariables = list(filter(isK, variables))
        self.orderedVariables = []
        while remainingVariables:
            numRemoved = 0
            for a in remainingVariables:
                isReady = lambda b : b in self.orderedVariables or \
                                     b in self.inputs or \
                                     b in source_arrays
                if all([isReady(b) for b in a.owner.inputs if _is_like_sa(b)]):
                    self.orderedVariables.append(a)
                    remainingVariables.remove(a)
                    numRemoved += 1
            assert numRemoved > 0

    # --------------------------------------------------------------------- #

    def __call__(self, input_objects):
        assert len(input_objects) == len(self.inputs)
        for a, a_obj in zip(self.inputs, input_objects):
            assert not hasattr(a, '_obj')
            a._obj = a_obj

        for a, a_obj in zip(source_arrays, self.source_objects):
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

        for a in filter(_is_like_sa, self.inputs):
            del a._obj
        for a in source_arrays:
            del a._obj
        for a in self.orderedVariables:
            del a._obj

        return output_objects


#==============================================================================#
#                           replace numpy operations                           #
#==============================================================================#

def add(x1, x2, out=None):
    if _is_like_sa(x2):
        return x2.__add__(x1)
    else:
        return np.add(x1, x2, out)

def subtract(x1, x2, out=None):
    if _is_like_sa(x2):
        return (-x2).__add__(x1)
    else:
        return np.subtract(x1, x2, out)

def multiply(x1, x2, out=None):
    if _is_like_sa(x2):
        return x2.__mul__(x1)
    else:
        return np.multiply(x1, x2, out)

def true_divide(x1, x2, out=None):
    if _is_like_sa(x2):
        return (1.0 / x2).__mul__(x1)
    else:
        return np.true_divide(x1, x2, out)

if np.set_numeric_ops()['add'] == np.add:
    np.set_numeric_ops(add=add)
if np.set_numeric_ops()['subtract'] == np.subtract:
    np.set_numeric_ops(subtract=subtract)
if np.set_numeric_ops()['multiply'] == np.multiply:
    np.set_numeric_ops(multiply=multiply)
if np.set_numeric_ops()['true_divide'] == np.true_divide:
    np.set_numeric_ops(divide=true_divide)
    np.set_numeric_ops(true_divide=true_divide)


# ============================================================================ #
#                                 unit tests                                   #
# ============================================================================ #

class TestSingleStage(unittest.TestCase):
    def testHeat(self):
        def heat(u):
            dx, dt = 0.1, 0.01
            return u + dt * (u.x_m + u.x_p + u.y_m + u.y_p - 4 * u) / dx**2

        Ni, Nj = 16, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        heatStages = decompose(heat, stencil_array(),
                source_objects=(G.i, G.j, G.zeros(())))

        self.assertEquals(len(heatStages), 1)
        stage0 = heatStages[0]

        u0 = G.ones(())
        result = stage0((u0,))
        self.assertEquals(len(result), 1)
        result = result[0]
        err = result - 1
        self.assertAlmostEqual(0, G.reduce_sum(err**2))

        u0 = G.sin(G.i / Ni * np.pi * 2)
        result = stage0((u0,))
        self.assertEquals(len(result), 1)
        result = result[0]
        err = result - u0 * (1 - 2 * (1 - np.cos(np.pi * 2 / Ni)))
        self.assertAlmostEqual(0, G.reduce_sum(err**2))

        u0 = G.sin(G.j / Nj * np.pi * 4)
        result = stage0((u0,))
        self.assertEquals(len(result), 1)
        result = result[0]
        err = result - u0 * (1 - 2 * (1 - np.cos(np.pi * 4 / Nj)))
        self.assertAlmostEqual(0, G.reduce_sum(err**2))

    def testODE(self):
        def ode(u):
            dt = 0.1
            return u - dt * sin(u)

        Ni, Nj = 4, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        odeStages = decompose(ode, stencil_array(),
                source_objects=(G.i, G.j, G.zeros(())))

        self.assertEquals(len(odeStages), 1)
        stage0 = odeStages[0]

        u0 = G.i
        result = stage0((u0,))
        self.assertEquals(len(result), 1)
        result = result[0]
        err = result - (G.i - 0.1 * G.sin(G.i))
        self.assertAlmostEqual(0, G.reduce_sum(err**2))


class TestTwoStage(unittest.TestCase):
    def testHeat(self):
        def heatMidpoint(u):
            dx, dt = 0.1, 0.01
            uh = u + 0.5 * dt * (u.x_m + u.x_p + u.y_m + u.y_p - 4 * u) / dx**2
            return u + dt * (uh.x_m + uh.x_p + uh.y_m + uh.y_p - 4 * uh) / dx**2

        Ni, Nj = 16, 8
        G = sa2d_single_thread.grid2d(Ni, Nj)
        heatStages = decompose(heatMidpoint, stencil_array(),
                source_objects=(G.i, G.j, G.zeros(())))

        self.assertEquals(len(heatStages), 2)
        stage0, stage1 = heatStages

        u0 = G.sin(G.i / Ni * np.pi * 2)
        result = stage1(stage0((u0,)))
        self.assertEquals(len(result), 1)
        result = result[0]

        dudt = 2 * (1 - np.cos(np.pi * 2 / Ni))
        err = result - u0 * (1 - dudt + dudt**2 / 2)
        self.assertAlmostEqual(G.reduce_sum(err**2), 0)

# ============================================================================ #
#                                                                              #
# ============================================================================ #

if __name__ == '__main__':
    import sa2d_single_thread

    unittest.main()

################################################################################
################################################################################
################################################################################
