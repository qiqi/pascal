#include<math.h>
#include<inttypes.h>
#include<string.h>

inline void ${STAGE_NAME}(uint64_t NI, uint64_t NJ, uint64_t NK, Workspace * p)
{
    const uint64_t NUM_INPUTS = ${NUM_INPUTS};
    const uint64_t NUM_OUTPUTS = ${NUM_OUTPUTS};
    const uint64_t MAX_VARS = ${MAX_VARS};

    float * p_source = p->source_workspace;
    float * p_sink = p->sink_workspace;

    FOR_IJK {
        const float * source =    p_source + OFFSET(i,  j,k,NUM_INPUTS);
        const float * source_ip = p_source + OFFSET(i+1,j,k,NUM_INPUTS);
        const float * source_im = p_source + OFFSET(i-1,j,k,NUM_INPUTS);
        const float * source_jp = p_source + OFFSET(i,j+1,k,NUM_INPUTS);
        const float * source_jm = p_source + OFFSET(i,j-1,k,NUM_INPUTS);
        const float * source_kp = p_source + OFFSET(i,j,k+1,NUM_INPUTS);
        const float * source_km = p_source + OFFSET(i,j,k-1,NUM_INPUTS);
        float * sink = p_sink + OFFSET(i,j,k,NUM_OUTPUTS);
        ${CODE}
    }

    workspace_swap(p, NUM_OUTPUTS);
}
