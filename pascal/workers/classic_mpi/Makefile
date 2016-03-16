CC = mpicxx
COPT = -O3 -Wall -I/usr/include/x86_64-linux-gnu
LOPT = -O3 -Wall -ldl

worker:	main.o hooks.o
	$(CC) $(LOPT) -o $@ $^

main.o:	main.c hooks.h
	$(CC) $(COPT) -c $<

hooks.o:	hooks.c hooks.h
	$(CC) $(COPT) -c $<

step.o:	step.c hooks.h
	$(CC) $(COPT) -c $<

clean:
	rm -f worker *.o
