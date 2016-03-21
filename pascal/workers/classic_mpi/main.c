#include<assert.h>
#include<inttypes.h>
#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include<unistd.h>
#include<time.h>

#include<dlfcn.h>
#include<unistd.h>
#include<sys/stat.h>

#include<mpi.h>

static struct {
    uint64_t i0, i1, j0, j1;
    uint64_t rank_i_m, rank_i_p, rank_j_m, rank_j_p;
    float * p_workspace;
    MPI_Comm comm;
} worker_global_const;

typedef void (*step_func_t)(
            uint64_t i0, uint64_t i1, uint64_t j0, uint64_t j1,
            float * p_workspace, uint64_t num_steps,
            void * exchange_halo_begin, void * exchange_halo_end);

typedef struct {
    uint64_t max_vars, num_inputs, num_steps, step_func_bytes;
    float * p_workspace;
    void * p_shared_lib;
    step_func_t step_func;
} job_t;

int global_mpi_rank;
uint64_t global_exchange_buffer_bytes = 0;
float * global_exchange_buffer = NULL;
MPI_Request global_mpi_send_requests[4];
MPI_Request global_mpi_recv_requests[4];

void exchange_halo_begin(uint64_t ni, uint64_t nj, uint64_t N, float * p)
{
    uint64_t required_bytes = sizeof(float) * N * (ni + nj) * 4;
    if (required_bytes > global_exchange_buffer_bytes) {
        if (global_exchange_buffer != NULL) {
            free(global_exchange_buffer);
        }
        global_exchange_buffer = (float*)malloc(required_bytes);
        global_exchange_buffer_bytes = required_bytes;
    }

    float * sendbuf_ip = global_exchange_buffer;
    float * sendbuf_im = sendbuf_ip + N * nj;
    float * sendbuf_jp = sendbuf_im + N * nj;
    float * sendbuf_jm = sendbuf_jp + N * ni;
    float * recvbuf_ip = sendbuf_jm + N * ni;
    float * recvbuf_im = recvbuf_ip + N * nj;
    float * recvbuf_jp = recvbuf_im + N * nj;
    float * recvbuf_jm = recvbuf_jp + N * ni;

    const int tag_i_forward = 1;
    const int tag_i_backward = 2;
    const int tag_j_forward = 3;
    const int tag_j_backward = 4;

    MPI_Irecv(recvbuf_ip, N * nj, MPI_FLOAT, worker_global_const.rank_i_p,
              tag_i_backward, MPI_COMM_WORLD, &global_mpi_recv_requests[0]);
    MPI_Irecv(recvbuf_im, N * nj, MPI_FLOAT, worker_global_const.rank_i_m,
              tag_i_forward, MPI_COMM_WORLD, &global_mpi_recv_requests[1]);
    MPI_Irecv(recvbuf_jp, N * ni, MPI_FLOAT, worker_global_const.rank_j_p,
              tag_j_backward, MPI_COMM_WORLD, &global_mpi_recv_requests[2]);
    MPI_Irecv(recvbuf_jm, N * ni, MPI_FLOAT, worker_global_const.rank_j_m,
              tag_j_forward, MPI_COMM_WORLD, &global_mpi_recv_requests[3]);

    for (uint64_t i = 0; i < ni; ++i) {
        memcpy(sendbuf_jp + i * N,
               p + N * (1 + (nj+2) * (i+1)), sizeof(float) * N);
        memcpy(sendbuf_jm + i * N,
               p + N * (nj + (nj+2) * (i+1)), sizeof(float) * N);
    }
    for (uint64_t j = 0; j < nj; ++j) {
        memcpy(sendbuf_ip + j * N,
               p + N * (j+1 + (nj+2) * 1), sizeof(float) * N);
        memcpy(sendbuf_im + j * N,
               p + N * (j+1 + (nj+2) * ni), sizeof(float) * N);
    }

    MPI_Isend(sendbuf_ip, N * nj, MPI_FLOAT, worker_global_const.rank_i_p,
              tag_i_forward, MPI_COMM_WORLD, &global_mpi_send_requests[0]);
    MPI_Isend(sendbuf_im, N * nj, MPI_FLOAT, worker_global_const.rank_i_m,
              tag_i_backward, MPI_COMM_WORLD, &global_mpi_send_requests[1]);
    MPI_Isend(sendbuf_jp, N * ni, MPI_FLOAT, worker_global_const.rank_j_p,
              tag_j_forward, MPI_COMM_WORLD, &global_mpi_send_requests[2]);
    MPI_Isend(sendbuf_jm, N * ni, MPI_FLOAT, worker_global_const.rank_j_m,
              tag_j_backward, MPI_COMM_WORLD, &global_mpi_send_requests[3]);
}

void exchange_halo_end(uint64_t ni, uint64_t nj, uint64_t N, float * p)
{
    MPI_Status statuses[4];
    MPI_Waitall(4, global_mpi_recv_requests, statuses);

    float * recvbuf = global_exchange_buffer + N * (ni + nj) * 2;
    float * recvbuf_ip = recvbuf    + N * ni;
    float * recvbuf_im = recvbuf_ip + N * nj;
    float * recvbuf_jp = recvbuf_im + N * nj;
    float * recvbuf_jm = recvbuf_jp + N * ni;

    for (uint64_t i = 0; i < ni; ++i) {
        memcpy(p + N * (0 + (nj+2) * (i+1) * 1),
               recvbuf_jp + i * N, sizeof(float) * N);
        memcpy(p + N * (nj+1 + (nj+2) * (i+1)),
               recvbuf_jm + i * N, sizeof(float) * N);
    }
    for (uint64_t j = 0; j < ni; ++j) {
        memcpy(p + N * (j+1 + (nj+2) * 0),
               recvbuf_ip + j * N, sizeof(float) * N);
        memcpy(p + N * (j+1 + (nj+2) * (ni+1)),
               recvbuf_im + j * N, sizeof(float) * N);
    }

    MPI_Waitall(4, global_mpi_send_requests, statuses);
}

void recv_job_step_func(job_t * p_job)
{
    char * step_func_bin = (char*)malloc(p_job->step_func_bytes);
    MPI_Bcast(step_func_bin, p_job->step_func_bytes, MPI_BYTE, 0,
              worker_global_const.comm);
    // write received binary into file
    char path[1024];
    if (getcwd(path, sizeof(path)) == NULL) {
        fprintf(stderr, "Cannot get current path\n");
        exit(-1);
    }
    int rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    char tmp_job_so[1024];
    sprintf(tmp_job_so, "%s/p_job->%d.so", path, rank);
    FILE * f = fopen(tmp_job_so, "wb");
    fwrite(step_func_bin, 1, p_job->step_func_bytes, f);
    fclose(f);
    // load file and obtain pointer to executable function
    chmod(tmp_job_so, 0777);
    p_job->p_shared_lib = dlopen(tmp_job_so, RTLD_LAZY);
    if (p_job->p_shared_lib == NULL) {
        fprintf(stderr, "Failed to load so.so\n");
        exit(-1);
    }
    p_job->step_func = (step_func_t) dlsym(p_job->p_shared_lib, "step_func");
    free(step_func_bin);
    unlink(tmp_job_so);
}

void recv_job_inputs(job_t * p_job)
{
    uint64_t i0 = worker_global_const.i0;
    uint64_t i1 = worker_global_const.i1;
    uint64_t j0 = worker_global_const.j0;
    uint64_t j1 = worker_global_const.j1;
    uint64_t num_floats = p_job->max_vars * 2 * (i1-i0+2) * (j1-j0+2);
    p_job->p_workspace = (float*) malloc(sizeof(float) * num_floats);

    uint64_t half_workspace = num_floats / 2;
    float * p_recv = p_job->p_workspace + half_workspace;
    const uint64_t input_size = p_job->num_inputs * (i1 - i0) * (j1 - j0);
    MPI_Scatter(0, 0, 0, p_recv, input_size, MPI_FLOAT,
                0, worker_global_const.comm);

    for (uint64_t i = 0; i < i1 - i0; ++i) {
        for (uint64_t j = 0; j < j1 - j0; ++j) {
            uint64_t ind_src = i * (j1 - j0) + j;
            uint64_t ind_des = (i + 1) * (j1 - j0 + 2) + (j + 1);
            float * p_src = p_recv + ind_src * p_job->num_inputs;
            float * p_des = p_job->p_workspace + ind_des * p_job->max_vars;
            memcpy(p_des, p_src, sizeof(float) * p_job->num_inputs);
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
        recv_job_step_func(&job);
        recv_job_inputs(&job);
    }
    return job;
}

void complete_job(job_t job)
{
    uint64_t i0 = worker_global_const.i0;
    uint64_t i1 = worker_global_const.i1;
    uint64_t j0 = worker_global_const.j0;
    uint64_t j1 = worker_global_const.j1;
    fprintf(stderr, "Worker %d starting job %d %d %d %d\n",
            global_mpi_rank,
            (int)job.max_vars,
            (int)job.num_inputs,
            (int)job.num_steps,
            (int)job.step_func_bytes);
    clock_t t0 = clock();
    job.step_func(i0, i1, j0, j1, job.p_workspace, job.num_steps,
                  (void*)&exchange_halo_begin, (void*)&exchange_halo_end);
    send_job_outputs(job);
    dlclose(job.p_shared_lib);
    fprintf(stderr, "Worker %d finished job in %f seconds\n",
            global_mpi_rank,
            (clock() - t0) / (float)CLOCKS_PER_SEC);
}

int main(int argc, char * argv[])
{
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &global_mpi_rank);
    MPI_Comm_get_parent(&worker_global_const.comm);
    if (worker_global_const.comm == MPI_COMM_NULL) {
        fprintf(stderr, "MPI failed to connect to parent\n");
        exit(-1);
    }
    MPI_Recv(&worker_global_const, 8, MPI_UINT64_T, 0,
             MPI_ANY_TAG, worker_global_const.comm, MPI_STATUS_IGNORE);
    fprintf(stderr, "Worker %d initialized\n", global_mpi_rank);
    // next job
    for (uint64_t i_job = 0; ; ++i_job) {
        job_t job = recv_job();
        if (job.num_inputs == 0) {
            break;
        }
        complete_job(job);
    }
    MPI_Barrier(worker_global_const.comm);
    MPI_Finalize();
    return 0;
}


