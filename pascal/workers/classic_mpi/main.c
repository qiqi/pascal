#include<assert.h>
#include<stdint.h>
#include<stdlib.h>
#include<string.h>
#include<unistd.h>
#include<dlfcn.h>
#include<mpi.h>
#include<sys/stat.h>

MPI_Comm command_comm;

struct {
    uint64_t i0, i1, j0, j1;
    uint64_t x_m, x_p, y_m, y_p;
} worker_const_position;

typedef struct {
    uint64_t max_vars, num_inputs, max_steps, step_func_bytes;
    float * p_workspace;
    void * p_shared_lib;
    void (*step_func)(uint64_t i0, uint64_t i1, uint64_t j0, uint64_t j1);
} job_t;

void delete_job(job_t job)
{
    free(job.p_workspace);
}

void receive_job_step_func(job_t job)
{
    char * step_func_bin = malloc(job.step_func_bytes);
    MPI_Bcast(step_func_bin, job.step_func_bytes, MPI_CHAR, 0, command_comm);
    // write into file
    char path[2048];
    getcwd(path, sizeof(path));
    strcat(path, "/job.so");
    FILE * f = fopen(path, "wb");
    f.write(step_func_bin);
    fchmod(f, 0777);
    fclose(f);
    // load file
    job.p_shared_lib = dlopen(path, RTLD_LAZY);
    if (p_dl == NULL) {
        fprintf(stderr, "Failed to load so.so\n");
        exit(-1);
    }
    job.step_func = dlsym(job.p_shared_lib, "step_func");
    free(step_func_bin);
}

void allocate_job_workspace(job_t job)
{
    uint64_t i0 = worker_const_position.i0;
    uint64_t i1 = worker_const_position.i1;
    uint64_t j0 = worker_const_position.j0;
    uint64_t j1 = worker_const_position.j1;
    uint64_t num_floats = job.max_vars * 2 * (i1 - i0 + 2) * (j1 - j0 + 2);
    job.p_workspace = (float*) malloc(sizeof(float) * num_floats);
}

job_t recv_job()
{
    job_t job;
    MPI_Bcast(&job, 4, MPI_UINT64_T, 0, command_comm);
    allocate_job_workspace(job);
    uint64_t half_workspace = job.max_vars * (i1 - i0 + 2) * (j1 - j0 + 2);
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
    MPI_Recv(&worker_const_position, 8, MPI_UINT64_T, 0,
             MPI_ANY_TAG, command_comm, MPI_STATUS_IGNORE);
    // next job
    uint64_t num_steps;
    recv_next_job(&num_steps, p_workspace);
    for (uint64_t istep = 0; istep < num_steps; ++istep) {
        // 
    }
    MPI_Finalize();
    return 0;
}
