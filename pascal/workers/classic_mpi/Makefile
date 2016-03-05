CC = mpicc
COPT = -O3 -std=c99
LOPT = -O3

worker:	main.o
	$(CC) $(LOPT) -o $@ $^

main.o:	main.c
	$(CC) $(COPT) -c $<
