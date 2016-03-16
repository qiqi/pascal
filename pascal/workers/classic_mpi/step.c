#include<inttypes.h>

#include "hooks.h"

const uint64_t MAX_VARS = 10;//SUBSTITUTE

void step_func(uint64_t i0, uint64_t i1, uint64_t j0, uint64_t j1,
               float * p_workspace, uint64_t num_steps,
               hook_func_t p_send, hook_func_t p_recv)
{
    float * p_input = p_workspace;
    float * p_output = p_workspace + MAX_VARS * (i1-i0+2) * (j1-j0+2);
    for (uint64_t i_step = 0; i_step < num_steps; ++i_step) {
        // BEGIN_ATOMIC_STAGE //
        const uint64_t NUM_INPUTS = 10;//SUBSTITUTE
        const uint64_t NUM_OUTPUTS = 10;//SUBSTITUTE

        for (uint64_t i = i0; i < i1; ++i)
        {
            for (uint64_t j = j0; j < j1; ++j)
            {
                const float * upstream =
                    p_input + NUM_INPUTS * (j-j0+1 + (i1-i0+2) * (i-i0+1));
                const float * upstream_i_p =
                    p_input + NUM_INPUTS * (j-j0+1 + (i1-i0+2) * (i-i0+2));
                const float * upstream_i_m =
                    p_input + NUM_INPUTS * (j-j0+1 + (i1-i0+2) * (i-i0));
                const float * upstream_j_p =
                    p_input + NUM_INPUTS * (j-j0+2 + (i1-i0+2) * (i-i0+1));
                const float * upstream_j_m =
                    p_input + NUM_INPUTS * (j-j0   + (i1-i0+2) * (i-i0+2));

                float * downstream =
                    p_output + NUM_OUTPUTS * (j-j0+1 + (i1-i0+2) * (i-i0+1));
                float * downstream_i_p =
                    p_output + NUM_OUTPUTS * (j-j0+1 + (i1-i0+2) * (i-i0+2));
                float * downstream_i_m =
                    p_output + NUM_OUTPUTS * (j-j0+1 + (i1-i0+2) * (i-i0));
                float * downstream_j_p =
                    p_output + NUM_OUTPUTS * (j-j0+2 + (i1-i0+2) * (i-i0+1));
                float * downstream_j_m =
                    p_output + NUM_OUTPUTS * (j-j0   + (i1-i0+2) * (i-i0+2));

                //MAIN_CODE
            }
        }

        float buffer_i_p[(j1-j0)*NUM_OUTPUTS];
        float buffer_i_m[(j1-j0)*NUM_OUTPUTS];
        float buffer_j_p[(i1-i0)*NUM_OUTPUTS];
        float buffer_j_m[(i1-i0)*NUM_OUTPUTS];

        for (uint64_t i = i0; i < i1; ++i) {
            memcpy(buffer_j_p);
            memcpy(buffer_j_m);
        }
        for (uint64_t j = i0; j < j1; ++j) {
            memcpy(buffer_i_p);
            memcpy(buffer_i_m);
        }
        p_send();

        // swap input and output pointers
        float * p_tmp = p_input;
        p_input = p_output;
        p_output = p_tmp;
        // END_ATOMIC_STAGE //
    }
}
