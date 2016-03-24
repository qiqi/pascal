CC = mpicxx
COPT = -O3 -g -Wall -I/usr/include/x86_64-linux-gnu
LOPT = -O3 -g -Wall -ldl

default:	main

main:	main.o exchange_halo.o job.o
	$(CC) $(LOPT) -o $@ $^

main.o:	main.cpp exchange_halo.h job.h
	$(CC) $(COPT) -c $<

job.o:	job.cpp job.h
	$(CC) $(COPT) -c $<

exchange_halo.o:	exchange_halo.c exchange_halo.h
	$(CC) $(COPT) -c $<

clean:
	rm -f main *.so *.o
