from .op_base import OpBase

__all__ = ['x_m', 'x_p', 'y_m', 'y_p']

class dummy_func(object):
    def __init__(self, shape):
        self.shape = shape
        self.x_p = self
        self.x_m = self
        self.y_p = self
        self.y_m = self

class x_m(OpBase):
    def __init__(self, a):
        OpBase.__init__(self, lambda x: x.x_m, (a,),
                        access_neighbor=True, dummy_func=dummy_func,
                        name='x_m')

    def c_code(self, input_var_names, output_var_name):
        return 'float * {1} = {0}_x_m;\n'.format(input_var_names[0],
                                                 output_var_name);

class x_p(OpBase):
    def __init__(self, a):
        OpBase.__init__(self, lambda x: x.x_p, (a,),
                        access_neighbor=True, dummy_func=dummy_func,
                        name='x_p')

    def c_code(self, input_var_names, output_var_name):
        return 'float * {1} = {0}_x_p;\n'.format(input_var_names[0],
                                                 output_var_name);

class y_m(OpBase):
    def __init__(self, a):
        OpBase.__init__(self, lambda x: x.y_m, (a,),
                        access_neighbor=True, dummy_func=dummy_func,
                        name='y_m')

    def c_code(self, input_var_names, output_var_name):
        return 'float * {1} = {0}_y_m;\n'.format(input_var_names[0],
                                                 output_var_name);

class y_p(OpBase):
    def __init__(self, a):
        OpBase.__init__(self, lambda x: x.y_p, (a,),
                        access_neighbor=True, dummy_func=dummy_func,
                        name='y_p')

    def c_code(self, input_var_names, output_var_name):
        return 'float * {1} = {0}_y_p;\n'.format(input_var_names[0],
                                                 output_var_name);

