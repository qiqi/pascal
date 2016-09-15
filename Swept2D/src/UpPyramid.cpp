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

#include "UpPyramid.h"

extern int substeps;

UpPyramid::UpPyramid(int n,double *foundation,double *staging,int substeps,int dataPointSize, int constants,int conservedQuantities)
{
	this->n = (n+2);
	this->constants = constants;
	this->substeps = substeps;
	this->dataPointSize = dataPointSize;
	this->conservedQuantities = conservedQuantities;
	panelSize = 2;
	for(int i=n;i>2;i=i-2)
		panelSize += i;
	panelSize *= 2;	
	//--panelSize = panelSize * substeps * dataPointSize;
	panelSize = (panelSize * 1 * dataPointSize) + (panelSize * constants);
	this->foundation = foundation;
	this->staging    = staging;
	this->northPanel = new double[panelSize];
	this->southPanel = new double[panelSize];
	this->eastPanel  = new double[panelSize];
	this->westPanel  = new double[panelSize];	
}

int UpPyramid::ijToIndex(int i,int j)
{
	return Swept2DUtils::ijToIndex(n,i,j,this->dataPointSize,this->constants);
}

void UpPyramid::printFoundation()
{
	
	for(int i=1;i<n-1;i++)
	{
		for(int j=1;j<n-1;j++)
		{
			printf("%.0f ",this->foundation[ijToIndex(i,j) + constants]);
		}
		printf("\n");
	}
	printf("\n\n");
}
void UpPyramid::setInitCondition(void initFnc(int,int,InitPoint2D*))
{	
	for(int i=1;i<n-1;i++)
	{
		for(int j=1;j<n-1;j++)
		{
			InitPoint2D point;
			point.U_input = &foundation[this->ijToIndex(i,j) + constants];
			point.U_constants  = &foundation[this->ijToIndex(i,j)];
			point.U_conserved  = &foundation[(this->ijToIndex(i,j)) + (this->constants-this->conservedQuantities)];
			initFnc((pg.iIndex*(n-2))+i-1,(pg.jIndex*(n-2))+j-1,&point);			
		}
	}
}

void UpPyramid::updateSystem(void updateFnc(int,int,InitPoint2D*))
{	
	for(int i=1;i<n-1;i++)
	{
		for(int j=1;j<n-1;j++)
		{
			InitPoint2D point;
			point.U_input = &foundation[this->ijToIndex(i,j) + constants];
			point.U_constants  = &foundation[this->ijToIndex(i,j)];
			point.U_conserved  = &foundation[(this->ijToIndex(i,j)) + (this->constants-this->conservedQuantities)];
			updateFnc((pg.iIndex*(n-2))+i-1,(pg.jIndex*(n-2))+j-1,&point);			
		}
	}
}

void UpPyramid::buildPanels(int level)
{
	int indexStart = Swept2DUtils::getShrinkingIndex(this->n,level,this->dataPointSize,this->constants);
	
	double *sourceData;
	if(level%2 == 0)
	{	
		sourceData = foundation;
	}
	else
	{
		sourceData = staging;	
	}

	//North Panel
	int index = indexStart;
	for(int i=level+1;i<level+2+1;i++)
	{
		for(int j=0+level+1;j<(n-2)-level+1;j++)
		{
			int srcIndex = this->ijToIndex(i,j);
			memcpy(&this->northPanel[index],&sourceData[this->ijToIndex(i,j)],((1 * dataPointSize) + constants) * sizeof(double));			
			index += (1 * dataPointSize) + constants;			
		}
	}
	
	//South Panel
	index = indexStart;
	for(int i=(n-2)-level-2+1;i<(n-2)-level+1;i++)
	{
		for(int j=0+level+1;j<(n-2)-level+1;j++)
		{
			memcpy(&this->southPanel[index],&sourceData[this->ijToIndex(i,j)],((1 * dataPointSize) + constants) * sizeof(double));
			index += (1 * dataPointSize) + constants;	
		}
	}
		
	//East Panel
	index = indexStart;
	for(int j=(n-2)-level-2+1;j<(n-2)-level+1;j++)
	{
		for(int i=0+level+1;i<(n-2)-level+1;i++)
		{
			memcpy(&this->eastPanel[index],&sourceData[this->ijToIndex(i,j)],((1 * dataPointSize) + constants) * sizeof(double));
			index += (1 * dataPointSize) + constants;			
		}
	}
		
	//West Panel
	index = indexStart;	
	for(int j=level+1;j<level+2+1;j++)
	{
		for(int i=0+level+1;i<(n-2)-level+1;i++)		
		{
			memcpy(&this->westPanel[index],&sourceData[this->ijToIndex(i,j)],((1 * dataPointSize) + constants) * sizeof(double));
			index += (1 * dataPointSize) + constants;			
		}
	}
	
}

void UpPyramid::build(int executeFnc)
{
	double *sourceData;
	double *destData;
	int levels = (n-2)/2;
	this->buildPanels(0);
	
	for(int level=1;level<levels;level++)
	{
		if(level%2 != 0)
		{
			destData   = staging;
			sourceData = foundation;
		}
		else
		{
			destData   = foundation;
			sourceData = staging;
		}
		for(int i=0+level+1;i<(n-2)-level+1;i++)
		{
			for(int j=0+level+1;j<(n-2)-level+1;j++)
			{
				PointStruct2D point;
				point.ConstantsOutput = &destData[this->ijToIndex(i,j)];
				memcpy(&destData[this->ijToIndex(i,j)],&sourceData[this->ijToIndex(i,j)],constants * sizeof(double));
				point.output = &destData[this->ijToIndex(i,j) + constants];
				point.C_input = &sourceData[this->ijToIndex(i,j) + constants];
				point.C_constants  = &sourceData[this->ijToIndex(i,j)];
				point.C_conserved  = &destData[(this->ijToIndex(i,j)) + (this->constants-this->conservedQuantities)];
				point.W_input = &sourceData[this->ijToIndex(i-1,j) + constants];
				point.W_constants  = &sourceData[this->ijToIndex(i-1,j)];
				point.E_input = &sourceData[this->ijToIndex(i+1,j) + constants];
				point.E_constants  = &sourceData[this->ijToIndex(i+1,j)];
				point.S_input = &sourceData[this->ijToIndex(i,j+1) + constants];
				point.S_constants  = &sourceData[this->ijToIndex(i,j+1)];
				point.N_input = &sourceData[this->ijToIndex(i,j-1) + constants];
				point.N_constants  = &sourceData[this->ijToIndex(i,j-1)];				

				point.NE_input = &sourceData[this->ijToIndex(i+1,j-1) + constants];
				point.NE_constants  = &sourceData[this->ijToIndex(i+1,j-1)];		
				point.NW_input = &sourceData[this->ijToIndex(i-1,j-1) + constants];
				point.NW_constants  = &sourceData[this->ijToIndex(i-1,j-1)];		
				point.SE_input = &sourceData[this->ijToIndex(i+1,j+1) + constants];
				point.SE_constants  = &sourceData[this->ijToIndex(i+1,j+1)];		
				point.SW_input = &sourceData[this->ijToIndex(i-1,j+1) + constants];
				point.SW_constants  = &sourceData[this->ijToIndex(i-1,j+1)];		
				Substeps2D::executeStepFnc(executeFnc,&point);				
			}
		}
		this->buildPanels(level);
		executeFnc++;
		if(executeFnc==substeps)executeFnc = 0;
	}
}

double *UpPyramid::getEastPanel()
{
	return this->eastPanel;
}

double *UpPyramid::getWestPanel()
{
	return this->westPanel;
}

double *UpPyramid::getNorthPanel()
{
	return this->northPanel;
}

double *UpPyramid::getSouthPanel()
{
	return this->southPanel;
}

UpPyramid::~UpPyramid(void)
{
	delete[] northPanel;
	delete[] southPanel;
	delete[] eastPanel;
	delete[] westPanel;
}
