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

#include "DownPyramid.h"

extern int substeps;


DownPyramid::DownPyramid(int n,double *foundation,double *staging,int substeps,int dataPointSize,int constants,int conservedQuantities)
{
	this->n = (n+2);
	this->substeps = substeps;
	this->constants = constants;
	this->dataPointSize = dataPointSize;
	this->conservedQuantities = conservedQuantities;
	panelSize = 2;
	for(int i=n;i>2;i=i-2)panelSize += i;panelSize *= 2;
	int constantsToAdd = panelSize * constants;
	//panelSize = panelSize * substeps * dataPointSize;
	panelSize = panelSize * 1 * dataPointSize + constantsToAdd;
	this->foundation = foundation;
	this->staging    = staging;
	this->tempFoundation = new double[(n+2) * (n+2) * 1 * dataPointSize + ((n+2) * (n+2) * constants)];
	for(int i=0;i<(n+2) * (n+2) * 1 * dataPointSize + ((n+2) * (n+2) * constants);i++)
	{
		this->foundation[i] = 0;
		this->staging[i] = 0;
		this->tempFoundation[i] = 0;
	}	
}

void DownPyramid::setPanels(double *northPanel,double *southPanel,double *eastPanel,double *westPanel)
{
	this->northPanel = northPanel;
	this->southPanel = southPanel;
	this->eastPanel  = eastPanel;
	this->westPanel  = westPanel;
}
int DownPyramid::ijToIndex(int i,int j)
{
	return Swept2DUtils::ijToIndex(n,i,j,this->dataPointSize,this->constants);
}

void DownPyramid::printFoundation(double *foundationPtr,int dataPoint)
{
	for(int j=1;j<n-1;j++)
	{
		for(int i=1;i<n-1;i++)
		{
			printf("%.7f ",foundationPtr[ijToIndex(i,j) + constants + dataPoint]);
		}
		printf("\n");
	}
	printf("\n\n");
}

void DownPyramid::getFoundation(double *foundationPtr,double *result,int dataPoint)
{
	int index =0;
	for(int i=1;i<n-1;i++)
	{
		for(int j=1;j<n-1;j++)
		{
			result[index] = foundationPtr[ijToIndex(i,j) + constants + dataPoint];
			index++;
		}		
	}	
}

void DownPyramid::populateFoundation(int level,double *sourceData)
{
	int indexStart = Swept2DUtils::getGrowingIndex(this->n,level,this->dataPointSize,this->constants);
		
	//North Panel
	int index = indexStart;
	for(int j=(n-2)/2-level-1;j<(n-2)/2-level-1+2;j++)
	{
		for(int i=(n-2)/2-level-1;i<(n-2)/2-level-1+((level+1)*2);i++)
		{
			memcpy(&sourceData[this->ijToIndex(i,j)],&this->westPanel[index],((1 * dataPointSize) + constants) * sizeof(double));
			index += (1 * dataPointSize) + constants;
		}
	}
	
	//South Panel
	index = indexStart;
	for(int i=(n-2)/2-level-1;i<(n-2)/2-level-1+2;i++)		
	{		
		for(int j=(n-2)/2-level-1+2;j<(n-2)/2-level-1+2+((level+1)*2);j++)
		{
			memcpy(&sourceData[this->ijToIndex(i,j)],&this->northPanel[index],((1 * dataPointSize) + constants) * sizeof(double));			
			index += (1 * dataPointSize) + constants;
		}
	}
		
	//East Panel
	index = indexStart;
	for(int i=(n-2)/2+level+1;i<(n-2)/2+level+1+2;i++)	
	{
		for(int j=(n-2)/2-level-1;j<(n-2)/2-level-1+((level+1)*2);j++)
		{
			memcpy(&sourceData[this->ijToIndex(i,j)],&this->southPanel[index],((1 * dataPointSize) + constants) * sizeof(double));
			index += (1 * dataPointSize) + constants;
		}
	}
		
	//West Panel
	index = indexStart;	
	for(int j=(n-2)/2+level+1;j<(n-2)/2+level+1+2;j++)
	{
		for(int i=(n-2)/2-level+1;i<(n-2)/2-level+1+((level+1)*2);i++)
		{
			memcpy(&sourceData[this->ijToIndex(i,j)],&this->eastPanel[index],((1 * dataPointSize) + constants) * sizeof(double));
			index += (1 * dataPointSize) + constants;
		}
	}	
}

void DownPyramid::build(int executeFnc)
{
	double *sourceData;
	double *destData;
	int levels = (n-2)/2;
	int execute = executeFnc;

	for(int level=0;level<levels;level++)
	{
		if(level%2 != 0)
		{
			/*
			destData   = staging;
			sourceData = foundation;
			*/
			destData   = foundation;
			sourceData = staging;
		}
		else
		{
			/*
			destData   = foundation;
			sourceData = staging;
			*/
			destData   = staging;
			sourceData = foundation;
		}
		this->populateFoundation(level,sourceData);		
		
		for(int i=(n-2)/2-level;i<(n-2)/2-level+(level+1)*2;i++)
		{
			for(int j=(n-2)/2-level;j<(n-2)/2-level+(level+1)*2;j++)
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

				Substeps2D::executeStepFnc(execute,&point);
			}
		}
				
		execute++;
		if(execute==substeps)execute = 0;
	}
	
	if(this->foundation != destData)
	{
		memcpy(this->tempFoundation,this->foundation,sizeof(double) * ((n*n) * 1 * dataPointSize + ((n*n) * constants)));	
		memcpy(this->foundation,destData,sizeof(double) * ((n*n) * 1 * dataPointSize + ((n*n) * constants)));	
		memcpy(this->staging,this->tempFoundation,sizeof(double) * ((n*n) * 1 * dataPointSize + ((n*n) * constants)));	
	}
}

DownPyramid::~DownPyramid(void)
{	
}
