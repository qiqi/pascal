import os
from io import BytesIO
import numpy as np
from subprocess import Popen, PIPE

my_path = os.path.dirname(os.path.abspath(__file__))
bin_path = os.path.abspath(os.path.join(my_path, '..', '..', 'bin'))
quarkflow_bin = os.path.join(bin_path, 'quarkflow')

assert os.path.exists(quarkflow_bin)

def test_heat_midpoint():
    p = Popen(quarkflow_bin, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    input_file = os.path.join(my_path, 'heat_midpoint.txt')
    out, err = p.communicate(open(input_file, 'rb').read())
    c, d, e = np.loadtxt(BytesIO(out), int).T
    assert len(err.strip()) == 0
    assert c.min() == 1 and c.max() == 2
    assert (d - c > 0).sum() == 2

def test_manufactured():
    p = Popen(quarkflow_bin, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    input_file = os.path.join(my_path, 'manufactured.txt')
    out, err = p.communicate(open(input_file, 'rb').read())
    c, d, e = np.loadtxt(BytesIO(out), int).T
    assert len(err.strip()) == 0
    assert c.min() == 1 and c.max() == 3
    assert (d != c).sum() == 2
    assert d[2] != c[2] and d[4] != c[4]
