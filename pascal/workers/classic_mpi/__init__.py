import os
import sys
import string
import subprocess
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '../../..'))

from pascal.sa2d_generate_c import *

def substitute_stage_h(template, name, stage, max_vars):
    assert len(stage.upstream_values) == 1
    assert len(stage.downstream_values) == 1
    code = generate_c_code(stage).replace('\n', '\n' + ' ' * 12)
    return string.Template(template).substitute(
                        STAGE_NAME=name,
                        NUM_INPUTS=stage.upstream_values[0].size,
                        NUM_OUTPUTS=stage.downstream_values[0].size,
                        MAX_VARS=max_vars,
                        MAIN_CODE=code)

def substitute_step_c(template, stage_names, max_vars):
    include, stages = '', ''
    for name in stage_names:
        include += '#include "{0}.h"\n'.format(name)
        stages += '    {0}(i0, i1, j0, j1, p_w, p_s, p_e);\n'.format(name)
    return string.Template(template).substitute(
            INCLUDE=include,
            STAGES=stages)

def subs_and_write(stages, template_path, tmp_path):
    step_c = open(os.path.join(template_path, 'step.c')).read()
    stage_h = open(os.path.join(template_path, 'stage.h')).read()
    max_vars = max(s.downstream_values[0].size for s in stages)
    stage_names = ['stage_{0}'.format(i) for i in range(len(stages))]
    with open(os.path.join(tmp_path, 'step.c'), 'wt') as f:
        f.write(substitute_step_c(step_c, stage_names, max_vars))
    for name, stage in zip(stage_names, stages):
        with open(os.path.join(tmp_path, name + '.h'), 'wt') as f:
            f.write(substitute_stage_h(stage_h, name, stage, max_vars))

def compile_and_load(tmp_path, compiler='gcc'):
    compiler = subprocess.check_output(['which', compiler]).decode().strip()
    src = os.path.join(tmp_path, 'step.c')
    obj = os.path.join(tmp_path, 'step.o')
    so = os.path.join(tmp_path, 'step.so')
    subprocess.check_call([
        compiler, '-O3', '--std=c99', '--PIC', '-c', src, '-o', obj
    ])
    subprocess.check_call([compiler, '-O3', '--shared', obj, '-o', so])
    return open(so, 'rb').read()

def build(stages):
    file_path = os.path.split(os.path.abspath(__file__))[0]
    tmp_path = os.path.join(file_path, '.tmp.src.build')
    if not os.path.exists(tmp_path):
        os.mkdir(tmp_path)
    subs_and_write(stages, file_path, tmp_path)
    return compile_and_load(tmp_path)

def test_build():
    def heat(w):
        return w.i_p + w.i_m - 2 * w
    def step(w):
        return w + heat(w + 0.5 * heat(w))
    stages = decompose_function(step, stencil_array())
    binary = build(stages)
    print('shared library size: ', len(binary))

if __name__ == '__main__':
    test_build()
