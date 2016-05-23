default:	bin
	cd src/quarkflow; make

bin:
	mkdir bin

clean:
	rm bin/quarkflow
