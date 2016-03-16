#ifndef CLASSIC_MPI_WORKER_HOOKS_H
#define CLASSIC_MPI_WORKER_HOOKS_H

typedef void (*hook_func_t)(
            uint64_t n, float * im, float * ip, float * jm, float * jp);
typedef void (*step_func_t)(
            uint64_t i0, uint64_t i1, uint64_t j0, uint64_t j1,
            float * p_workspace, uint64_t num_steps,
            hook_func_t p_send, hook_func_t p_recv);

void send(uint64_t n, float * im, float * ip, float * jm, float * jp);
void recv(uint64_t n, float * im, float * ip, float * jm, float * jp);

#endif
