#pragma once

#include<stdio.h>

typedef struct {
    int from_node;
    int to_node;
    int is_swept;
} comp_graph_edge_t;

typedef struct {
    int num_vertices, num_edges;
    int * cutting_cost;
    comp_graph_edge_t * edges;
    int * swept_in_degree, * in_degree, * out_degree;
    int (*cde)[3];
} comp_graph_t;

void comp_graph_read(comp_graph_t * g, FILE * f);
void comp_graph_read_quarkflow(comp_graph_t * g, FILE * f);
void comp_graph_write_quarkflow(comp_graph_t * g, FILE * f);
void comp_graph_free(comp_graph_t * g);
