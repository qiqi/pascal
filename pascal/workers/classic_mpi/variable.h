#include<inttypes.h>

#include<mpi.h>

class Variable {
    private:

    uint64_t id_;
    uint64_t size_;
    uint64_t ni_;
    uint64_t nj_;
    float * data_;

    public:

    Variable(uint64_t id, uint64_t size, uint64_t ni, uint64_t nj);
    void receive(MPI_Comm comm);
    void send(MPI_Comm comm) const;
    void copy_to_workspace(float * p_workspace) const;
    void copy_from_workspace(float * p_workspace);
    ~Variable();
};
