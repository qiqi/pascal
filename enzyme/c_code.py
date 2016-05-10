
import itertools

import numpy as np

from .symbolic_variable import *
from .symbolic_variable import _is_like_sa_value

def name_generator():
    for i in itertools.count():
        yield 'var_{0}'.format(i)

def define_constant(v, name):
    v = np.ravel(np.array(v, float));
    c_code = 'double {0}[{1}];\n'.format(name, v.size);
    for i in range(v.size):
        c_code += '{0}[{1}] = {2};\n'.format(name, i, v[i])
    return c_code

def copy_to_output(name, size):
    c_code = ''
    for i in range(size):
        c_code += 'sink[{0}] = {1}[{0}];\n'.format(i, name)
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
        for a in ['_im', '_ip', '_jm', '_jp', '_km', '_kp']:
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
        if v is builtin.ZERO.value:
            for suffix in ['', '_ip', '_im', '_jp', '_jm', '_km', '_kp']:
                c_code += 'const double {0}{1}[1] = {{0.0f}};\n'.format(
                                       v._name, suffix)
        elif v is builtin.I.value:
            for suffix, shift in zip(['','_ip','_im','_jp','_jm','_km','_kp'],
                                     [0,   +1,   -1,   0,     0,    0,    0]):
                c_code += ('const double {0}{1}[1] = ' +
                           '{{(double)(i+({2}))}};\n').format(
                                       v._name, suffix, shift)
        elif v is builtin.J.value:
            for suffix, shift in zip(['','_ip','_im','_jp','_jm','_km','_kp'],
                                     [0,   0,     0,   +1,   -1,    0,    0]):
                c_code += ('const double {0}{1}[1] = ' +
                           '{{(double)(j+({2}))}};\n').format(
                                       v._name, suffix, shift)
        elif v is builtin.K.value:
            for suffix, shift in zip(['','_ip','_im','_jp','_jm','_km','_kp'],
                                     [0,    0,    0,    0,    0,   -1,   +1]):
                c_code += ('const double {0}{1}[1] = ' +
                           '{{(double)(k+({2}))}};\n').format(
                                       v._name, suffix, shift)
    return c_code + '\n'

def generate_c_code(stage):
    assert len(stage.source_values) == 1
    assert len(stage.sink_values) == 1
    init_values = stage.source_values + stage.triburary_values
    names = ['source'] + ['triburary_{0}'.format(i)
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
