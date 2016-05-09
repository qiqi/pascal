#include<limits.h>
#include<assert.h>
#include<stdlib.h>
#include<stdio.h>
#include<glpk.h>

typedef struct { double rhs, pi; } v_data;
typedef struct { double low, cap, cost, x; } a_data;

#define node(v) ((v_data *)((v)->data))
#define arc(a) ((a_data *)((a)->data))

typedef struct {
    int num_vertices, num_edges;
    int * weights;
    int (*edges)[3];
    int * swept_in_degree, * in_degree, * out_degree;
    int (*cde)[3];
} c_graph_t;

void c_graph_analyze(c_graph_t * g);

void check_result(int ret, int expected) {
    if (ret != expected) {
        fprintf(stderr, "expected to read %d integers, but found %d\n",
                expected, ret);
        exit(-1);
    }
}

void c_graph_read(c_graph_t * g, FILE * f)
{
    check_result(fscanf(f, "%d %d", &g->num_vertices, &g->num_edges), 2);
    g->weights = (int*)
        malloc(sizeof(int) * (g->num_vertices + 1));
    for (int i = 0; i <= g->num_vertices; ++i)
    {
        check_result(fscanf(f, "%d", &g->weights[i]), 1);
    }
    g->edges = (int(*)[3])
        malloc(sizeof(int) * 3 * g->num_edges);
    for (int i = 0; i < g->num_edges; ++i)
    {
        check_result(fscanf(f, "%d %d %d", &g->edges[i][0],
                                           &g->edges[i][1],
                                           &g->edges[i][2]), 3);
    }
    c_graph_analyze(g);
}

void c_graph_analyze(c_graph_t * g)
{
    g->swept_in_degree = (int*) calloc(g->num_vertices, sizeof(int));
    g->in_degree = (int*) calloc(g->num_vertices, sizeof(int));
    g->out_degree = (int*) calloc(g->num_vertices, sizeof(int));

    for (int i = 0; i < g->num_edges; ++i) {
        int from_node = g->edges[i][0];
        int to_node = g->edges[i][1];
        int is_swept = g->edges[i][2];
        assert(from_node < g->num_vertices && to_node < g->num_vertices);
        assert(is_swept == 0 || is_swept == 1);
        g->out_degree[from_node] += 1;
        g->in_degree[to_node] += 1;
        g->swept_in_degree[to_node] += is_swept;
    }
}

void _quarkflow_vertex_assign(glp_vertex * v, int weight)
{
    node(v)->rhs = (double) weight;
}

glp_arc * _quarkflow_arc_create(glp_graph * glp, int i0, int i1,
                           int low, int cap, int cost)
{
    glp_arc * a = glp_add_arc(glp, i0, i1);
    arc(a)->low = (double) low;
    arc(a)->cap = (double) cap;
    arc(a)->cost = (double) cost;
    return a;
}

void _quarkflow_vertices_assemble(const c_graph_t * g, glp_graph * glp)
{
    glp_add_vertices(glp, 3 * g->num_vertices + 2);
    int w_K = g->weights[g->num_vertices];
    glp_vertex * v_0 = glp->v[1];
    glp_vertex * v_K = glp->v[glp->nv];
    _quarkflow_vertex_assign(v_0, -0*w_K);
    _quarkflow_vertex_assign(v_K, +0*w_K);
    for (int i_vertex = 0; i_vertex < g->num_vertices; ++i_vertex)
    {
        int c_i = i_vertex*3+2;
        int d_i = i_vertex*3+3;
        int e_i = i_vertex*3+4;
        glp_vertex * v_c = glp->v[c_i];
        glp_vertex * v_d = glp->v[d_i];
        glp_vertex * v_e = glp->v[e_i];
        _quarkflow_vertex_assign(v_c, +g->weights[i_vertex]);
        _quarkflow_vertex_assign(v_d, -g->weights[i_vertex]);
        _quarkflow_vertex_assign(v_e, 0);
        int is_source = g->in_degree[i_vertex] == 0;
        int is_sink = g->out_degree[i_vertex] == 0;
        if (is_source) {
            _quarkflow_arc_create(glp, 1, c_i, 0, INT_MAX/4, 0);
            _quarkflow_arc_create(glp, c_i, 1, 0, INT_MAX/4, 0);
        }
        if (is_sink) {
            int K = glp->nv;
            _quarkflow_arc_create(glp, d_i, K, 0, INT_MAX/4, 0);
            _quarkflow_arc_create(glp, K, d_i, 0, INT_MAX/4, 0);
        }
        const int cd_cost = 0;
        const int ec_cost = 1;
        const int ce_cost = -(g->swept_in_degree[i_vertex] > 0);
        _quarkflow_arc_create(glp, c_i, d_i, 0, INT_MAX/4, cd_cost);
        _quarkflow_arc_create(glp, c_i, e_i, 0, INT_MAX/4, ce_cost);
        _quarkflow_arc_create(glp, e_i, c_i, 0, INT_MAX/4, ec_cost);
    }
}

void _quarkflow_edges_assemble(const c_graph_t * g, glp_graph * glp)
{
    for (int i_edge = 0; i_edge < g->num_edges; ++i_edge) {
        int i_vertex = g->edges[i_edge][0];
        int j_vertex = g->edges[i_edge][1];
        int is_swept = g->edges[i_edge][2];
        int c_i = i_vertex*3+2;
        int d_i = i_vertex*3+3;
        int e_i = i_vertex*3+4;
        int c_j = j_vertex*3+2;
        int e_j = j_vertex*3+4;
        const int ee_cost = -is_swept;
        _quarkflow_arc_create(glp, c_i, c_j, 0, INT_MAX/4, 0);
        _quarkflow_arc_create(glp, c_j, d_i, 0, INT_MAX/4, 0);
        _quarkflow_arc_create(glp, e_i, e_j, 0, INT_MAX/4, ee_cost);
    }
}

void c_graph_quarkflow(c_graph_t * g)
{
    glp_graph * glp = glp_create_graph(sizeof(double)*2, sizeof(double)*4);
    _quarkflow_vertices_assemble(g, glp);
    _quarkflow_edges_assemble(g, glp);
    int ret_code = glp_mincost_okalg(
        glp, offsetof(v_data, rhs),
        offsetof(a_data, low), offsetof(a_data, cap), offsetof(a_data, cost),
        NULL, offsetof(a_data, x), offsetof(v_data, pi)
    );
    if (ret_code) {
        fprintf(stderr, "glp_mincost_okalg ret_code = %d\n", ret_code);
        exit(-1);
    }
    g->cde = (int(*)[3]) malloc(sizeof(int) * g->num_vertices * 3);
    int base_potential = (int)node(glp->v[1])->pi;
    for (int i_vertex = 0; i_vertex < g->num_vertices; ++i_vertex) {
        int c_i = i_vertex*3+2;
        int d_i = i_vertex*3+3;
        int e_i = i_vertex*3+4;
        g->cde[i_vertex][0] = (int)node(glp->v[c_i])->pi - base_potential;
        g->cde[i_vertex][1] = (int)node(glp->v[d_i])->pi - base_potential;
        g->cde[i_vertex][2] = (int)node(glp->v[e_i])->pi - base_potential;
    }
}

void c_graph_free(c_graph_t * g)
{
    free(g->edges);
    free(g->weights);
    free(g->swept_in_degree);
    free(g->in_degree);
    free(g->out_degree);
    free(g->cde);
}

int main()
{
    c_graph_t c_graph;
    c_graph_read(&c_graph, stdin);
    c_graph_quarkflow(&c_graph);
    {
        c_graph_t * g = &c_graph;
        for (int i = 0; i < g->num_vertices; ++i) {
            printf("%d %d %d %d\n", i, g->cde[i][0], g->cde[i][1], g->cde[i][2]);
        }
    }

    c_graph_free(&c_graph);
}
