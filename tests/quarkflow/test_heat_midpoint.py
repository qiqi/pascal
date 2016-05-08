import os
from subprocess import Popen, PIPE

my_path = os.path.dirname(os.path.abspath(__file__))
bin_path = os.path.abspath(os.path.join(my_path, '..', '..', 'bin'))
quarkflow_bin = os.path.join(bin_path, 'quarkflow')

assert os.path.exists(quarkflow_bin)

def test_heat_midpoint():
    p = Popen(quarkflow_bin, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    input_file = os.path.join(my_path, 'heat_midpoint.txt')
    out, err = p.communicate(open(input_file, 'rb').read())
    print(out)

test_heat_midpoint()
