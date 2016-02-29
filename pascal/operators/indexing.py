import copy

import numpy as np

from .op_base import OpBase

__all__ = ['getitem', 'setitem']

class getitem(OpBase):
    def __init__(self, a, ind):
        self.ind = copy.copy(ind)
        OpBase.__init__(self, lambda x: x[ind], (a,),
                        name='getitem[{0}]'.format(ind))

    def c_code(self, input_var_names, output_var_name):
        a = self.output
        lines = 'float {0}[{1}];\n'.format(output_var_name, a.size)
        ind = np.arange(a.size).reshape(a.shape)[self.ind]
        for i in ind:
            lines += '{1}[{0}] = {2}[{0}];\n'.format(
                    i, input_var_names[0], output_var_name)
        return lines

class setitem(OpBase):
    def __init__(self, a, ind, b):
        self.ind = copy.copy(ind)
        def op(x, a):
            x = copy.copy(x)
            x[self.ind] = a
            return x
        OpBase.__init__(self, op, (a, b), shape=a.shape,
                        name='setitem[{0}]'.format(ind))

    def c_code(self, input_var_names, output_var_name):
        inp, out = self.inputs[1], self.output
        lines = 'float {0}[{1}];\n'.format(output_var_name, out.size)
        for i in range(out.size):
            lines += '{1}[{0}] = {2}[{0}];\n'.format(
                    i, output_var_name, input_var_names[0])
        ind_out = np.arange(out.size).reshape(out.shape)[self.ind]
        ind_in = np.empty(out.shape, int)
        ind_in[self.ind] = np.arange(inp.size).reshape(inp.shape)
        ind_in = ind_in[self.ind]
        assert ind_in.size == ind_out.size
        lines += '\n'
        for i_in, i_out in zip(ind_in, ind_out):
            lines += '{0}[{1}] = {2}[{3}];\n'.format(
                    output_var_name, i_out, input_var_names[1], i_in)
        return lines

