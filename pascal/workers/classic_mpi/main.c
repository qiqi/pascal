#include<assert.h>
#include<stdint.h>
#include<stdlib.h>
#include<string.h>
#include<mpi.h>

#define MAX_VARIABLES 10
#define NUM_INPUTS 4

MPI_Comm command_comm;

struct {
    uint64_t i0, i1, j0, j1;
    uint64_t x_m, x_p, y_m, y_p;
} worker_position;

void recv_next_job(uint64_t* p_num_step, float* p_workspace)
{
    const uint64_t i0 = worker_position.i0;
    const uint64_t i1 = worker_position.i1;
    const uint64_t j0 = worker_position.j0;
    const uint64_t j1 = worker_position.j1;
    MPI_Recv(p_num_step, 1, MPI_UINT64_T, 0,
             MPI_ANY_TAG, command_comm, MPI_STATUS_IGNORE);
    uint64_t half_workspace = MAX_VARIABLES * (i1 - i0 + 2) * (j1 - j0 + 2);
    float * p_recv = p_workspace + half_workspace;
    const uint64_t input_size = NUM_INPUTS * (i1 - i0) * (j1 - j0);
    MPI_Recv(p_recv, input_size, MPI_FLOAT, 0,
             MPI_ANY_TAG, command_comm, MPI_STATUS_IGNORE);
    for (uint64_t i = 0; i < i1 - i0; ++i) {
        for (uint64_t j = 0; j < j1 - j0; ++j) {
            uint64_t ind_src = i * (j1 - j0) + j;
            uint64_t ind_des = (i + 1) * (j1 - j0 + 2) + (j + 1);
            float * p_src = p_recv + ind_src * NUM_INPUTS;
            float * p_des = p_workspace + ind_des * MAX_VARIABLES;
            memcpy(p_des, p_src, sizeof(float) * NUM_INPUTS);
        }
    }
}

int main(int argc, char** argv)
{
    MPI_Init(&argc, &argv);
    MPI_Comm_get_parent(&command_comm);
    assert(command_comm != MPI_COMM_NULL);
    MPI_Recv(&worker_position, 8, MPI_UINT64_T, 0,
             MPI_ANY_TAG, command_comm, MPI_STATUS_IGNORE);
    uint64_t num_floats = MAX_VARIABLES * 2
         * (worker_position.i1 - worker_position.i0 + 2)
         * (worker_position.j1 - worker_position.j0 + 2);
    float * p_workspace = (float*) malloc(sizeof(float) * num_floats);
    // next job
    uint64_t num_steps;
    recv_next_job(&num_steps, p_workspace);
    for (uint64_t istep = 0; istep < num_steps; ++istep) {
        // 
    }
    MPI_Finalize();
    return 0;
}
