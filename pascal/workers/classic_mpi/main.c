#include<assert.h>
#include<inttypes.h>
#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include<unistd.h>
#include<dlfcn.h>
#include<mpi.h>
#include<sys/stat.h>

#include "hooks.h"

static struct {
    uint64_t i0, i1, j0, j1;
    uint64_t i_m, i_p, j_m, j_p;
    float * p_workspace;
    MPI_Comm comm;
} worker_global_const;

typedef struct {
    uint64_t max_vars, num_inputs, num_steps, step_func_bytes;
    float * p_workspace;
    void * p_shared_lib;
    step_func_t step_func;
} job_t;

void receive_job_step_func(job_t job)
{
    char * step_func_bin = (char*)malloc(job.step_func_bytes);
    MPI_Bcast(step_func_bin, job.step_func_bytes, MPI_BYTE, 0,
              worker_global_const.comm);
    // write received binary into file
    char path[1024];
    if (getcwd(path, sizeof(path)) == NULL) {
        fprintf(stderr, "Cannot get current path\n");
        exit(-1);
    }
    strcat(path, "/job.so");
    FILE * f = fopen(path, "wb");
    fwrite(step_func_bin, 1, job.step_func_bytes, f);
    fclose(f);
    // load file and obtain pointer to executable function
    chmod(path, 0777);
    job.p_shared_lib = dlopen(path, RTLD_LAZY);
    if (job.p_shared_lib == NULL) {
        fprintf(stderr, "Failed to load so.so\n");
        exit(-1);
    }
    job.step_func = (step_func_t)dlsym(job.p_shared_lib, "step_func");
    free(step_func_bin);
}

void receive_job_inputs(job_t job)
{
    uint64_t i0 = worker_global_const.i0;
    uint64_t i1 = worker_global_const.i1;
    uint64_t j0 = worker_global_const.j0;
    uint64_t j1 = worker_global_const.j1;
    uint64_t num_floats = job.max_vars * 2 * (i1 - i0 + 2) * (j1 - j0 + 2);
    job.p_workspace = (float*) malloc(sizeof(float) * num_floats);

    uint64_t half_workspace = num_floats / 2;
    float * p_recv = job.p_workspace + half_workspace;
    const uint64_t input_size = job.num_inputs * (i1 - i0) * (j1 - j0);
    MPI_Bcast(p_recv, input_size, MPI_FLOAT, 0, worker_global_const.comm);

    for (uint64_t i = 0; i < i1 - i0; ++i) {
        for (uint64_t j = 0; j < j1 - j0; ++j) {
            uint64_t ind_src = i * (j1 - j0) + j;
            uint64_t ind_des = (i + 1) * (j1 - j0 + 2) + (j + 1);
            float * p_src = p_recv + ind_src * job.num_inputs;
            float * p_des = job.p_workspace + ind_des * job.max_vars;
            memcpy(p_des, p_src, sizeof(float) * job.num_inputs);
        }
    }
}

void send_job_outputs(job_t job)
{
    uint64_t i0 = worker_global_const.i0;
    uint64_t i1 = worker_global_const.i1;
    uint64_t j0 = worker_global_const.j0;
    uint64_t j1 = worker_global_const.j1;
    uint64_t half_workspace = job.max_vars * (i1 - i0 + 2) * (j1 - j0 + 2);
    float * p_send = job.p_workspace + half_workspace;
    for (uint64_t i = 0; i < i1 - i0; ++i) {
        for (uint64_t j = 0; j < j1 - j0; ++j) {
            uint64_t ind_des = i * (j1 - j0) + j;
            uint64_t ind_src = (i + 1) * (j1 - j0 + 2) + (j + 1);
            float * p_des = p_send + ind_des * job.num_inputs;
            float * p_src = job.p_workspace + ind_src * job.max_vars;
            memcpy(p_des, p_src, sizeof(float) * job.num_inputs);
        }
    }
    const uint64_t output_size = job.num_inputs * (i1 - i0) * (j1 - j0);
    MPI_Gather(p_send, output_size, MPI_FLOAT,
               NULL, 0, MPI_FLOAT, 0, worker_global_const.comm);
    free(job.p_workspace);
}

job_t recv_job()
{
    job_t job;
    MPI_Bcast(&job, 4, MPI_UINT64_T, 0, worker_global_const.comm);
    if (job.num_inputs > 0) {
        receive_job_step_func(job);
        receive_job_inputs(job);
    }
    return job;
}

void complete_job(job_t job)
{
    uint64_t i0 = worker_global_const.i0;
    uint64_t i1 = worker_global_const.i1;
    uint64_t j0 = worker_global_const.j0;
    uint64_t j1 = worker_global_const.j1;
    job.step_func(i0, i1, j0, j1, job.p_workspace, job.num_steps, &send, &recv);
    send_job_outputs(job);
    dlclose(job.p_shared_lib);
}

int main(int argc, char * argv[])
{
    fprintf(stderr, "Worker started\n");
    MPI_Init(&argc, &argv);
    fprintf(stderr, "MPI Initialized\n");
    MPI_Comm_get_parent(&worker_global_const.comm);
    if (worker_global_const.comm == MPI_COMM_NULL) {
        fprintf(stderr, "MPI failed to connect to parent\n");
        exit(-1);
    }
    fprintf(stderr, "Connected to parent\n");
    MPI_Recv(&worker_global_const, 8, MPI_UINT64_T, 0,
             MPI_ANY_TAG, worker_global_const.comm, MPI_STATUS_IGNORE);
    fprintf(stderr, "Obtained worker constants: ");
    fprintf(stderr, "%" PRId64 " ", worker_global_const.i0);
    fprintf(stderr, "%" PRId64 " ", worker_global_const.i1);
    fprintf(stderr, "%" PRId64 " ", worker_global_const.j0);
    fprintf(stderr, "%" PRId64 " ", worker_global_const.j1);
    fprintf(stderr, "%" PRId64 " ", worker_global_const.i_m);
    fprintf(stderr, "%" PRId64 " ", worker_global_const.i_p);
    fprintf(stderr, "%" PRId64 " ", worker_global_const.j_m);
    fprintf(stderr, "%" PRId64 " ", worker_global_const.j_p);
    fprintf(stderr, "\n");
    // next job
    for (uint64_t i_job = 0; ; ++i_job) {
        job_t job = recv_job();
        printf("Received job %" PRIu64 "\n", i_job);
        if (job.num_inputs == 0) {
            break;
        }
        complete_job(job);
        printf("Completed job %" PRIu64 "\n", i_job);
    }
    MPI_Finalize();
    return 0;
}


void send(uint64_t n, float * im, float * ip, float * jm, float * jp)
{}
void recv(uint64_t n, float * im, float * ip, float * jm, float * jp)
{}
