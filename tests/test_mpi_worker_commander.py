import os
import sys
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..'))

from pascal.mpi_worker_commander import *

# ============================================================================ #

class TestCustomFunction(unittest.TestCase):
    def testAddOne(self):
        comm = MPI_Commander(8, 8, 2, 2)
        comm.set_custom_func('add_one', lambda x : x + 1)
        i = WorkerVariable('i')
        ip1 = WorkerVariable()
        comm.func('add_one', (i,), result_var=ip1)
        ip1_sum = comm.func(np.sum, (ip1,))
        self.assertAlmostEqual(ip1_sum[0], 90)
        self.assertAlmostEqual(ip1_sum[1], 90)
        self.assertAlmostEqual(ip1_sum[2], 234)
        self.assertAlmostEqual(ip1_sum[3], 234)

    # -------------------------------------------------------------------- #

    def testDoubleTriple(self):
        comm = MPI_Commander(8, 8, 2, 2)
        comm.set_custom_func('double_triple', lambda x : (2 * x, 3 * x))
        j = WorkerVariable('j')
        j_double, j_triple = WorkerVariable(), WorkerVariable()
        comm.func('double_triple', (j,), result_var=(j_double, j_triple))
        j_double_max = comm.func(np.max, (j_double,))
        j_triple_max = comm.func(np.max, (j_triple,))
        self.assertAlmostEqual(j_double_max[0], 8)
        self.assertAlmostEqual(j_double_max[1], 16)
        self.assertAlmostEqual(j_double_max[2], 8)
        self.assertAlmostEqual(j_double_max[3], 16)
        self.assertAlmostEqual(j_triple_max[0], 12)
        self.assertAlmostEqual(j_triple_max[1], 24)
        self.assertAlmostEqual(j_triple_max[2], 12)
        self.assertAlmostEqual(j_triple_max[3], 24)


#==============================================================================#

class TestPassingParamters(unittest.TestCase):
    def testPassingNumpyArray(self):
        comm = MPI_Commander(4, 8, 1, 2)
        z34 = WorkerVariable()
        def make_worker_variable(z, x):
            return x + z.reshape(z.shape + (1,) * x.ndim)
        comm.set_custom_func('make_worker_variable', make_worker_variable)
        comm.func('make_worker_variable', (ZERO, np.zeros([3,4])),
                result_var=z34)
        comm.set_custom_func('get_shape', lambda x : x.shape)
        shape0, shape1 = comm.func('get_shape', (z34,))
        self.assertEqual(shape0, shape1)
        self.assertEqual(shape0, (6, 6, 3, 4))

    def testPassingNonUniformNumpyArray(self):
        comm = MPI_Commander(4, 8, 1, 2)
        z34 = WorkerVariable()
        def make_worker_variable(z, x):
            return x + z.reshape(z.shape + (1,) * x.ndim)
        comm.set_custom_func('make_worker_variable', make_worker_variable)
        args = ((ZERO, np.zeros([3,4])), (ZERO, np.ones([3,4])))
        comm.func_nonuniform_args('make_worker_variable', args, result_var=z34)
        comm.set_custom_func('get_shape', lambda x : x.shape)
        shape0, shape1 = comm.func('get_shape', (z34,))
        self.assertEqual(shape0, shape1)
        self.assertEqual(shape0, (6, 6, 3, 4))
        max0, max1 = comm.func(np.max, (z34,))
        min0, min1 = comm.func(np.min, (z34,))
        self.assertEqual(max0, 0)
        self.assertEqual(min0, 0)
        self.assertEqual(max1, 1)
        self.assertEqual(min1, 1)


#==============================================================================#

class TestFunctions(unittest.TestCase):
    def testNumpyFunsions(self):
        comm = MPI_Commander(4, 8, 1, 2)
        sin_j = WorkerVariable()
        comm.func(np.sin, (J,), result_var=sin_j)
        comm.func(np.copy, (sin_j,), result_var=sin_j)
        sin_j_max = comm.func(np.max, (sin_j,))
        self.assertAlmostEqual(sin_j_max[0], 0.90929742682568171)
        self.assertAlmostEqual(sin_j_max[1], 0.98935824662338179)

    def testPickledNumpyFunsions(self):
        comm = MPI_Commander(4, 8, 1, 2)
        sin_j = WorkerVariable()
        comm.func(dill.dumps(np.sin), (J,), result_var=sin_j)
        comm.func(np.copy, (sin_j,), result_var=sin_j)
        sin_j_max = comm.func(np.max, (sin_j,))
        self.assertAlmostEqual(sin_j_max[0], 0.90929742682568171)
        self.assertAlmostEqual(sin_j_max[1], 0.98935824662338179)

################################################################################
################################################################################
################################################################################
