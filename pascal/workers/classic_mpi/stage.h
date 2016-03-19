#include<inttypes.h>
#include<string.h>

#include "hooks.h"

void inline ${STAGE_NAME}(uint64_t i0, uint64_t i1, uint64_t j0, uint64_t j1,
                       float * p_workspace,
                       hook_func_t p_send, hook_func_t p_recv)
{
    const uint64_t NUM_INPUTS = ${NUM_INPUTS};
    const uint64_t NUM_OUTPUTS = ${NUM_OUTPUTS};
    const uint64_t MAX_VARS = ${MAX_VARS};

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

    float sendbuf_ip[(j1-j0)*NUM_OUTPUTS];
    float sendbuf_im[(j1-j0)*NUM_OUTPUTS];
    float sendbuf_jp[(i1-i0)*NUM_OUTPUTS];
    float sendbuf_jm[(i1-i0)*NUM_OUTPUTS];

    for (uint64_t i = i0; i < i1; ++i) {
        memcpy(sendbuf_jp + (i-i0) * NUM_OUTPUTS,
               p_output + NUM_OUTPUTS * (1 + (j1-j0+2) * (i-i0+1)),
               sizeof(float) * NUM_OUTPUTS);
        memcpy(sendbuf_jm + (i-i0) * NUM_OUTPUTS,
               p_output + NUM_OUTPUTS * (j1-j0 + (j1-j0+2) * (i-i0+1)),
               sizeof(float) * NUM_OUTPUTS);
    }
    for (uint64_t j = i0; j < j1; ++j) {
        memcpy(sendbuf_ip + (j-j0) * NUM_OUTPUTS,
               p_output + NUM_OUTPUTS * (j-j0+1 + (j1-j0+2) * 1),
               sizeof(float) * NUM_OUTPUTS);
        memcpy(sendbuf_im + (j-j0) * NUM_OUTPUTS,
               p_output + NUM_OUTPUTS * (j-j0+1 + (j1-j0+2) * (i1-i0)),
               sizeof(float) * NUM_OUTPUTS);
    }
    p_send(NUM_OUTPUTS, sendbuf_im, sendbuf_ip, sendbuf_jm, sendbuf_jp);

    float recvbuf_ip[(j1-j0)*NUM_OUTPUTS];
    float recvbuf_im[(j1-j0)*NUM_OUTPUTS];
    float recvbuf_jp[(i1-i0)*NUM_OUTPUTS];
    float recvbuf_jm[(i1-i0)*NUM_OUTPUTS];

    p_recv(NUM_OUTPUTS, recvbuf_im, recvbuf_ip, recvbuf_jm, recvbuf_jp);

    for (uint64_t i = i0; i < i1; ++i) {
        memcpy(p_output + NUM_OUTPUTS * (0 + (j1-j0+2) * (i-i0+1) * 1),
               recvbuf_jp + (i-i0) * NUM_OUTPUTS,
               sizeof(float) * NUM_OUTPUTS);
        memcpy(p_output + NUM_OUTPUTS * (j1-j0+1 + (j1-j0+2) * (i-i0+1)),
               recvbuf_jm + (i-i0) * NUM_OUTPUTS,
               sizeof(float) * NUM_OUTPUTS);
    }
    for (uint64_t j = i0; j < j1; ++j) {
        memcpy(p_output + NUM_OUTPUTS * (j-j0+1 + (j1-j0+2) * 0),
               recvbuf_ip + (j-j0) * NUM_OUTPUTS,
               sizeof(float) * NUM_OUTPUTS);
        memcpy(p_output + NUM_OUTPUTS * (j-j0+1 + (j1-j0+2) * (i1-i0+1)),
               recvbuf_im + (j-j0) * NUM_OUTPUTS,
               sizeof(float) * NUM_OUTPUTS);
    }

    // swap input and output pointers
    float * p_tmp = p_input;
    p_input = p_output;
    p_output = p_tmp;
}


