import os
import time
import string
import tempfile
from subprocess import check_call, Popen, PIPE,call

import numpy as np
from .c_code import generate_c_code,generate_init_code

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

def execute(initialization , stages, constants , n , nx , ny , outIndex):
    dataPointSize = max(max([s.source_values[0].size for s in stages]),
                    max([s.sink_values[0].size for s in stages]))
    if callable(stages):
        stages = (stages,)
    stages, stage_indices = unique_stages(stages)
    prefix = time.strftime('%Y%m%d-%H%M%S-', time.localtime())
    tmp_path = tempfile.mkdtemp(prefix=prefix, dir=_tmp_path)
    #generate_main_c(tmp_path, stages, stage_indices, x)
    #generate_workspace_h(tmp_path)
    generate_stage_h(tmp_path, initialization,stages,constants)
    sweptPath = tmp_path + '/../../../Swept2D/'
    call('rm -f ' + sweptPath + 'stages/*.h',shell=True)
    call('rm -f ' + sweptPath + 'bin/*',shell=True)
    call('cp ' + tmp_path + '/* ' + sweptPath + 'stages/',shell=True)
    call('rm -rf ' + tmp_path , shell=True)
    call('cd ' + sweptPath + '/scripts ; ./compile' , shell=True)
    #print 'cd ' + sweptPath + '/scripts ; ./run ' + str(n) + ' ' + str(nx) + ' ' + str(ny) + ' ' +  \
    #     str(len(stages)) + ' ' + str(dataPointSize) + ' ' + str(constants) + ' ' + str(outIndex)
    call('cd ' + sweptPath + '/scripts ; ./run ' + str(n) + ' ' + str(nx) + ' ' + str(ny) + ' ' +  \
         str(len(stages)) + ' ' + str(dataPointSize) + ' ' + str(constants) + ' ' + str(outIndex) , shell=True)
    return 

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

def generate_stage_h(path, initialization,stages,constants):
    assert len(initialization[0].source_values) == len(initialization[0].sink_values) == 1
    for s in stages:
        assert len(s.source_values) == len(s.sink_values) == 1
    template = open(os.path.join(_my_path, 'c_template', 'stage.h')).read()
    template = string.Template(template)
    max_vars = max(max([s.source_values[0].size for s in stages]),
                   max([s.sink_values[0].size for s in stages]))

    initTemplate = open(os.path.join(_my_path, 'c_template', 'init.h')).read()
    initTemplate = string.Template(initTemplate)
    code = generate_init_code(initialization[0],constants)
    code = initTemplate.substitute(CODE=code)
    with open(os.path.join(path, 'init.h'), 'wt') as f:
        f.write(code)
    stage_names = []
    for i, s in enumerate(stages):
        stage_name = 'stage_{0}'.format(i)
        stage_names.append(stage_name)
        code = generate_c_code(s)
        num_inputs = s.source_values[0].size
        num_outputs = s.sink_values[0].size
        code = template.substitute(
                MAX_VARS=max_vars, STAGE_NAME=stage_name,
                NUM_INPUTS=num_inputs, NUM_OUTPUTS=num_outputs, CODE=code)
        with open(os.path.join(path, stage_name + '.h'), 'wt') as f:
            f.write(code)

    template = open(os.path.join(_my_path, 'c_template', 'Substeps2D.h')).read()
    template = string.Template(template)
    includeStages = '\n'
    callStages    = '\n'
    includeStages += '#include \"init.h"\n'
    for i, stageName in enumerate(stage_names):
        includeStages += '#include \"' + stageName + '.h"\n'
        if i==0:
           callStages += 'if(executeFnc == ' + str(i) + ') ' + stageName + '(point);\n'
        else:
           callStages += 'else if(executeFnc == ' + str(i) + ') ' + stageName + '(point);\n'
    code = template.substitute(STAGE_INCLUDE=includeStages, STAGE_CALL=callStages)
    with open(os.path.join(path, 'Substeps2D.h'), 'wt') as f:
       f.write(code)


