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

#ifndef H_SWEPT2DGLOBALS
#define H_SWEPT2DGLOBALS
#include "ProcessGraph.h"
#include "Swept2DUtils.h"
#include <string.h>
#include <string>

using namespace std;
extern ProcessGraph pg;
extern long stepCount[100] , localCount[100];
extern int constants;;
extern int remoteConstants;
extern int substeps;
extern int dataPointSize;
extern int cycles;
extern int n;
extern  double dx,dy,dt,lx,ly;
extern long count1,count2;
extern int fileOutputEvery;
extern string outputDirectory;
extern double *globals;
extern int totalGlobals;
extern int totalConvergenceQuantities,convergenceCheckEvery;

typedef struct
{
	double *output;
	double *N_input;
	double *S_input;
	double *N_constants;
	double *S_constants;	
	double *C_input;
	double *C_constants;
	double *C_conserved;
	double *E_input;
	double *W_input;
	double *E_constants;
	double *W_constants;
	double *ConstantsOutput;
	double *NE_input;
	double *NW_input;
	double *SE_input;
	double *SW_input;	
	double *NE_constants;
	double *NW_constants;
	double *SE_constants;
	double *SW_constants;

} PointStruct2D;

typedef struct
{
	double *U_input;
	double *U_constants;
	double *U_conserved;
} InitPoint2D;

typedef struct
{
	unsigned char R;
	unsigned char G;
	unsigned char B;
} ColorRGB;

#endif 
