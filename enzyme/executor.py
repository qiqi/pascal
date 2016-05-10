import os
import time
import string
import tempfile
from subprocess import check_call, Popen, PIPE

import numpy as np
from .c_code import generate_c_code

_my_path = os.path.dirname(os.path.abspath(__file__))
_tmp_path = os.path.join(_my_path, 'tmp_c_code')
if not os.path.exists(_tmp_path): os.mkdir(_tmp_path)

def unique_stages(stages):
    unique_stage_list = []
    unique_stage_dict = {}
    stage_indices = []
    for s in stages:
        if not s in unique_stage_dict:
            unique_stage_dict[s] = len(unique_stage_list)
            unique_stage_list.append(s)
        stage_indices.append(unique_stage_dict[s])
    return unique_stage_list, stage_indices

def execute(stages, x):
    if callable(stages):
        stages = (stages,)
    stages, stage_indices = unique_stages(stages)
    prefix = time.strftime('%Y%m%d-%H%M%S-', time.localtime())
    tmp_path = tempfile.mkdtemp(prefix=prefix, dir=_tmp_path)
    generate_main_c(tmp_path, stages, stage_indices, x)
    generate_workspace_h(tmp_path)
    generate_stage_h(tmp_path, stages)
    check_call('gcc --std=c99 -O3 main.c -lm -o main'.split(), cwd=tmp_path)
    in_bytes = np.asarray(x, np.float64, 'C').tobytes()
    p = Popen('./main', cwd=tmp_path, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out_bytes, err = p.communicate(in_bytes)
    assert len(err.strip()) == 0
    y = np.frombuffer(out_bytes, np.float64)
    y_shape = x.shape[:3] + stages[-1].sink_values[0].shape
    return np.asarray(y, x.dtype).reshape(y_shape)

def generate_main_c(path, stages, stage_indices, x):
    ni, nj, nk = x.shape[:3]
    max_vars = max(max([s.source_values[0].size for s in stages]),
                   max([s.sink_values[0].size for s in stages]))
    assert np.prod(x.shape[3:]) == stages[0].source_values[0].size
    num_inputs = stages[0].source_values[0].size
    num_outputs = stages[-1].sink_values[0].size

    names = ['stage_{0}'.format(i) for i in range(len(stages))]
    include = '\n'.join(['#include "{0}.h"'.format(n) for n in names])
    names = ['stage_{0}'.format(i) for i in stage_indices]
    stages = '\n'.join(['{0}(NI,NJ,NK,&buf);'.format(n) for n in names])

    template = open(os.path.join(_my_path, 'c_template', 'main.c')).read()
    template = string.Template(template)
    code = template.substitute(NI=ni, NJ=nj, NK=nk, MAX_VARS=max_vars,
                               NUM_INPUTS=num_inputs, NUM_OUTPUTS=num_outputs,
                               INCLUDE=include, STAGES=stages)
    with open(os.path.join(path, 'main.c'), 'wt') as f:
        f.write(code)

def generate_workspace_h(path):
    code = open(os.path.join(_my_path, 'c_template', 'workspace.h')).read()
    with open(os.path.join(path, 'workspace.h'), 'wt') as f:
        f.write(code)

def generate_stage_h(path, stages):
    for s in stages:
        assert len(s.source_values) == len(s.sink_values) == 1
    template = open(os.path.join(_my_path, 'c_template', 'stage.h')).read()
    template = string.Template(template)
    max_vars = max(max([s.source_values[0].size for s in stages]),
                   max([s.sink_values[0].size for s in stages]))
    for i, s in enumerate(stages):
        stage_name = 'stage_{0}'.format(i)
        code = generate_c_code(s)
        num_inputs = s.source_values[0].size
        num_outputs = s.sink_values[0].size
        code = template.substitute(
                MAX_VARS=max_vars, STAGE_NAME=stage_name,
                NUM_INPUTS=num_inputs, NUM_OUTPUTS=num_outputs, CODE=code)
        with open(os.path.join(path, stage_name + '.h'), 'wt') as f:
            f.write(code)
