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

#ifndef H_HBRIDGE
#define H_HBRIDGE
#include <stdio.h>
#include <stdlib.h>
#include "Swept2DGlobals.h"
#include "Substeps2D.h"
#include "string.h"

class HorizontalBridge
{

private:
	double *foundation;
	double *staging;
	double *northPanel;
	double *southPanel;
	double *eastPanel;
	double *westPanel;
	int    n,panelSize,constants;
	int conservedQuantities;
	int substeps;
	int dataPointSize;
	int    ijToIndex(int i,int j);
	void   buildPanels(int level,double *sourceData);
	void   populateFoundation(int level,double *destData);	
	void   fillValley(int level,int executeFnc,double *sourceData,double *destData);
	
public:
	HorizontalBridge(int n,double *foundation,double *staging,int substeps,int dataPointSize,int constants,int conservedQuantities);
	void setEastWestPanels(double *eastPanel,double *westPanel);
	void build(int executeFnc);
	double *getNorthPanel();
	double *getSouthPanel();
	void printFoundation(double *foundationPtr);
	~HorizontalBridge();

};

#endif
