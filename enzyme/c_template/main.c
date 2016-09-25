#include<math.h>
#include<stdio.h>
#include<inttypes.h>
#include<string.h>
#include<stdlib.h>

#include "workspace.h"
${INCLUDE}

const int64_t NI = ${NI};
const int64_t NJ = ${NJ};
const int64_t NK = ${NK};
const uint64_t MAX_VARS = ${MAX_VARS};
const uint64_t NUM_INPUTS = ${NUM_INPUTS};
const uint64_t NUM_OUTPUTS = ${NUM_OUTPUTS};
const uint64_t NUM_CONSTS = ${NUM_CONSTS};

void update_halo(double * p, uint64_t n)
{
    FOR_IJ {
        memcpy(p+OFFSET(i,j,-1,n), p+OFFSET(i,j,NK-1,n), n*sizeof(double));
        memcpy(p+OFFSET(i,j,NK,n), p+OFFSET(i,j,0,n), n*sizeof(double));
    }
    FOR_IK {
        memcpy(p+OFFSET(i,-1,k,n), p+OFFSET(i,NJ-1,k,n), n*sizeof(double));
        memcpy(p+OFFSET(i,NJ,k,n), p+OFFSET(i,0,k,n), n*sizeof(double));
    }
    FOR_JK {
        memcpy(p+OFFSET(-1,j,k,n), p+OFFSET(NI-1,j,k,n), n*sizeof(double));
        memcpy(p+OFFSET(NI,j,k,n), p+OFFSET(0,j,k,n), n*sizeof(double));
    }
}

void workspace_init(Workspace * p)
{
    int64_t n_grid = (NI+2)*(NJ+2)*(NK+2);
    int64_t n_floats_per_grid = MAX_VARS * 2 + NUM_CONSTS;
    p->workspace = (double *)malloc(sizeof(double)*n_grid*n_floats_per_grid);
    p->input_workspace = p->workspace;
    p->output_workspace = p->workspace + n_grid*MAX_VARS;
    p->const_workspace = p->workspace + n_grid*MAX_VARS*2;

    int r = fread(p->workspace, sizeof(double), NI*NJ*NK*NUM_CONSTS, stdin);
    FOR_IJK_reversed {
        double * src = p->workspace + NUM_CONSTS * (k + j*NK + i*NK*NJ);
        double * dest = p->const_workspace + OFFSET(i,j,k,NUM_CONSTS);
        memcpy(dest, src, NUM_CONSTS * sizeof(double));
    }
    update_halo(p->const_workspace, NUM_CONSTS);

    r = fread(p->workspace, sizeof(double), NI*NJ*NK*NUM_INPUTS, stdin);
    FOR_IJK {
        double * src = p->workspace + NUM_INPUTS * (k + j*NK + i*NK*NJ);
        double * dest = p->output_workspace + OFFSET(i,j,k,NUM_INPUTS);
        memcpy(dest, src, NUM_INPUTS * sizeof(double));
    }
}

void workspace_swap_sync(Workspace * p, uint64_t n)
{
    double * output = p->input_workspace;
    double * src = p->output_workspace;
    p->input_workspace = src;
    p->output_workspace = output;
    update_halo(src, n);
}

void workspace_finalize(Workspace * p)
{
    FOR_IJK {
        double * src = p->output_workspace + OFFSET(i,j,k,NUM_OUTPUTS);
        double * dest = p->input_workspace + NUM_OUTPUTS * (k+j*NK+i*NK*NJ);
        memcpy(dest, src, NUM_OUTPUTS * sizeof(double));
    }
    int r = fwrite(p->input_workspace, sizeof(double),
                   NI*NJ*NK*NUM_OUTPUTS, stdout);
}

int main()
{
    Workspace buf;
    workspace_init(&buf);
    ${STAGES}
    workspace_finalize(&buf);
}
