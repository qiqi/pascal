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

#ifndef H_DOWNPYRAMID
#define H_DOWNPYRAMID
#include <stdio.h>
#include <stdlib.h>
#include "Swept2DGlobals.h"
#include "Substeps2D.h"
#include "string.h"

using namespace std;
class DownPyramid
{

private:
	double *foundation;
	double *staging;
	double *northPanel;
	double *southPanel;
	double *eastPanel;
	double *westPanel;
	double *tempFoundation;
	int n;
	int panelSize;
	int substeps;
	int dataPointSize;
	int constants;
	int conservedQuantities;
	int    ijToIndex(int i,int j);	
	void   populateFoundation(int level,double *sourceData);

public:
	DownPyramid(int n,double *foundation,double *staging,int substeps,int dataPointSize,int constants,int conservedQuantities);
	void setPanels(double *northPanel,double *southPanel,double *eastPanel,double *westPanel);	
	void printFoundation(double *foundationPtr);	
	void printFoundation(double *foundationPtr,int dataPoint = 0);	
	void getFoundation(double *foundationPtr,double *result,int dataPoint = 0);
	void build(int executeFnc);
	~DownPyramid();
};

#endif