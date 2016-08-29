#include<stdlib.h>
#include"compgraph.h"

void check_result(int ret, int expected) {
    if (ret != expected) {
        fprintf(stderr, "expected to read %d integers, but found %d\n",
                expected, ret);
        exit(-1);
    }
}

void comp_graph_read(comp_graph_t * g, FILE * f)
{
    check_result(fscanf(f, "%d %d", &g->num_vertices, &g->num_edges), 2);
    g->cutting_cost = (int*)
        malloc(sizeof(int) * (g->num_vertices + 1));
    for (int i = 0; i <= g->num_vertices; ++i)
    {
        check_result(fscanf(f, "%d", &g->cutting_cost[i]), 1);
    }
    g->edges = (comp_graph_edge_t *)
        malloc(sizeof(comp_graph_edge_t) * g->num_edges);
    for (int i = 0; i < g->num_edges; ++i)
    {
        check_result(fscanf(f, "%d %d %d", &g->edges[i].from_node,
                                           &g->edges[i].to_node,
                                           &g->edges[i].is_swept), 3);
    }

    g->swept_in_degree = (int*) calloc(g->num_vertices, sizeof(int));
    g->in_degree = (int*) calloc(g->num_vertices, sizeof(int));
    g->out_degree = (int*) calloc(g->num_vertices, sizeof(int));
    g->cde = (int(*)[3]) malloc(sizeof(int) * g->num_vertices * 3);
}

void comp_graph_free(comp_graph_t * g)
{
    free(g->edges);
    free(g->cutting_cost);
    free(g->swept_in_degree);
    free(g->in_degree);
    free(g->out_degree);
    free(g->cde);
}

void comp_graph_write_quarkflow(comp_graph_t * g, FILE * f)
{
    for (int i = 0; i < g->num_vertices; ++i) {
        fprintf(f, "%d %d %d\n", g->cde[i][0], g->cde[i][1], g->cde[i][2]);
    }
}

void comp_graph_read_quarkflow(comp_graph_t * g, FILE * f)
{
    for (int i = 0; i < g->num_vertices; ++i) {
        if (fscanf(f, "%d %d %d\n",
                   &g->cde[i][0], &g->cde[i][1], &g->cde[i][2]) != 3)
        {
             exit(-1);
        }
    }
}
