
import itertools

import numpy as np

from .sa2d_decomp import *
from .sa2d_decomp import _is_like_sa_value

def name_generator():
    for i in itertools.count():
        yield 'var_{0}'.format(i)

def define_constant(v, name):
    v = np.ravel(np.array(v, float));
    lines = 'float {0}[{1}];\n'.format(name, v.size);
    for i in range(v.size):
        lines += '{0}[{1}] = {2};\n'.format(name, i, v[i])
    return lines

def copy_to_output(name, size):
    lines = ''
    for i in range(size):
        lines += 'downstream[{0}] = {1}[{0}];\n'.format(i, name)
    return lines

def generate_c_code_for_op(op, name_gen):
    lines = ''
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
            lines += define_constant(inp, const_name) + '\n'
            input_names.append(const_name)
    output_name = next(name_gen)
    lines += op.c_code(input_names, output_name) + '\n'
    if v.has_neighbor:
        for a in ['_i_m', '_i_p', '_j_m', '_j_p']:
            input_nbr_names = []
            for inp, name in zip(op.inputs, input_names):
                if _is_like_sa_value(inp):
                    input_nbr_names.append(name + a)
                else:
                    input_nbr_names.append(name)
            lines += op.c_code(input_nbr_names, output_name + a) + '\n'
    v._name = output_name
    return lines

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
    lines = ''
    name_gen = name_generator()
    for v in stage.sorted_values:
        lines += generate_c_code_for_op(v.owner, name_gen)
    lines += copy_to_output(v._name, v.size)
    for v in init_values + stage.sorted_values:
        del v._name
    return lines

def generate_test_c_code(stage, stage_name, ni, nj):
    lines =  '#include<math.h>\n'
    lines += '#include<stdio.h>\n\n'
    v_up, v_down = stage.upstream_values[0], stage.downstream_values[0]
    args = ['float down[{0}][{1}][{2}]'.format(ni, nj, v_down.size),
            'float up[{0}][{1}][{2}]'.format(ni, nj, v_up.size)]
    for i, v in enumerate(stage.triburary_values):
        args.append(
            'float trib_{0}[{1}][{2}][{3}]'.format(i, ni, nj, v.size))
    lines += 'void {0}({1})\n{{\n'.format(stage_name, ', '.join(args))
    lines += '    for (int i = 0; i < {0}; ++i) {{\n'.format(ni)
    lines += '        for (int j = 0; j < {0}; ++j) {{\n'.format(nj)
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
    lines += '\n'.join(' ' * 12 + line for line in inner.splitlines()) + '\n'
    lines += '        }\n'
    lines += '    }\n'
    lines += '}\n'
    return lines
