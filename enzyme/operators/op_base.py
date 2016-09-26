import copy
import string

import numpy as np

from enzyme.symbolic_value import _is_like_sa_value, symbolic_array_value

def infer_context(a):
    '''
    Infer the appropriate math function, e.g., sin, to call on a
    Usage: infer_context(a).sin(a)
    '''
    if isinstance(a, np.ndarray):
        return np
    else:
        return a.__context__


# ============================================================================ #
#                                   Op class                                   #
# ============================================================================ #

class OpBase(object):
    '''
    Perform operations between values, and remember whether the operation
    accesses grid neighbors

    Op(operation, inputs)
        operation: a function that takes a list of inputs as arguments
        inputs: a list of stencil array
    '''
    def __init__(self, py_operation, inputs, access_neighbor=False,
                 shape_keeper=np.ones, shape=None, name=None):
        self.py_operation = py_operation
        self.inputs = []
        for inp in inputs:
            if _is_like_sa_value(inp):
                self.inputs.append(inp)
            else:
                inp = np.array(inp, np.float64)
                #try:
                #except (IndexError, TypeError):
                #    pass
                self.inputs.append(inp)
        self.name = name

        def produce_shape_keepers(a):
            if _is_like_sa_value(a):
                return shape_keeper(a.shape)
            else:
                return np.array(a, np.float64)
        shape_keeper_inputs = tuple(map(produce_shape_keepers, self.inputs))
        if shape is None:
            shape = py_operation(*shape_keeper_inputs).shape

        self.access_neighbor = access_neighbor
        self.output = symbolic_array_value(shape, self)

    def perform(self, input_objects):
        assert len(input_objects) == len(self.inputs)
        return self.py_operation(*input_objects)

    def __repr__(self):
        return 'Operator {0}'.format(self.name)


def binary_op_indices(a, b, c):
    ind_a = np.ravel(np.arange(a.size).reshape(a.shape) +
                     np.zeros(b.shape, int))
    ind_b = np.ravel(np.zeros(a.shape, int) +
                     np.arange(b.size).reshape(b.shape))
    ind_c = np.arange(c.size)
    assert ind_a.shape == ind_b.shape and ind_a.shape == ind_c.shape
    return ind_a, ind_b, ind_c


class BinaryOp(OpBase):
    def __init__(self, py_operator, inputs, name, c_operator_str):
        assert len(inputs) == 2
        assert isinstance(c_operator_str, str)
        OpBase.__init__(self, py_operator, inputs, name=name)
        self.c_operator_str = c_operator_str

    def c_code(self, input_var_names, output_var_name):
        a_name, b_name = input_var_names
        c_name = output_var_name
        ind_a, ind_b, ind_c = binary_op_indices(
                self.inputs[0], self.inputs[1], self.output)
        lines = 'double {0}[{1}];\n'.format(c_name, self.output.size)
        for ia, ib, ic in zip(ind_a, ind_b, ind_c):
            lines += '{0}[{1}] = {2}[{3}] {6} {4}[{5}];\n'.format(
                    c_name, ic,
                    a_name, ia,
                    b_name, ib,
                    self.c_operator_str)
        return lines


class BinaryFunction(OpBase):
    def __init__(self, py_operator, inputs, name, c_function_str):
        assert len(inputs) == 2
        assert isinstance(c_function_str, str)
        OpBase.__init__(self, py_operator, inputs, name=name)
        self.c_function_str = c_function_str

    def c_code(self, input_var_names, output_var_name):
        a_name, b_name = input_var_names
        c_name = output_var_name
        ind_a, ind_b, ind_c = binary_op_indices(
                self.inputs[0], self.inputs[1], self.output)
        lines = 'double {0}[{1}];\n'.format(c_name, self.output.size)
        for ia, ib, ic in zip(ind_a, ind_b, ind_c):
            lines += '{0}[{1}] = {6}({2}[{3}], {4}[{5}]);\n'.format(
                    c_name, ic,
                    a_name, ia,
                    b_name, ib,
                    self.c_function_str)
        return lines


class UnitaryFunction(OpBase):
    def __init__(self, py_operator, inputs, name, c_function_str):
        assert len(inputs) == 1
        assert isinstance(c_function_str, str)
        OpBase.__init__(self, py_operator, inputs, name=name)
        self.c_function_str = c_function_str

    def c_code(self, input_var_names, output_var_name):
        a_name, = input_var_names
        b_name = output_var_name
        lines = 'double {0}[{1}];\n'.format(b_name, self.output.size)
        for i in np.arange(self.output.size):
            lines += '{0}[{1}] = {4}({2}[{3}]);\n'.format(
                    b_name, i,
                    a_name, i,
                    self.c_function_str)
        return lines
