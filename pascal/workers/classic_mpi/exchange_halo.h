#include<inttypes.h>

void set_neighbor_ranks(uint64_t ranks[4]);

void exchange_halo_begin(uint64_t ni, uint64_t nj, uint64_t N, float * p);
void exchange_halo_end(uint64_t ni, uint64_t nj, uint64_t N, float * p);
