CC = mpicxx
COPT = -O3 -Wall -I/usr/include/x86_64-linux-gnu
LOPT = -O3 -Wall -ldl

default:	main step.so

step.so:	step.o
	$(CC) $(LOPT) --shared -o $@ $^

main:	main.o
	$(CC) $(LOPT) -o $@ $^

main.o:	main.c hooks.h
	$(CC) $(COPT) -c $<

step.o:	step.c hooks.h
	$(CC) $(COPT) --PIC -c $<

clean:
	rm -f main *.so *.o
