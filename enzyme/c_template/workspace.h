#ifndef C_TEMPLATE_COMMON_H
#define C_TEMPLATE_COMMON_H

typedef struct {
    float * workspace;
    float * source_workspace;
    float * sink_workspace;
} Workspace;

void workspace_init(Workspace * p);
void workspace_swap(Workspace * p, uint64_t n);
void workspace_finalize(Workspace * p);

#define FOR_IJK for (int64_t i = 1; i <= NI; ++i) \
                for (int64_t j = 1; j <= NJ; ++j) \
                for (int64_t k = 1; k <= NK; ++k)
#define FOR_IJ for (int64_t i = 1; i <= NI; ++i) \
               for (int64_t j = 1; j <= NJ; ++j)
#define FOR_IK for (int64_t i = 1; i <= NI; ++i) \
               for (int64_t k = 1; k <= NK; ++k)
#define FOR_JK for (int64_t j = 1; j <= NJ; ++j) \
               for (int64_t k = 1; k <= NK; ++k)
#define OFFSET(i,j,k,n) n * (k+1 + (NK+2)*(j+1 + (NJ+2)*(i+1)))


#endif
