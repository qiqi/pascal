#include<inttypes.h>

#include<mpi.h>

#include "variable.h"

class Job {
    private:

    typedef void (*step_func_t)(
                uint64_t i0, uint64_t i1, uint64_t j0, uint64_t j1,
                float * p_workspace, uint64_t num_steps,
                void * exchange_halo_begin, void * exchange_halo_end);

    MPI_Comm comm_;
    uint64_t i0_, i1_, j0_, j1_;
    uint64_t job_consts_[5];
    uint64_t &max_vars_, &num_inputs_, &num_outputs_,
             &num_steps_, &step_func_bytes_;
    float * p_workspace_;
    void * p_shared_lib_;
    step_func_t step_func_;

    void recv_job_step_func_();
    void alloc_workspace_();

    public:

    Job(MPI_Comm comm, uint64_t i0, uint64_t i1, uint64_t j0, uint64_t j1);
    bool is_empty() { return num_inputs_ == 0 && num_outputs_ == 0; }
    void complete(const Variable & input, Variable & output);
    uint64_t input_size() const { return num_inputs_; }
    uint64_t output_size() const { return num_outputs_; }
    ~Job();
};
