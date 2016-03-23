#include<stdlib.h>
#include<string.h>
#include<mpi.h>

#include "exchange_halo.h"

uint64_t global_exchange_buffer_bytes = 0;
float * global_exchange_buffer = NULL;
MPI_Request global_mpi_send_requests[4];
MPI_Request global_mpi_recv_requests[4];

int global_rank_i_m;
int global_rank_i_p;
int global_rank_j_m;
int global_rank_j_p;

void set_neighbor_ranks(uint64_t ranks[4])
{
    global_rank_i_m = ranks[0];
    global_rank_i_p = ranks[1];
    global_rank_j_m = ranks[2];
    global_rank_j_p = ranks[3];
}

void exchange_halo_begin(uint64_t ni, uint64_t nj, uint64_t N, float * p)
{
    uint64_t required_bytes = sizeof(float) * N * (ni + nj) * 4;
    if (required_bytes > global_exchange_buffer_bytes) {
        if (global_exchange_buffer != NULL) {
            free(global_exchange_buffer);
        }
        global_exchange_buffer = (float*)malloc(required_bytes);
        global_exchange_buffer_bytes = required_bytes;
    }

    float * sendbuf_ip = global_exchange_buffer;
    float * sendbuf_im = sendbuf_ip + N * nj;
    float * sendbuf_jp = sendbuf_im + N * nj;
    float * sendbuf_jm = sendbuf_jp + N * ni;
    float * recvbuf_ip = sendbuf_jm + N * ni;
    float * recvbuf_im = recvbuf_ip + N * nj;
    float * recvbuf_jp = recvbuf_im + N * nj;
    float * recvbuf_jm = recvbuf_jp + N * ni;

    const int tag_i_forward = 1;
    const int tag_i_backward = 2;
    const int tag_j_forward = 3;
    const int tag_j_backward = 4;

    MPI_Irecv(recvbuf_ip, N * nj, MPI_FLOAT, global_rank_i_p,
              tag_i_backward, MPI_COMM_WORLD, &global_mpi_recv_requests[0]);
    MPI_Irecv(recvbuf_im, N * nj, MPI_FLOAT, global_rank_i_m,
              tag_i_forward, MPI_COMM_WORLD, &global_mpi_recv_requests[1]);
    MPI_Irecv(recvbuf_jp, N * ni, MPI_FLOAT, global_rank_j_p,
              tag_j_backward, MPI_COMM_WORLD, &global_mpi_recv_requests[2]);
    MPI_Irecv(recvbuf_jm, N * ni, MPI_FLOAT, global_rank_j_m,
              tag_j_forward, MPI_COMM_WORLD, &global_mpi_recv_requests[3]);

    for (uint64_t i = 0; i < ni; ++i) {
        memcpy(sendbuf_jp + i * N,
               p + N * (1 + (nj+2) * (i+1)), sizeof(float) * N);
        memcpy(sendbuf_jm + i * N,
               p + N * (nj + (nj+2) * (i+1)), sizeof(float) * N);
    }
    for (uint64_t j = 0; j < nj; ++j) {
        memcpy(sendbuf_ip + j * N,
               p + N * (j+1 + (nj+2) * 1), sizeof(float) * N);
        memcpy(sendbuf_im + j * N,
               p + N * (j+1 + (nj+2) * ni), sizeof(float) * N);
    }

    MPI_Isend(sendbuf_ip, N * nj, MPI_FLOAT, global_rank_i_p,
              tag_i_forward, MPI_COMM_WORLD, &global_mpi_send_requests[0]);
    MPI_Isend(sendbuf_im, N * nj, MPI_FLOAT, global_rank_i_m,
              tag_i_backward, MPI_COMM_WORLD, &global_mpi_send_requests[1]);
    MPI_Isend(sendbuf_jp, N * ni, MPI_FLOAT, global_rank_j_p,
              tag_j_forward, MPI_COMM_WORLD, &global_mpi_send_requests[2]);
    MPI_Isend(sendbuf_jm, N * ni, MPI_FLOAT, global_rank_j_m,
              tag_j_backward, MPI_COMM_WORLD, &global_mpi_send_requests[3]);
}

void exchange_halo_end(uint64_t ni, uint64_t nj, uint64_t N, float * p)
{
    MPI_Status statuses[4];
    MPI_Waitall(4, global_mpi_recv_requests, statuses);

    float * recvbuf = global_exchange_buffer + N * (ni + nj) * 2;
    float * recvbuf_ip = recvbuf    + N * ni;
    float * recvbuf_im = recvbuf_ip + N * nj;
    float * recvbuf_jp = recvbuf_im + N * nj;
    float * recvbuf_jm = recvbuf_jp + N * ni;

    for (uint64_t i = 0; i < ni; ++i) {
        memcpy(p + N * (0 + (nj+2) * (i+1) * 1),
               recvbuf_jp + i * N, sizeof(float) * N);
        memcpy(p + N * (nj+1 + (nj+2) * (i+1)),
               recvbuf_jm + i * N, sizeof(float) * N);
    }
    for (uint64_t j = 0; j < ni; ++j) {
        memcpy(p + N * (j+1 + (nj+2) * 0),
               recvbuf_ip + j * N, sizeof(float) * N);
        memcpy(p + N * (j+1 + (nj+2) * (ni+1)),
               recvbuf_im + j * N, sizeof(float) * N);
    }

    MPI_Waitall(4, global_mpi_send_requests, statuses);
}

