#include<math.h>
#include<inttypes.h>
#include<string.h>

void ${STAGE_NAME}(uint64_t NI, uint64_t NJ, uint64_t NK, Workspace * p)
{
    const uint64_t NUM_INPUTS = ${NUM_INPUTS};
    const uint64_t NUM_OUTPUTS = ${NUM_OUTPUTS};
    const uint64_t MAX_VARS = ${MAX_VARS};

    workspace_swap_sync(p, NUM_INPUTS);

    double * p_source = p->source_workspace;
    double * p_sink = p->sink_workspace;

    FOR_IJK {
        const double * source =    p_source + OFFSET(i,  j,k,NUM_INPUTS);
        const double * source_ip = p_source + OFFSET(i+1,j,k,NUM_INPUTS);
        const double * source_im = p_source + OFFSET(i-1,j,k,NUM_INPUTS);
        const double * source_jp = p_source + OFFSET(i,j+1,k,NUM_INPUTS);
        const double * source_jm = p_source + OFFSET(i,j-1,k,NUM_INPUTS);
        const double * source_kp = p_source + OFFSET(i,j,k+1,NUM_INPUTS);
        const double * source_km = p_source + OFFSET(i,j,k-1,NUM_INPUTS);
        double * sink = p_sink + OFFSET(i,j,k,NUM_OUTPUTS);
        ${CODE}
    }
}
