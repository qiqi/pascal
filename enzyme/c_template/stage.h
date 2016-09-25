#include<math.h>
#include<inttypes.h>
#include<string.h>

void ${STAGE_NAME}(uint64_t NI, uint64_t NJ, uint64_t NK, Workspace * p)
{
    const uint64_t NUM_INPUTS = ${NUM_INPUTS};
    const uint64_t NUM_CONSTS = ${NUM_CONSTS};
    const uint64_t NUM_OUTPUTS = ${NUM_OUTPUTS};

    workspace_swap_sync(p, NUM_INPUTS);

    double * p_input = p->input_workspace;
    double * p_const = p->const_workspace;
    double * p_output = p->output_workspace;

    FOR_IJK {
        const double * input =    p_input + OFFSET(i,  j,k,NUM_INPUTS);
        const double * input_ip = p_input + OFFSET(i+1,j,k,NUM_INPUTS);
        const double * input_im = p_input + OFFSET(i-1,j,k,NUM_INPUTS);
        const double * input_jp = p_input + OFFSET(i,j+1,k,NUM_INPUTS);
        const double * input_jm = p_input + OFFSET(i,j-1,k,NUM_INPUTS);
        const double * input_kp = p_input + OFFSET(i,j,k+1,NUM_INPUTS);
        const double * input_km = p_input + OFFSET(i,j,k-1,NUM_INPUTS);
        const double * consts =    p_const + OFFSET(i,  j,k,NUM_CONSTS);
        const double * consts_ip = p_const + OFFSET(i+1,j,k,NUM_CONSTS);
        const double * consts_im = p_const + OFFSET(i-1,j,k,NUM_CONSTS);
        const double * consts_jp = p_const + OFFSET(i,j+1,k,NUM_CONSTS);
        const double * consts_jm = p_const + OFFSET(i,j-1,k,NUM_CONSTS);
        const double * consts_kp = p_const + OFFSET(i,j,k+1,NUM_CONSTS);
        const double * consts_km = p_const + OFFSET(i,j,k-1,NUM_CONSTS);
        double * output = p_output + OFFSET(i,j,k,NUM_OUTPUTS);
        ${CODE}
    }
}
