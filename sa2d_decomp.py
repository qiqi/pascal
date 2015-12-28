# ============================================================================ #
#                                                                              #
#                    sa2d_decomp.py copyright(c) Qiqi Wang 2015                #
#                                                                              #
# ============================================================================ #

import copy
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
        a.owner is None or hasattr(a.owner, 'access_neighbor')
    else:
        return False


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
        assert(all(_is_like_sa(inp) for inp in inputs))

        self.operation = operation
        self.inputs = inputs

        produce_dummy = lambda a : dummy_func(a.shape) if _is_like_sa(a) else a
        dummy_inputs = tuple(produce_dummy(a) for a in inputs)
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
    def __init__(self, shape, owner):
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

    @property
    def x_p(self):
        return Op(lambda x : x.x_p, (self,), access_neighbor=True).output

    @property
    def x_m(self):
        return Op(lambda x : x.x_m, (self,), access_neighbor=True).output

    @property
    def y_p(self):
        return Op(lambda x : x.y_p, (self,), access_neighbor=True).output

    @property
    def y_m(self):
        return Op(lambda x : x.y_m, (self,), access_neighbor=True).output

    # ---------------------------- indexing ------------------------------- #

    def __getitem__(self, ind):
        return Op(lambda x : x[copy.copy(ind)], (self,)).output

    def __setitem__(self, ind, a):
        copied_self = copy.copy(self)
        if self.owner:
            self.owner.output = copied_self

        self.owner = Op(lambda x, a : x[ind] = a, (copied_self, a))
        self.shape = self.owner.result.shape
        self.owner.output = self


# ============================================================================ #
#                             data transformations                             #
# ============================================================================ #

def transpose(x, axes=None):
    mod = x._module
    return Op(lambda x : mod.transpose(x, copy.copy(axes))).output

def reshape(x, shape):
    mod = x._module
    return Op(lambda x : mod.reshape(x, copy.copy(shape))).output

def roll(x, shift, axis=None):
    mod = x._module
    shift, axis = copy.copy(shift), copy.copy(axis)
    return Op(lambda x : mod.roll(x, shift, axis)).output

def copy(a):
    mod = x._module
    return Op(lambda x : mod.copy(x, copy.copy(shape))).output


# ============================================================================ #
#                            mathematical functions                            #
# ============================================================================ #

def sin(a):
    mod = x._module
    return Op(lambda x : mod.sin(x)).output

def cos(a):
    mod = x._module
    return Op(lambda x : mod.cos(x)).output

def exp(a):
    mod = x._module
    return Op(lambda x : mod.exp(x)).output

def sum(a, axis=None):
    pass #TODO

def mean(a, axis=None):
    pass #TODO

# ============================================================================ #
#                              source sa arrays                                #
# ============================================================================ #

i = stencil_array((), None)
j = stencil_array((), None)
_zero = stencil_array((), None)

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
        self.outputs = func(self.inputs)

        if not isinstance(self.outputs, tuple):
            self.outputs = (self.outputs,)

    # --------------------------------------------------------------------- #

    def _assign_id_to_variables(self):
        self.variables = []
        def set_variable_id(a):
            assert _is_like_sa(a)
            if not hasattr(a, '_variableId'):
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
            A_eq.append(hstack([Ac, Ak, Ag]))
            b_eq.append(b)

        def add_lt(A_c, A_k, A_g, A_K, b):
            A_lt.append(hstack([Ac, Ak, Ag]))
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

            if a.onwer:
                for b in a.owner.inputs:
                    j = b._variableId
                    add_lt(e[j] - e[i], z, z, 0, 0)
                    add_lt(e[i], -e[j], z, 0, 0)
                    if a.owner.access_neighbor:
                        add_lt(e[j] - e[i], z, e[j] - e[i], 0, -1)
                    else:
                        add_lt(e[j] - e[i], z, e[j] - e[i], 0, 0)
                if a.owner.access_neighbor:
                    add_eq(z, z, e[i], 0, 1)

        w = [a.size for a in self.variables]
        c = np.hstack([-w, w, z, 0])

        self._linear_program = c, A_eq, A_lt, b_eq, b_lt

    # --------------------------------------------------------------------- #

    def _solve_linear_program(self):
        c, A_eq, A_lt, b_eq, b_lt = self._linear_program
        self._linear_program_result = \
                scipy.optimize.linprog(c, A_lt, b_lt, A_eq, b_eq)
        assert self._linear_program_result.sucess

    # --------------------------------------------------------------------- #

    def _assign_lp_results_to_vars(self):
        self.numStages = self._linear_program_result.x[-1] + 1
        c, k, g = self._linear_program_result.x[:-1].reshape([3,-1])
        assert c.size == len(self.variables)
        for i, a in enumerate(self.variables):
            a = self.variables[i]
            a.createStage = c[i]
            a.killStage = k[i]
            a.hasNeighbor = (g[i] == 0)

    # --------------------------------------------------------------------- #

    def __init__(self, func, inputs):
        self._build_computational_graph(func, inputs)
        self._assign_id_to_variables()
        self._build_linear_program()
        self._solve_linear_program()
        self._assign_lp_results_to_vars()

        self.stages = [Stage(self.variables, self.inputs, self.outputs, k) \
                       for k in range(self.numStages)]

    # --------------------------------------------------------------------- #

    def __iter__(self):
        for s in self.stages:
            yield s


# ============================================================================ #
#                                atomic stage                                  #
# ============================================================================ #

class Stage(object):
    def __init__(self, variables, globalInputs, globalOutputs, k):
        assert k >= 0 and k < self.numStages

        isIn = lambda a : a.createStage < k and a.killStage >= k
        isOut = lambda a : a.createStage <= k and a.killStage > k

        self.inputs = tuple(filter(isIn, variables)) \
            if k > 0 else globalInputs
        self.outputs = tuple(filter(isOut, variables)) \
            if k < self.numStages - 1 else globalOutputs

        isK = lambda a : a.createStage == k and a.owner
        remainingVariables = list(filter(isK, variables))
        self.orderedVariables = []
        while remainingVariables:
            numRemoved = 0
            for a in remainingVariables:
                if all(b in self.orderedVariables or b in self.inputs \
                       or b in source_arrays for b in a.owner.inputs):
                    self.orderedVariables.append(a)
                    remainingVariables.remove(a)
                    numRemoved += 1
            assert numRemoved > 0

    # --------------------------------------------------------------------- #

    def __call__(self, input_objects, source_objects):
        assert len(inputs) == len(self.inputs)
        for a, a_obj in zip(self.inputs, input_objects):
            assert not hasattr(a, '_obj')
            a._obj = a_obj

        for a, a_obj in zip(source_arrays, source_objects):
            assert not hasattr(a, '_obj')
            a._obj = a_obj

        for a in self.orderedVariables:
            assert not hasattr(a, '_obj')
            assert all(hasattr(b, '_obj') for b in a.owner.inputs)
            input_objects = tuple(b._obj for b in a.owner.inputs)
            a._obj = a.onwer.perform(input_objects)

        assert all(hasattr(a, '_obj') for a in self.outputs)
        output_objects = tuple(a._obj for a in self.outputs)

        for a in self.inputs:
            del a._obj
        for a in source_objects:
            del a._obj
        for a in self.orderedVariables:
            del a._obj

        return output_objects


# ============================================================================ #
#                                 unit tests                                   #
# ============================================================================ #

class TestOperators(unittest.TestCase):
    pass

# ============================================================================ #
#                                                                              #
# ============================================================================ #

if __name__ == '__main__':
    def heat(u):
        dx, dt = 0.1, 0.05
        return u + dt * (u.x_m + u.x_p - 2 * u) / dx**2

    heatStages = decompose(heat)
    # unittest.main()

################################################################################
################################################################################
################################################################################
