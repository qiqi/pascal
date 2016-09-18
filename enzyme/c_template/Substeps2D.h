// This file is part of Swept2D
// Copyright (C) 2015 Qiqi Wang, qiqi@mit.edu AND Maitham Alhubail, hubailmm@mit.edu
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) an later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT Any WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

#ifndef H_SUBSTEPS2D
#define H_SUBSTEPS2D

#include <math.h>
#include <stdlib.h>
#include "Swept2DGlobals.h"

extern void printHex(double a);

class Substeps2D
{


public:

	$STAGE_INCLUDE
	static inline void executeStepFnc(int executeFnc,PointStruct2D *point)
	{
		$STAGE_CALL	
		localCount[executeFnc]++;				
	}

	static void setGlobalVariables(int nx,int ny)
	{
		double gamma = 1.4;
		double R     = 287.;
		double T0    = 300.;
		double p0    = 101325.;
		double M0    = 0.25;
		double c0    = sqrt(gamma * R * T0);
		const double rho0 = p0 / (R * T0);  
		const double u0   = c0 * M0;  
		
		globals[0] = sqrt(rho0);
		globals[1] = sqrt(rho0) * u0;
		globals[2] = sqrt(rho0) * 0.0;
		globals[3] = p0;
		globals[4] = nx;
		globals[5] = ny;

		
		if(pg.rank ==0)printf("Global Variables Setup DONE! Nx = %d , Ny = %d\n",nx,ny);
	}

	static void setInitParameters(int nx,int ny)
	{
		//PARAMETERS SETUP
		totalGlobals = 6;
		//constants = 2;		
		
		//OUTPUT SETUP AND CONTROL
		outputDirectory = ".";
		//fileOutputEvery = 1;
		
		//CONSERVATION SETUP AND CONTROL		
		convergenceCheckEvery = 10;

		//SIMULATION SETUP
		lx = .05*nx;
		ly = .05*ny;		
		dx = lx/nx;		
		dy = ly/ny;
	}		
};

#endif
