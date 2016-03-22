
import itertools

import numpy as np

from .sa2d_decomp import *
from .sa2d_decomp import _is_like_sa_value

def name_generator():
    for i in itertools.count():
        yield 'var_{0}'.format(i)

def define_constant(v, name):
    v = np.ravel(np.array(v, float));
    c_code = 'float {0}[{1}];\n'.format(name, v.size);
    for i in range(v.size):
        c_code += '{0}[{1}] = {2};\n'.format(name, i, v[i])
    return c_code

def copy_to_output(name, size):
    c_code = ''
    for i in range(size):
        c_code += 'downstream[{0}] = {1}[{0}];\n'.format(i, name)
    return c_code

def generate_c_code_for_op(op, name_gen):
    c_code = ''
    v = op.output
    assert not hasattr(v, '_name')
    input_names = []
    v.has_neighbor = not op.access_neighbor
    for inp in op.inputs:
        if _is_like_sa_value(inp):
            input_names.append(inp._name)
            v.has_neighbor = v.has_neighbor and inp.has_neighbor
        else:
            const_name = next(name_gen)
            c_code += define_constant(inp, const_name) + '\n'
            input_names.append(const_name)
    output_name = next(name_gen)
    c_code += op.c_code(input_names, output_name) + '\n'
    if v.has_neighbor:
        for a in ['_i_m', '_i_p', '_j_m', '_j_p']:
            input_nbr_names = []
            for inp, name in zip(op.inputs, input_names):
                if _is_like_sa_value(inp):
                    input_nbr_names.append(name + a)
                else:
                    input_nbr_names.append(name)
            c_code += op.c_code(input_nbr_names, output_name + a) + '\n'
    v._name = output_name
    return c_code

def initialize_default_values(values):
    c_code = ''
    for v in values:
        if v is builtin.ZERO:
            for suffix in ['', '_i_p', '_i_m', '_j_p', '_j_m']:
                c_code += 'const float {0}{1}[1] = {{0.0f}};\n'.format(
                                       v._name, suffix)
    return c_code + '\n'

def generate_c_code(stage):
    assert len(stage.upstream_values) == 1
    assert len(stage.downstream_values) == 1
    init_values = stage.upstream_values + stage.triburary_values
    names = ['upstream'] + ['triburary_{0}'.format(i)
                            for i in range(len(stage.triburary_values))]
    for v, name in zip(init_values, names):
        assert not hasattr(v, '_name')
        v._name = name
        v.has_neighbor = True
    c_code = initialize_default_values(init_values)
    name_gen = name_generator()
    for v in stage.sorted_values:
        c_code += generate_c_code_for_op(v.owner, name_gen)
    c_code += copy_to_output(v._name, v.size)
    for v in init_values + stage.sorted_values:
        del v._name
    return c_code
