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

#ifndef H_UPPYRAMID
#define H_UPPYRAMID
#include <stdio.h>
#include <stdlib.h>
#include "Swept2DGlobals.h"
#include "ProcessGraph.h"
#include "Substeps2D.h"
#include "string.h"

extern ProcessGraph pg;

class UpPyramid
{

private:
	double *foundation;
	double *staging;
	double *northPanel;
	double *southPanel;
	double *eastPanel;
	double *westPanel;
	int    n;
	int constants;
	int    panelSize;
	int substeps;
	int dataPointSize;
	int conservedQuantities;
	int    ijToIndex(int i,int j);
	void   buildPanels(int level);

public:
	UpPyramid(int n,double *foundation,double *staging,int substeps,int dataPointSize,int constants,int conservedQuantities);
	double *getNorthPanel();
	double *getSouthPanel();
	double *getEastPanel();
	double *getWestPanel();
	void   setInitCondition(void initFnc(int,int,InitPoint2D*));
	void   updateSystem(void initFnc(int,int,InitPoint2D*));
	void   printFoundation();
	void   build(int executeFnc);
	~UpPyramid();
};

#endif