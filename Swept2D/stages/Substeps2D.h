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

	#include "stage_0.h"
	#include "stage_1.h"
	#include "stage_2.h"
	#include "stage_3.h"
	#include "stage_4.h"
	#include "stage_5.h"
	#include "stage_6.h"
	#include "stage_7.h"
	
	static inline void executeStepFnc(int executeFnc,PointStruct2D *point)
	{
		if(executeFnc == 0)
			stage_0(point);
		else if(executeFnc == 1)
			stage_1(point);
		else if(executeFnc == 2)
			stage_2(point);
		else if(executeFnc == 3)
			stage_3(point);
		else if(executeFnc == 4)
			stage_4(point);
		else if(executeFnc == 5)
			stage_5(point);
		else if(executeFnc == 6)
			stage_6(point);
		else if(executeFnc == 7)
			stage_7(point);
	
		localCount[executeFnc]++;				
	}


	static void init(int i,int j,InitPoint2D *point)
	{
		const double PI = atan(1.0) * 4;
		double x = (i + 0.5) * dx - 0.2 * lx;
		double y = (j + 0.5) * dy - 0.5 * ly;
		double obs = exp(-pow((x*x + (y-.25*dy)*(y-.25*dy))/.01,8));
		point->U_constants[0] = obs;
		double fan = 2 * (pow(cos((x / lx + 0.2) * PI),64) + pow(sin((y / ly) * PI),64));
		point->U_constants[1] = fan;

		//double dc = pow(cos((x / lx + 0.2) * PI),64);
		//point->U_constants[1] = dc;
		point->U_constants[0] = 0;
		if(i==globals[4]/4 && j==globals[5]/2)
			point->U_constants[0] = 1;
		else if(i==globals[4]/4 + 1 && j==globals[5]/2 + 1)
			point->U_constants[0] = 1;
		else if(i==globals[4]/4 + 1 && j==globals[5]/2)
			point->U_constants[0] = 1;
		else if(i==globals[4]/4 && j==globals[5]/2 + 1)
			point->U_constants[0] = 1;

		point->U_constants[0] = obs;

		for (int ii = 0; ii < 4; ++ii) 
		{
			point->U_input[ii] = globals[ii];			
		}
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
