# ============================================================================ #
#                                                                              #
#                    sa2d_decomp.py copyright(c) Qiqi Wang 2015                #
#                                                                              #
# ============================================================================ #

import unittest
import operator
import numpy as np
import theano
import theano.tensor as T

def _is_like_sa(a):
    '''
    Check attributes of stencil array object
    '''
    return hasattr(a, 'owner') and hasattr(a, 'stencil_level')

class Op(object):
    '''
    Perform operations between arrays with different stencil levels
    The resulting array has the deepest stencil level among all inputs.

    Op(operation, inputs)
        operation: a function that takes a list of inputs as arguments
        inputs: a list of stencil array
    '''
    def __init__(self, operation, inputs, access_neighbor=False):
        self.operation = operation
        self.inputs = inputs

        stencil_level = max(a.stencil_level for a in inputs if _is_like_sa(a))
        if access_neighbor:
            stencil_level += 1
        self.output = stencil_array(self, stencil_level)

    def perform(self, input_objects):
        assert len(input_objects) == len(self.inputs)
        return self.operation(*input_objects)


class stencil_array(object):
    def __init__(self, owner, stencil_level=0):
        self.owner = owner
        self.stencil_level = stencil_level

    # --------------------------- operations ------------------------------ #
    #TODO

    # ------------------------- transformations --------------------------- #
    #TODO

    # ------------------------ neighbor access -------------------------- #

    @property
    def x_p(self):
        return Op(lambda x : x.x_p, (self,), access_neighbor=True)

    @property
    def x_m(self):
        return Op(lambda x : x.x_m, (self,), access_neighbor=True)

    @property
    def y_p(self):
        return Op(lambda x : x.y_p, (self,), access_neighbor=True)

    @property
    def y_m(self):
        return Op(lambda x : x.y_m, (self,), access_neighbor=True)

    # ---------------------------- indexing ------------------------------- #
    #TODO


# ============================================================================ #
#                                 unit tests                                   #
# ============================================================================ #

class TestOperators(unittest.TestCase):
    pass

# ============================================================================ #
#                                                                              #
# ============================================================================ #

if __name__ == '__main__':
    unittest.main()

################################################################################
################################################################################
################################################################################
