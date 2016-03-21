#include<stdio.h>
${INCLUDE}

inline void stages(uint64_t i0, uint64_t i1, uint64_t j0, uint64_t j1,
                   float * p_w, void * p_s, void * p_e)
{
${STAGES}
}

void step_func(uint64_t i0, uint64_t i1, uint64_t j0, uint64_t j1,
               float * p_workspace, uint64_t num_steps,
               void * exchange_halo_begin, void * exchange_halo_end)
{
    for (uint64_t i_step = 0; i_step < num_steps; ++i_step) {
        stages(i0, i1, j0, j1, p_workspace,
               exchange_halo_begin, exchange_halo_end);
    }
}
