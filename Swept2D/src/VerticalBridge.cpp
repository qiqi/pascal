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

#include "VerticalBridge.h"

VerticalBridge::VerticalBridge(int n,double *foundation,double *staging,int substeps,int dataPointSize,int constants,int conservedQuantities)
{
	this->n = (n+2);	
	this->substeps = substeps;
	this->dataPointSize = dataPointSize;
	this->constants = constants;
	this->conservedQuantities = conservedQuantities;
	panelSize = 2;
	for(int i=n;i>2;i=i-2)panelSize += i;panelSize *= 2;
	int constantsToAdd = panelSize * constants;
	panelSize = panelSize * 1 * dataPointSize;
	this->foundation = foundation;
	this->staging    = staging;
	this->eastPanel  = new double[panelSize + constantsToAdd];
	this->westPanel  = new double[panelSize + constantsToAdd];
}

void VerticalBridge::setNorthSouthPanels(double *northPanel,double *southPanel)
{
	this->northPanel = northPanel;
	this->southPanel = southPanel;
}

int VerticalBridge::ijToIndex(int i,int j)
{
	return Swept2DUtils::ijToIndex(n,i,j,this->dataPointSize,this->constants);
}

void VerticalBridge::populateFoundation(int level,double *destData)
{
	int indexStart = Swept2DUtils::getShrinkingIndex(this->n,level,this->dataPointSize,this->constants);

	//Read and Place North Panel Values
	int index = indexStart;
	for(int j=(n-2)/2-(2+level)+1;j<(n-2)/2-level+1;j++)
	{
		for(int i=level+1;i<(n-2)-level+1;i++)
		{
			memcpy(&destData[this->ijToIndex(j,i)],&this->northPanel[index],((1 * dataPointSize) + constants) * sizeof(double));			
			index += (1 * dataPointSize) + constants;
		}
	}
	
	//Read and Place South Panel Values
	index = indexStart;
	for(int j=(n-2)/2+(level)+1;j<(n-2)/2+2+level+1;j++)
	{
		for(int i=level+1;i<(n-2)-level+1;i++)
		{
			memcpy(&destData[this->ijToIndex(j,i)],&this->southPanel[index],((1 * dataPointSize) + constants) * sizeof(double));			
			index += (1 * dataPointSize) + constants;
		}
	}
	
}

void VerticalBridge::buildPanels(int level,double *sourceData)
{
	int indexStart = Swept2DUtils::getGrowingIndex(this->n,level,this->dataPointSize,this->constants);

	//West Panel
	int index = indexStart;
	for(int i=level+1;i<level+2+1;i++)
	{
		for(int j=(n-2)/2-(1+level)+1+1;j<((n-2)/2-(1+level))+((level+1)*2)+1+1;j++)
		{
			memcpy(&this->westPanel[index],&sourceData[this->ijToIndex(j,i)],((1 * dataPointSize) + constants) * sizeof(double));			
			index += (1 * dataPointSize) + constants;
		}
	}
		
	//East Panel
	index = indexStart;
	for(int i=(n-2)-level-2+1;i<(n-2)-level+1;i++)
	{
		for(int j=(n-2)/2-(1+level)-1+1;j<((n-2)/2-(1+level))+((level+1)*2)-1+1;j++)
		{
			memcpy(&this->eastPanel[index],&sourceData[this->ijToIndex(j,i)],((1 * dataPointSize) + constants) * sizeof(double));			
			index += (1 * dataPointSize) + constants;
		}
	}	
}

void VerticalBridge::fillValley(int level,int executeFnc,double *sourceData,double *destData)
{
	for(int j=(n-2)/2-(level)+1;j<((n-2)/2-(level))+((level)*2)+1;j++)
	{
		for(int i=level+1;i<(n-2)-level+1;i++)
		{
			PointStruct2D point;
			point.ConstantsOutput = &destData[this->ijToIndex(j,i)];
			memcpy(&destData[this->ijToIndex(j,i)],&sourceData[this->ijToIndex(j,i)],constants * sizeof(double));
			point.output = &destData[this->ijToIndex(j,i) + constants];
			point.C_input = &sourceData[this->ijToIndex(j,i) + constants];
			point.C_constants  = &sourceData[this->ijToIndex(j,i)];
			point.C_conserved  = &destData[(this->ijToIndex(i,j)) + (this->constants-this->conservedQuantities)];
			point.W_input = &sourceData[this->ijToIndex(j-1,i) + constants];
			point.W_constants  = &sourceData[this->ijToIndex(j-1,i)];
			point.E_input = &sourceData[this->ijToIndex(j+1,i) + constants];
			point.E_constants  = &sourceData[this->ijToIndex(j+1,i)];
			point.S_input = &sourceData[this->ijToIndex(j,i+1) + constants];
			point.S_constants  = &sourceData[this->ijToIndex(j,i+1)];
			point.N_input = &sourceData[this->ijToIndex(j,i-1) + constants];
			point.N_constants  = &sourceData[this->ijToIndex(j,i-1)];

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
}
void VerticalBridge::build(int executeFnc)
{
	double *sourceData = foundation;
	double *destData = staging;
	int level = 0;
	populateFoundation(level,sourceData);
	buildPanels(level,sourceData);
	for(level=1;level<(n-2)/2;level++)
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
		fillValley(level,executeFnc,sourceData,destData);
		populateFoundation(level,destData);
		buildPanels(level,destData);
		executeFnc++;
		if(executeFnc==substeps)executeFnc = 0;
	}	
}

double *VerticalBridge::getEastPanel()
{
	return this->eastPanel;
}

double *VerticalBridge::getWestPanel()
{
	return this->westPanel;
}

VerticalBridge::~VerticalBridge()
{
	delete[] this->eastPanel;
	delete[] this->westPanel;
}
