CC = mpicxx
COPT = -O3 -Wall -std=c99 -I/usr/include/x86_64-linux-gnu
LOPT = -O3 -Wall -ldl

worker:	main.o
	$(CC) $(LOPT) -o $@ $^

main.o:	main.c
	$(CC) $(COPT) -c $<

clean:
	rm -f worker *.o
