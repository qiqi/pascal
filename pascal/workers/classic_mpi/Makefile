CC = mpicxx
COPT = -O3 -g -Wall -I/usr/include/x86_64-linux-gnu
LOPT = -O3 -g -Wall -ldl

default:	main

main:	main.o
	$(CC) $(LOPT) -o $@ $^

main.o:	main.c
	$(CC) $(COPT) -c $<

clean:
	rm -f main *.so *.o
