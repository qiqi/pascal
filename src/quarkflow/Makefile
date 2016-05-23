default:	../../bin/quarkflow

../../bin/quarkflow:	quarkflow.o compgraph.o
	gcc -Wall --std=c99 -O3 $^ -o $@ -lglpk

%.o:	%.c compgraph.h
	gcc -Wall --std=c99 -O3 $<
