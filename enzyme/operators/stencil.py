import numpy as np
from .op_base import OpBase

__all__ = ['im', 'ip', 'jm', 'jp', 'km', 'kp']

class ShapeKeeper(object):
    def __init__(self, shape):
        self.shape = shape
        self.ip = self
        self.im = self
        self.jp = self
        self.jm = self
        self.kp = self
        self.km = self

def stencil_op(op_name, shift, axis):
    def op(a):
        return getattr(a, op_name)
    def __init__(self, a):
        OpBase.__init__(self, op, (a,), access_neighbor=True,
                        shape_keeper=ShapeKeeper, name=op_name)
    def c_code(self, input_var_names, output_var_name):
        return 'const float * {0} = {1}_{2};\n'.format(
                output_var_name, input_var_names[0], op_name)
    return type(op_name, (OpBase,), {'__init__': __init__, 'c_code': c_code})

im = stencil_op('im', +1, 0)
ip = stencil_op('ip', -1, 0)
jm = stencil_op('jm', +1, 1)
jp = stencil_op('jp', -1, 1)
km = stencil_op('km', +1, 2)
kp = stencil_op('kp', -1, 2)
