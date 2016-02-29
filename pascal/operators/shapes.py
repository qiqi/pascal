import copy

import numpy as np

from .op_base import OpBase, infer_context

__all__ = ['transpose', 'reshape', 'roll']

class transpose(OpBase):
    def __init__(self, a, axes=None):
        self.axes = copy.copy(axes)
        OpBase.__init__(self, lambda x: x.transpose(self.axes),
                        (a,), name='transpose')

    def c_code(self, input_var_names, output_var_name):
        inp, out = self.inputs[1], self.output
        ind_inp = np.arange(inp.size).reshape(inp.shape)
        ind_out = ind_inp.transpose(self.axes)
        lines = 'float {0}[{1}];\n'.format(output_var_name, out.size)
        for i_in, i_out in zip(np.ravel(ind_inp), np.ravel(ind_out)):
            lines += '{0}[{1}] = {2}[{3}];\n'.format(
                    output_var_name, i_out, input_var_names[1], i_in)
        return lines


class reshape(OpBase):
    def __init__(self, a, shape):
        self.shape = copy.copy(shape)
        OpBase.__init__(self, lambda x: x.reshape(self.shape),
                        (a,), name='reshape')

    def c_code(self, input_var_names, output_var_name):
        inp, out = self.inputs[1], self.output
        ind_inp = np.arange(inp.size).reshape(inp.shape)
        ind_out = ind_inp.reshape(self.shape)
        lines = 'float {0}[{1}];\n'.format(output_var_name, out.size)
        for i_in, i_out in zip(np.ravel(ind_inp), np.ravel(ind_out)):
            lines += '{0}[{1}] = {2}[{3}];\n'.format(
                    output_var_name, i_out, input_var_names[1], i_in)
        return lines


class roll(OpBase):
    def __init__(self, a, shift, axis=None):
        self.shift = copy.copy(shift)
        self.axis = copy.copy(axis)
        op = lambda x: infer_context(x).roll(x, self.shift, self.axis)
        OpBase.__init__(self, op, (a,), name='roll')

    def c_code(self, input_var_names, output_var_name):
        inp, out = self.inputs[1], self.output
        ind_inp = np.arange(inp.size).reshape(inp.shape)
        ind_out = np.roll(ind_inp, self.shift, self.axis)
        lines = 'float {0}[{1}];\n'.format(output_var_name, out.size)
        for i_in, i_out in zip(np.ravel(ind_inp), np.ravel(ind_out)):
            lines += '{0}[{1}] = {2}[{3}];\n'.format(
                    output_var_name, i_out, input_var_names[1], i_in)
        return lines

