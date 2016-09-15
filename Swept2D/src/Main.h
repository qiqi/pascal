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

#include <iostream>
#include "SweptDiscretization2D.h"
#include "MpiGlobals2D.h"
#include "stdlib.h"
#include <ctime>
#include <cmath>
#include <string>
#include "base64.h"

using namespace std;

long stepCount[100];
long localCount[100];
int constants;
int remoteConstants;
int substeps,n;
int dataPointSize;
int cycles;
int fileOutputEvery;
string outputDirectory;
double dx,dy,dt,lx,ly;
double *globals;
int totalGlobals;
int totalConvergenceQuantities,convergenceCheckEvery;

