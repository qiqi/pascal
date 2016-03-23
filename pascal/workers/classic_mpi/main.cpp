#include<cassert>
#include<cstdlib>
#include<cstring>
#include<ctime>

#include<unistd.h>
#include<inttypes.h>

#include<mpi.h>

#include "job.h"

static struct {
    uint64_t i_range[2], j_range[2];
    uint64_t neighbor_ranks[4];
    float * p_workspace;
    MPI_Comm comm;
    int global_mpi_rank;
} worker_global_const;

int main(int argc, char * argv[])
{
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &worker_global_const.global_mpi_rank);
    MPI_Comm_get_parent(&worker_global_const.comm);
    if (worker_global_const.comm == MPI_COMM_NULL) {
        fprintf(stderr, "MPI failed to connect to parent\n");
        exit(-1);
    }
    MPI_Recv(&worker_global_const, 8, MPI_UINT64_T, 0,
             MPI_ANY_TAG, worker_global_const.comm, MPI_STATUS_IGNORE);
    set_neighbor_ranks(worker_global_const.neighbor_ranks);
    fprintf(stderr, "Worker %d initialized\n",
            worker_global_const.global_mpi_rank);
    // next job
    for (uint64_t i_job = 0; ; ++i_job) {
        job_t job = recv_job();
        if (job.num_inputs == 0) {
            break;
        }
    fprintf(stderr, "Worker %d starting job %d %d %d %d\n",
            worker_global_const.global_mpi_rank,
            (int)job.max_vars,
            (int)job.num_inputs,
            (int)job.num_steps,
            (int)job.step_func_bytes);
        complete_job(job);
    }
    MPI_Barrier(worker_global_const.comm);
    MPI_Finalize();
    return 0;
}
