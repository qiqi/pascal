import os
import sys
import subprocess
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '../..'))

from pascal.sa2d_generate_c import *

def substitute_stage_h(template, name, stage, max_vars):
    assert len(stage.upstream_values) == 1
    assert len(stage.downstream_values) == 1
    stage_h = '''
        #define STAGE_NAME {0}
        #define NUM_INPUTS {1}
        #define NUM_OUTPUTS {2}
        #define MAX_VARS {3}
    '''.format(
        name,
        stage.upstream_values[0].size,
        stage.downstream_values[0].size,
        max_vars
    ).replace('    ', '')

    for line in template.splitlines():
        if line.strip() == r'/*MAIN_CODE*/':
            stage_h += generate_c_code(stage) + '\n'
        elif not line.strip().startswith('#define '):
            stage_h += line + '\n'
    return stage_h

def substitute_step_c(template, stage_names, max_vars):
    step_c, step_func = '', ''
    for name in stage_names:
        step_c += '#include "{0}.h"\n'.format(name)
        step_func += '{0}(i0, i1, j0, j1, p_w, p_s, p_r);\n'.format(name)
    step_c += '''
        inline void stages(uint64_t i0, uint64_t i1, uint64_t j0, uint64_t j1,
            float * p_w, hook_func_t p_s, hook_func_t p_r) {
        ''' + step_func + '\n}\n'

    for line in template.splitlines():
        if not line.strip().endswith(r'// SUBSTITUTE'):
            step_c += line + '\n'
    return step_c

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
    with open(os.path.join(tmp_path, 'hooks.h'), 'wt') as f:
        f.write(open(os.path.join(template_path, 'hooks.h')).read())

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

def compile_to_worker(stages, worker_name):
    file_path = os.path.split(os.path.abspath(__file__))[0]
    template_path = os.path.join(file_path, worker_name)
    tmp_path = os.path.join(file_path, '.tmp.src.build')
    if not os.path.exists(tmp_path):
        os.mkdir(tmp_path)
    subs_and_write(stages, template_path, tmp_path)
    return compile_and_load(tmp_path)

def test_compile():
    worker_name = 'classic_mpi'
    def heat(w):
        return w.i_p + w.i_m - 2 * w
    def step(w):
        return w + heat(w)
    # not working yet because of redefinition and triburary
    # def step(w):
    #     return w + heat(w + 0.5 * heat(w))
    stages = decompose_function(step, stencil_array())
    binary = compile_to_worker(stages, worker_name)
    print('shared library size: ', len(binary))

if __name__ == '__main__':
    test_compile()
