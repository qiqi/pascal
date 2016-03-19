
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
        if v is G_ZERO:
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

def generate_test_c_code(stage, stage_name, ni, nj):
    c_code =  '#include<math.h>\n'
    c_code += '#include<stdio.h>\n\n'
    v_up, v_down = stage.upstream_values[0], stage.downstream_values[0]
    args = ['float down[{0}][{1}][{2}]'.format(ni, nj, v_down.size),
            'float up[{0}][{1}][{2}]'.format(ni, nj, v_up.size)]
    for i, v in enumerate(stage.triburary_values):
        args.append(
            'float trib_{0}[{1}][{2}][{3}]'.format(i, ni, nj, v.size))
    c_code += 'void {0}({1})\n{{\n'.format(stage_name, ', '.join(args))
    c_code += '    for (int i = 0; i < {0}; ++i) {{\n'.format(ni)
    c_code += '        for (int j = 0; j < {0}; ++j) {{\n'.format(nj)
    inner =  'float * downstream = down[i][j];\n'
    inner += 'float * downstream_x_p = down[(i+1)%{0}][j];\n'.format(ni)
    inner += 'float * downstream_x_m = down[(i+{0}-1)%{0}][j];\n'.format(ni)
    inner += 'float * downstream_y_p = down[i][(j+1)%{0}];\n'.format(nj)
    inner += 'float * downstream_y_m = down[i][(j+{0}-1)%{0}];\n'.format(nj)
    inner += 'const float * upstream = up[i][j];\n'
    inner += 'const float * upstream_x_p = up[(i+1)%{0}][j];\n'.format(ni)
    inner += 'const float * upstream_x_m = up[(i+{0}-1)%{0}][j];\n'.format(ni)
    inner += 'const float * upstream_y_p = up[i][(j+1)%{0}];\n'.format(nj)
    inner += 'const float * upstream_y_m = up[i][(j+{0}-1)%{0}];\n'.format(nj)
    for i in range(len(stage.triburary_values)):
        pref = 'const float * triburary_'
        inner += pref + '{0} = trib_{0}[i][j];\n' .format(i)
        inner += pref + '{0}_x_p = trib_{0}[(i+1)%{1}][j];\n'.format(i, ni)
        inner += pref + '{0}_x_m = trib_{0}[(i+{1}-1)%{1}][j];\n'.format(i, ni)
        inner += pref + '{0}_y_p = trib_{0}[i][(j+1)%{1}];\n'.format(i, nj)
        inner += pref + '{0}_y_m = trib_{0}[i][(j+{1}-1)%{1}];\n'.format(i, nj)
    inner += generate_c_code(stage)
    c_code += '\n'.join(' ' * 12 + line for line in inner.splitc_code()) + '\n'
    c_code += '        }\n'
    c_code += '    }\n'
    c_code += '}\n'
    return c_code
