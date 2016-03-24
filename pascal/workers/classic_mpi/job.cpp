#include<stdlib.h>
#include<dlfcn.h>
#include<unistd.h>
#include<sys/stat.h>

#include "job.h"
#include "exchange_halo.h"

Job::Job(MPI_Comm comm, uint64_t i0, uint64_t i1, uint64_t j0, uint64_t j1)
    : comm_(comm), i0_(i0), i1_(i1), j0_(j0), j1_(j1),
      max_vars_(job_consts_[0]),
      num_inputs_(job_consts_[1]),
      num_outputs_(job_consts_[2]),
      num_steps_(job_consts_[3]),
      step_func_bytes_(job_consts_[4]),
      p_workspace_(0),
      p_shared_lib_(0),
      step_func_(0)
{
    MPI_Bcast(job_consts_, 5, MPI_UINT64_T, 0, comm_);
    alloc_workspace_();
    if (num_inputs_ > 0) {
        recv_job_step_func_();
    }
}

Job::~Job()
{
    if (p_shared_lib_) {
        dlclose(p_shared_lib_);
    }
    if (p_workspace_) {
        free(p_workspace_);
    }
}

void Job::complete(const Variable & input, Variable & output)
{
    input.copy_to_workspace(p_workspace_);
    step_func_(i0_, i1_, j0_, j1_, p_workspace_, num_steps_,
               (void*)&exchange_halo_begin, (void*)&exchange_halo_end);
    output.copy_from_workspace(p_workspace_);
}

void Job::recv_job_step_func_()
{
    char * step_func_bin = (char*)malloc(step_func_bytes_);
    MPI_Bcast(step_func_bin, step_func_bytes_, MPI_BYTE, 0, comm_);
    // write received binary into file
    char path[1024];
    if (getcwd(path, sizeof(path)) == NULL) {
        std::cerr << "Cannot get current path\n";
        exit(-1);
    }
    int rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    char tmp_job_so[1024];
    sprintf(tmp_job_so, "%s/p_job->%d.so", path, rank);
    FILE * f = fopen(tmp_job_so, "wb");
    fwrite(step_func_bin, 1, step_func_bytes_, f);
    fclose(f);
    // load file and obtain pointer to executable function
    chmod(tmp_job_so, 0777);
    p_shared_lib_ = dlopen(tmp_job_so, RTLD_LAZY);
    if (p_shared_lib_ == NULL) {
        std::cerr << "Failed to load so.so\n";
        exit(-1);
    }
    step_func_ = (step_func_t) dlsym(p_shared_lib_, "step_func");
    free(step_func_bin);
    unlink(tmp_job_so);
}

void Job::alloc_workspace_()
{
    uint64_t ni = i1_ - i0_, nj = j1_ - j0_;
    uint64_t num_floats = max_vars_ * 2 * (ni+2) * (nj+2);
    p_workspace_ = (float*) malloc(sizeof(float) * num_floats);
}

