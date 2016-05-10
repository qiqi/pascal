import copy
import operator
import numbers

import numpy as np

from .op_base import infer_context
from .op_base import OpBase, BinaryOp, BinaryFunction, UnitaryFunction

__all__ = ['add', 'sub', 'mul', 'truediv', 'pow', 'neg', 'sin', 'cos', 'exp',
           'sum']

class add(BinaryOp):
    def __init__(self, a, b):
        BinaryOp.__init__(self,
                          operator.add,
                          (a, b), name="add",
                          c_operator_str="+")

class sub(BinaryOp):
    def __init__(self, a, b):
        BinaryOp.__init__(self,
                          operator.sub,
                          (a, b), name="sub",
                          c_operator_str="-")

class mul(BinaryOp):
    def __init__(self, a, b):
        BinaryOp.__init__(self,
                          operator.mul,
                          (a, b), name="mul",
                          c_operator_str="*")

class truediv(BinaryOp):
    def __init__(self, a, b):
        BinaryOp.__init__(self,
                          operator.truediv,
                          (a, b), name="div",
                          c_operator_str="/")

class pow(BinaryFunction):
    def __init__(self, a, b):
        BinaryFunction.__init__(self,
                                operator.pow,
                                (a, b), name="pow",
                                c_function_str="pow")

class neg(UnitaryFunction):
    def __init__(self, a):
        UnitaryFunction.__init__(self,
                                 operator.neg,
                                 (a,), name="neg",
                                 c_function_str="-")

class sin(UnitaryFunction):
    def __init__(self, a):
        op = lambda x: infer_context(x).sin(x)
        UnitaryFunction.__init__(self, op, (a,), name="sin",
                                 c_function_str="sin")

class cos(UnitaryFunction):
    def __init__(self, a):
        op = lambda x: infer_context(x).cos(x)
        UnitaryFunction.__init__(self, op, (a,), name="cos",
                                 c_function_str="cos")

class exp(UnitaryFunction):
    def __init__(self, a):
        op = lambda x: infer_context(x).exp(x)
        UnitaryFunction.__init__(self, op, (a,), name="exp",
                                 c_function_str="exp")


class sum(OpBase):
    def __init__(self, a, axis=None):
        self.axis = copy.copy(axis)
        OpBase.__init__(self, lambda x: x.sum(self.axis),
                        (a,), name='sum')

    def c_code(self, input_var_names, output_var_name):
        inp, out = self.inputs[1], self.output
        ind_out = np.zeros(inp.shape, int)
        if self.axis is not None:
            shape = list(inp.shape)
            shape[self.axis] = 1
            i_out = np.arange(out.size).reshape(shape)
            ind_out += i_out
        lines = 'double {0}[{1}];\n'.format(output_var_name, out.size)
        for i in range(out.size):
            lines += '{0}[{1}] = 0.0;\n'.format(output_var_name, i)
        for i_inp, i_out in enumerate(np.ravel(ind_out)):
            lines += '{0}[{1}] += {2}[{3}];\n'.format(
                    output_var_name, i_out, input_var_names[1], i_inp)
        return lines

