#include<stdlib.h>
#include<string.h>

#include "variable.h"

Variable::Variable(uint64_t id, uint64_t size, uint64_t ni, uint64_t nj)
    : id_(id), size_(size), ni_(ni), nj_(nj)
{
    data_ = (float*) malloc(sizeof(double) * size * ni * nj);
}

void Variable::receive(MPI_Comm comm)
{
    uint64_t size = size_ * ni_ * nj_;
    MPI_Scatter(0, 0, 0, data_, size, MPI_FLOAT, 0, comm);
}

void Variable::send(MPI_Comm comm) const
{
    uint64_t size = size_ * ni_ * nj_;
    MPI_Gather(data_, size, MPI_FLOAT, NULL, 0, MPI_FLOAT, 0, comm);
}

void Variable::copy_to_workspace(float * p_workspace) const
{
    for (uint64_t i = 0; i < ni_; ++i) {
        for (uint64_t j = 0; j < nj_; ++j) {
            uint64_t ind_src = i * nj_ + j;
            uint64_t ind_des = (i + 1) * (nj_ + 2) + (j + 1);
            float * p_src = data_ + ind_src * size_;
            float * p_des = p_workspace + ind_des * size_;
            memcpy(p_des, p_src, sizeof(float) * size_);
        }
    }
}

void Variable::copy_from_workspace(float * p_workspace)
{
    for (uint64_t i = 0; i < ni_; ++i) {
        for (uint64_t j = 0; j < nj_; ++j) {
            uint64_t ind_des = i * nj_ + j;
            uint64_t ind_src = (i + 1) * (nj_ + 2) + (j + 1);
            float * p_des = data_ + ind_des * size_;
            float * p_src = p_workspace + ind_src * size_;
            memcpy(p_des, p_src, sizeof(float) * size_);
        }
    }
}

Variable::~Variable()
{
    if (data_) {
        free(data_);
    }
}

