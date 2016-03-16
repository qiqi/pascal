#include<inttypes.h>

#include "hooks.h"

void step_func(uint64_t i0, uint64_t i1, uint64_t j0, uint64_t j1,
               float * p_workspace, uint64_t num_steps,
               hook_func_t p_send, hook_func_t p_recv)
{
    for (int i_step = 0; i_step < num_steps; ++i_step) {
        // AN ATOMIC STAGE //
    }
}
