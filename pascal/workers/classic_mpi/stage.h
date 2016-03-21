#include<inttypes.h>
#include<string.h>

typedef void (*exchange_halo_func_t)(uint64_t ni, uint64_t nj,
                                     uint64_t N, float * p);

inline void ${STAGE_NAME}(uint64_t i0, uint64_t i1, uint64_t j0, uint64_t j1,
                          float * p_workspace, void * p_b, void * p_e)
{
    const uint64_t NUM_INPUTS = ${NUM_INPUTS};
    const uint64_t NUM_OUTPUTS = ${NUM_OUTPUTS};
    const uint64_t MAX_VARS = ${MAX_VARS};

    exchange_halo_func_t exchange_halo_begin = (exchange_halo_func_t) p_b;
    exchange_halo_func_t exchange_halo_end = (exchange_halo_func_t) p_e;

    float * p_input = p_workspace;
    float * p_output = p_workspace + MAX_VARS * (i1-i0+2) * (j1-j0+2);

    for (uint64_t i = i0; i < i1; ++i)
    {
        for (uint64_t j = j0; j < j1; ++j)
        {
            const float * upstream =
                p_input + NUM_INPUTS * (j-j0+1 + (j1-j0+2) * (i-i0+1));
            const float * upstream_i_p =
                p_input + NUM_INPUTS * (j-j0+1 + (j1-j0+2) * (i-i0+2));
            const float * upstream_i_m =
                p_input + NUM_INPUTS * (j-j0+1 + (j1-j0+2) * (i-i0));
            const float * upstream_j_p =
                p_input + NUM_INPUTS * (j-j0+2 + (j1-j0+2) * (i-i0+1));
            const float * upstream_j_m =
                p_input + NUM_INPUTS * (j-j0   + (j1-j0+2) * (i-i0+2));

            float * downstream =
                p_output + NUM_OUTPUTS * (j-j0+1 + (j1-j0+2) * (i-i0+1));

            ${MAIN_CODE}
        }
    }

    exchange_halo_begin(i1-i0, j1-j0, NUM_OUTPUTS, p_output);
    exchange_halo_end(i1-i0, j1-j0, NUM_OUTPUTS, p_output);

    // swap input and output pointers
    float * p_tmp = p_input;
    p_input = p_output;
    p_output = p_tmp;
}
