from .op_base import OpBase

__all__ = ['i_m', 'i_p', 'j_m', 'j_p']

class dummy_func(object):
    def __init__(self, shape):
        self.shape = shape
        self.i_p = self
        self.i_m = self
        self.j_p = self
        self.j_m = self

class i_m(OpBase):
    def __init__(self, a):
        OpBase.__init__(self, lambda x: x.i_m, (a,),
                        access_neighbor=True, dummy_func=dummy_func,
                        name='i_m')

    def c_code(self, input_var_names, output_var_name):
        return 'const float * {1} = {0}_i_m;\n'.format(input_var_names[0],
                                                       output_var_name);

class i_p(OpBase):
    def __init__(self, a):
        OpBase.__init__(self, lambda x: x.i_p, (a,),
                        access_neighbor=True, dummy_func=dummy_func,
                        name='i_p')

    def c_code(self, input_var_names, output_var_name):
        return 'const float * {1} = {0}_i_p;\n'.format(input_var_names[0],
                                                       output_var_name);

class j_m(OpBase):
    def __init__(self, a):
        OpBase.__init__(self, lambda x: x.j_m, (a,),
                        access_neighbor=True, dummy_func=dummy_func,
                        name='j_m')

    def c_code(self, input_var_names, output_var_name):
        return 'const float * {1} = {0}_j_m;\n'.format(input_var_names[0],
                                                       output_var_name);

class j_p(OpBase):
    def __init__(self, a):
        OpBase.__init__(self, lambda x: x.j_p, (a,),
                        access_neighbor=True, dummy_func=dummy_func,
                        name='j_p')

    def c_code(self, input_var_names, output_var_name):
        return 'const float * {1} = {0}_j_p;\n'.format(input_var_names[0],
                                                       output_var_name);

