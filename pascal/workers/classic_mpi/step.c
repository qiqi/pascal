${INCLUDE}
#include "hooks.h"

inline void stages(uint64_t i0, uint64_t i1, uint64_t j0, uint64_t j1,
                   float * p_w, hook_func_t p_s, hook_func_t p_r)
{
${STAGES}
}

void step_func(uint64_t i0, uint64_t i1, uint64_t j0, uint64_t j1,
               float * p_workspace, uint64_t num_steps,
               hook_func_t p_send, hook_func_t p_recv)
{
    for (uint64_t i_step = 0; i_step < num_steps; ++i_step) {
        stages(i0, i1, j0, j1, p_workspace, p_send, p_recv);
    }
}
