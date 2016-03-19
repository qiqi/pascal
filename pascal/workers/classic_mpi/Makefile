CC = mpicxx
COPT = -O3 -Wall -I/usr/include/x86_64-linux-gnu
LOPT = -O3 -Wall -ldl

default:	main

main:	main.o
	$(CC) $(LOPT) -o $@ $^

main.o:	main.c hooks.h
	$(CC) $(COPT) -c $<

clean:
	rm -f main *.so *.o
