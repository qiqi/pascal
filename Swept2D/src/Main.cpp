// This file is part of Swept2D
// Copyright (C) 2015 Qiqi Wang, qiqi@mit.edu AND Maitham Alhubail, hubailmm@mit.edu
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) an later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT An WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

#include "Main.h"

int main(int argc,char *argv[])
{
	n                 = atoi(argv[1]);
	const int xNodes  = atoi(argv[2]);
	const int yNodes  = atoi(argv[3]);
	cycles            = 100000;//atoi(argv[4]);	
	int port          = 30000;//atoi(argv[5]);
	convergenceCheckEvery = 1;
	totalGlobals = 6;
	fileOutputEvery   = 5;

	initMPI(argc,argv,xNodes,yNodes,false,port);
	double ellapsed;
        swept2d = new SweptDiscretization2D(n,8,48,2,0,0);    
	Substeps2D::setInitParameters(xNodes*n,yNodes*n);
	swept2d->setOutputDirectory(outputDirectory);
	swept2d->setFileOutput(fileOutputEvery);

    if(totalGlobals > 0)
    {
        globals = new double[totalGlobals];
        Substeps2D::setGlobalVariables(xNodes*n,yNodes*n);
    }
	
	for(int i=0;i<8;i++)
		localCount[i] = 0;
    stepCount[0]  = 0;
	swept2d->setInitCondition(Substeps2D::init);
	printf("\n");
	ellapsed = MPI_Wtime();
	swept2d->calculate(cycles);
	ellapsed = MPI_Wtime() - ellapsed;
	printf("Swept: Total Substeps: %d - us per substep: %f\n",cycles*n,ellapsed*1000000/(cycles*n));
	
	for(int i=0;i<8;i++)
		printf("Substep %d Function Calls: %ld\n",i,localCount[i]);
			finMPI();
	return 0;
}
