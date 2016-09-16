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

#include "SweptDiscretization2D.h"

#define TJE_IMPLEMENTATION
#include "tiny_jpeg.h"

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

static ColorRGB HSL2RGB(double h, double sl, double l)
{
    double v;
    double r,g,b;
 
    r = l;
    g = l;
    b = l;
    v = (l <= 0.5) ? (l * (1.0 + sl)) : (l + sl - l * sl);
    if (v > 0)
    {
            double m;
            double sv;
            int sextant;
            double fract, vsf, mid1, mid2;
 
            m = l + l - v;
            sv = (v - m ) / v;
            h *= 6.0;
            sextant = (int)h;
            fract = h - sextant;
            vsf = v * sv * fract;
            mid1 = m + vsf;
            mid2 = v - vsf;
            switch (sextant)
            {
                case 0:
                        r = v;
                        g = mid1;
                        b = m;
                        break;
                case 1:
                        r = mid2;
                        g = v;
                        b = m;
                        break;
                case 2:
                        r = m;
                        g = v;
                        b = mid1;
                        break;
                case 3:
                        r = m;
                        g = mid2;
                        b = v;
                        break;
                case 4:
                        r = mid1;
                        g = m;
                        b = v;
                        break;
                case 5:
                        r = v;
                        g = m;
                        b = mid2;
                        break;
            }
    }
    ColorRGB rgb;
    rgb.R = (unsigned char) (r * 255.0f);
    rgb.G = (unsigned char) (g * 255.0f);
    rgb.B = (unsigned char) (b * 255.0f);
    return rgb;
}
SweptDiscretization2D::SweptDiscretization2D(int n,int substeps,int dataPointSize,int totalConstants,int totalConservedQuantities,int remoteConstantsCount)
{
	if(totalConstants<remoteConstantsCount)
	{
		printf("Remote Constants Cannot be more than the total constants!!\n");
		exit(1);
	}
	this->n = n;
	this->substeps = substeps;
	this->dataPointSize = dataPointSize;
	//this->constants = totalConstants;
	this->constants = totalConstants + totalConvergenceQuantities;
	this->remoteConstantsCount = remoteConstantsCount;
	this->totalConservedQuantities = totalConservedQuantities;
	this->checkForRemoteCycles = -1;
	this->outputToFile = -1;
	this->convergenceCheckFreq = -1;
	this->firstConservedCheck = true;
	this->outputLength = 1;
	this->converged = false;
	this->oldNorm = 0;
	panelSize = 2;
	for(int i=n;i>2;i=i-2)panelSize += i;panelSize *= 2;
	int constantsToAdd = panelSize * this->constants;
	//--panelSize = panelSize * substeps * dataPointSize;
	panelSize = panelSize * 1 * dataPointSize;
	communicationSize = panelSize + constantsToAdd;
	//--foundationSize = ((n+2) * (n+2) * substeps * dataPointSize + ((n+2) * (n+2) * this->constants));
	foundationSize = ((n+2) * (n+2) * 1 * dataPointSize + ((n+2) * (n+2) * this->constants));
	resultArray = NULL;
	localResultArray = NULL;
	socketResultArray = NULL;
	MPI_Alloc_mem(foundationSize * sizeof(double), MPI_INFO_NULL, &foundation);
	MPI_Win_create(foundation,foundationSize * sizeof(double),1, MPI_INFO_NULL,MPI_COMM_WORLD, &foundationWindow);
	if(remoteConstantsCount > 0)
	{
		MPI_Alloc_mem(n * n * remoteConstantsCount * sizeof(double), MPI_INFO_NULL, &remoteConstants);
		MPI_Win_create(remoteConstants,n * n * remoteConstantsCount * sizeof(double),1, MPI_INFO_NULL,MPI_COMM_WORLD, &constantsWindow);
		constantsArrayBytes = (unsigned char*) malloc(n * n * remoteConstantsCount * sizeof(double) * pg.mpiSize);		
	}

	staging    = new double[foundationSize];
	northPanel = new double[panelSize + constantsToAdd];
	southPanel = new double[panelSize + constantsToAdd];
	eastPanel  = new double[panelSize + constantsToAdd];
	westPanel  = new double[panelSize + constantsToAdd];

	//Define Swept2D components
	up = new UpPyramid(n,foundation,staging,substeps,dataPointSize,this->constants,totalConservedQuantities);
	dp = new DownPyramid(n,foundation,staging,substeps,dataPointSize,this->constants,totalConservedQuantities);
	hb = new HorizontalBridge(n,foundation,staging,substeps,dataPointSize,this->constants,totalConservedQuantities);
	vb = new VerticalBridge(n,foundation,staging,substeps,dataPointSize,this->constants,totalConservedQuantities);
	dataPointers = NULL;
	dataBuffers  = NULL;
	dataRanks    = NULL;
	if(pg.rank == 0)
	{
		dataPointers = new vector<unsigned char*>();
		dataBuffers  = new vector<unsigned char*>();
		dataRanks    = new vector<int>();
		for(int i=0;i<ioRanks->size();i++)
		{
			int hostRank = (*ioRanks)[i];
			int hostListLength = ioInfos[hostRank].myListLength[0];
			int totalData = hostListLength * foundationSize * sizeof(double);
			unsigned char* dataBuffer = (unsigned char*) malloc(totalData);
			dataBuffers->push_back(dataBuffer);		
			for(int j=0;j<hostListLength;j++)
			{
				dataRanks->push_back(ioInfos[hostRank].myList[j]);
				unsigned char* location = dataBuffer + (j * foundationSize * sizeof(double));
				dataPointers->push_back(location);
			}
		}		
	}
}

int SweptDiscretization2D::ijToIndex(int i,int j)
{
	return Swept2DUtils::ijToIndex(n+2,i,j,this->dataPointSize,this->constants);
}

int SweptDiscretization2D::ijToConstantIndex(int i,int j)
{
	return this->remoteConstantsCount * (i + j * n);	
}

void SweptDiscretization2D::setConvergenceCheck(int cycles)
{
	this->convergenceCheckFreq = cycles;
}

void SweptDiscretization2D::setOutputLength(int outputLength)
{
	this->outputLength = outputLength;
}

double SweptDiscretization2D::calculateFoundationTrnsposeFoundation(double *C,int bases)
{
	double *CC    = new double[bases * bases + 1];	
	double *CCAll = new double[bases * bases + 1];	
	double beta = 0;
	for(int baseTranspose=0;baseTranspose<bases;baseTranspose++)
	{
		for(int base=0;base<bases;base++)
		{
			double result = 0;
			for(int j=1;j<n+1;j++)
			{
				for(int i=1;i<n+1;i++)
				{
					int index = this->ijToIndex(i,j) + this->constants;					
					result += foundation[index + baseTranspose] * foundation[index + base];					
				}
			}
			//printf("CC Index: (%d,%d) = %f\n",baseTranspose+1,base+1,result);
			CC[baseTranspose * bases + base] = result;
		}
	}
	//Generate Beta
	for(int j=1;j<n+1;j++)
	{
		for(int i=1;i<n+1;i++)
		{
			int index = this->ijToIndex(i,j);
			double val = foundation[index + 5];
			beta +=  val * val;
		}
	}
	CC[bases*bases] = beta;
	MPI_Allreduce(CC,CCAll,bases*bases+1,MPI_DOUBLE,MPI_SUM,MPI_COMM_WORLD);
	memcpy(C,CCAll,bases*bases*sizeof(double));
	beta = sqrt(CCAll[bases*bases]);
	delete[] CC;
	return beta;
}

void SweptDiscretization2D::calculateFoundationRinverse(double *Q,double *Rinv,int bases)
{
	int count = 0;
	for(int j=1;j<n+1;j++)
	{
		for(int i=1;i<n+1;i++)
		{
			int index = this->ijToIndex(i,j) + this->constants;
			int qIndex = (j-1) * bases + (i-1) * bases;
			for(int r=0;r<bases;r++)
			{
				double result = 0;
				for(int c=0;c<bases;c++)
				{
					int rIndex = c * bases + r;
					//printf("R Index: %d\n",rIndex);
					result += foundation[index + c] * Rinv[rIndex];
				}
				//printf("Index: Q[%d](%d,%d) = %f\n",count,(j-1),r,result);
				Q[count] = result;
				count++;
			}			
		}
	}	
}

void SweptDiscretization2D::reportConvergence()
{
	double newNormLocal[2];
	double newNormAll[2];
	newNormLocal[0] = 0;
	newNormLocal[1] = 0;
	for(int i=1;i<n+1;i++)
	{
		for(int j=1;j<n+1;j++)
		{			
			int cellIndex = ijToIndex(i,j);			
			double valueN = this->foundation[cellIndex + this->constants];
			double valueP = this->staging[cellIndex + this->constants];
			newNormLocal[0] += (valueN-valueP)*(valueN-valueP);
			newNormLocal[1] += valueP*valueP;

		}				
	}
	MPI_Allreduce(&newNormLocal,&newNormAll,2,MPI_DOUBLE,MPI_SUM,MPI_COMM_WORLD);	
	newNormAll[0] = sqrt(newNormAll[0]);
	newNormAll[1] = sqrt(newNormAll[1]);
	this->converged = ((newNormAll[0]/newNormAll[1]) < 1e-10) ;
	converged = false;
	
}
void SweptDiscretization2D::updateRemoteConstants(unsigned char *buffer)
{
	void *sendingBuffer = NULL;
	FILE *inFile = NULL;

	if(pg.rank == 0)
	{
		int bufferSize = this->remoteConstantsCount * n * n * pg.mpiSize * sizeof(double);
		MPI_Alloc_mem(bufferSize, MPI_INFO_NULL, &sendingBuffer);
		
		for(int r=0;r<pg.mpiSize;r++)
		{
			double *processing = (double*)sendingBuffer + (this->remoteConstantsCount * n * n * r);
			int jIndex = (r % (pg.xNodes*pg.yNodes)) / pg.xNodes;
			int iIndex = r % pg.xNodes;
			for(int j=0;j<n;j++)
			{
				for(int i=0;i<n;i++)
				{
					int iGlobal = n*iIndex + (i);
					int jGlobal = n*jIndex + (j);
					int index   = this->ijToConstantIndex(i,j);
					int globalIndex = this->remoteConstantsCount * (iGlobal + jGlobal * n * pg.xNodes);
					for(int k=0;k<this->remoteConstantsCount;k++)
					{
						processing[index + k] = ((double*)buffer)[k + globalIndex];
					}					
				}
			}		
		}
	}
	
	MPI_Win_fence(MPI_MODE_NOPRECEDE, this->constantsWindow);
	if(pg.rank == 0)
	{
		for(int r=0;r<pg.mpiSize;r++)
		{
			MPI_Put((unsigned char*)sendingBuffer + (r * remoteConstantsCount * n * n * sizeof(double)), remoteConstantsCount * n * n * sizeof(double), MPI_BYTE, r, 0, remoteConstantsCount * n * n * sizeof(double), MPI_BYTE, constantsWindow);			
		}
	}
	MPI_Win_fence((MPI_MODE_NOSTORE | MPI_MODE_NOSUCCEED), this->constantsWindow);

	if(pg.rank == 0)
	{
		MPI_Free_mem(sendingBuffer);					
	}
	for(int i=1;i<n+1;i++)
	{
		for(int j=1;j<n+1;j++)
		{
			for(int k=0;k<this->remoteConstantsCount;k++)
			{
				int windowIndex    = this->ijToConstantIndex(i-1,j-1);
				int foundationIndex = this->ijToIndex(i,j);
				this->foundation[foundationIndex + k] = this->remoteConstants[windowIndex + k];
			}
		}
	}
}

void SweptDiscretization2D::updateDataPoint(double *buffer,int dataPointNbr)
{
	int count = 0;
	for(int j=1;j<n+1;j++)
	{
		for(int i=1;i<n+1;i++)
		{
			int index   = this->ijToIndex(i,j) + constants + dataPointNbr;
			this->foundation[index] = buffer[count];
			count++;
		}
	}		
}

void SweptDiscretization2D::calculateResidul(double *r)
{
	double resNorm = 0;
	double resNormAll = 0;
	int count = 0;
	for(int j=1;j<n+1;j++)
	{
		for(int i=1;i<n+1;i++)
		{
			int jP = j;
			int jM = j;
			int iP = i;
			int iM = i;
			if(jP == n)
				jP = 1;
			else
				jP += 1;
			if(jM == 1)
				jM = n;
			else
				jM -=1;

			if(iP == n)
				iP = 1;
			else
				iP += 1;
			if(iM == 1)
				iM = n;
			else iM -=1;
						
			PointStruct2D point;
			point.C_constants = &foundation[this->ijToIndex(i,j)];
			point.C_input     = &foundation[this->ijToIndex(i,j) + constants];
			point.W_input     = &foundation[this->ijToIndex(iM,j) + constants];
			point.E_input     = &foundation[this->ijToIndex(iP,j) + constants];
			point.S_input     = &foundation[this->ijToIndex(i,jP) + constants];
			point.N_input     = &foundation[this->ijToIndex(i,jM) + constants];

			double c = point.C_input[0];
			double e = point.E_input[0];
			double w = point.W_input[0];
			double n = point.N_input[0];
			double s = point.S_input[0];

			double cc = point.C_constants[0];
			double ec = point.C_constants[1];
			double wc = point.C_constants[2];
			double nc = point.C_constants[3];
			double sc = point.C_constants[4];
			double b  = point.C_constants[5];
			double res = b - (cc * c + ec * e + wc * w + nc * n + sc * s);
			r[count] = res;
			resNorm += res*res;
			count++;
		}
	}
	MPI_Allreduce(&resNorm,&resNormAll,1,MPI_DOUBLE,MPI_SUM,MPI_COMM_WORLD);
	printf("Residul Norm: %f\n",sqrt(resNormAll));
}

void SweptDiscretization2D::updateRemoteConstants2(unsigned char *buffer)
{
	MPI_Request recvReq1,recvReq2;
	MPI_Irecv(this->remoteConstants,remoteConstantsCount * n * n * sizeof(double), MPI_BYTE,ioInfo.myWriter[0],2222,MPI_COMM_WORLD,&recvReq1);
	if(ioInfo.isWriter[0] == 1)
	{
		if(localResultArray == NULL)
			localResultArray = (double*) malloc(ioInfo.myListLength[0] * sizeof(double) * foundationSize);
		MPI_Irecv(this->localResultArray,remoteConstantsCount * n * n * sizeof(double) * ioInfo.myListLength[0], MPI_BYTE,0,222,MPI_COMM_WORLD,&recvReq2);
	}
	if(pg.rank == 0)
	{
		MPI_Request *sendReqs = (MPI_Request*) malloc(ioRanks->size() * sizeof(MPI_Request));
		for(int h=0;h<ioRanks->size();h++)
		{
			int hostRank = (*ioRanks)[h];
			int hostList = ioInfos[hostRank].myListLength[0];
			for(int p=0;p<hostList;p++)
			{
				int processingRank = ioInfos[hostRank].myList[p];
				double *processing = (double*)(*dataBuffers)[h] + (this->remoteConstantsCount * n * n * p);
				int jIndex = (processingRank % (pg.xNodes*pg.yNodes)) / pg.xNodes;
				int iIndex = processingRank % pg.xNodes;
				for(int j=0;j<n;j++)
				{
					for(int i=0;i<n;i++)
					{
						int iGlobal = n*iIndex + (i);
						int jGlobal = n*jIndex + (j);
						int index   = this->ijToConstantIndex(i,j);
						int globalIndex = this->remoteConstantsCount * (iGlobal + jGlobal * n * pg.xNodes);
						for(int k=0;k<this->remoteConstantsCount;k++)
						{
							processing[index + k] = ((double*)buffer)[k + globalIndex];
						}					
					}
				}
			}
			MPI_Isend((*dataBuffers)[h],remoteConstantsCount * n * n * sizeof(double) * hostList,MPI_BYTE,hostRank,222,MPI_COMM_WORLD,&(sendReqs[h]));
		}
		for(int h=0;h<ioRanks->size();h++)
			MPI_Wait(&(sendReqs[h]),MPI_STATUS_IGNORE);
		free(sendReqs);
	}
	if(ioInfo.isWriter[0] == 1)
	{
		MPI_Request *sendReqs = (MPI_Request*) malloc(ioInfo.myListLength[0] * sizeof(MPI_Request));
		MPI_Wait(&recvReq2,MPI_STATUS_IGNORE);
		for(int r=0;r<ioInfo.myListLength[0];r++)
		{
			int offset = remoteConstantsCount * n * n * sizeof(double) * r;
			MPI_Isend((unsigned char*)localResultArray+offset,remoteConstantsCount * n * n * sizeof(double),MPI_BYTE,ioInfo.myList[r],2222,MPI_COMM_WORLD,&(sendReqs[r]));
		}
		for(int r=0;r<ioInfo.myListLength[0];r++)
			MPI_Wait(&(sendReqs[r]),MPI_STATUS_IGNORE);
		free(sendReqs);
	}
	MPI_Wait(&recvReq1,MPI_STATUS_IGNORE);
	for(int i=1;i<n+1;i++)
	{
		for(int j=1;j<n+1;j++)
		{
			for(int k=0;k<this->remoteConstantsCount;k++)
			{
				int windowIndex    = this->ijToConstantIndex(i-1,j-1);
				int foundationIndex = this->ijToIndex(i,j);
				this->foundation[foundationIndex + k] = this->remoteConstants[windowIndex + k];
			}
		}
	}
}

void SweptDiscretization2D::allGatherOutputToJpeg(int dataPoint,string filename,string otherFile)
{
	
	void *buffer = NULL;
	
	if(pg.rank == 0)
	{
		MPI_Alloc_mem(foundationSize * pg.mpiSize * sizeof(double), MPI_INFO_NULL, &buffer);		
	}
	
	MPI_Gather(this->foundation,foundationSize * sizeof(double), MPI_BYTE,buffer,(foundationSize * sizeof(double)),MPI_BYTE,0,MPI_COMM_WORLD);
	if(pg.rank == 0)
	{
		int w = (n * pg.xNodes);
		int h = (n * pg.yNodes);
		int resultArraySize = w * h;
		if(socketResultArray == NULL)
			socketResultArray = (float*) malloc(resultArraySize * sizeof(float));
		
		for(int r=0;r<pg.mpiSize;r++)
		{
			double *processing = (double*)buffer + (foundationSize * r);			
			int jIndex = (r % (pg.xNodes*pg.yNodes)) / pg.xNodes;
			int iIndex = r % pg.xNodes;
			for(int j=1;j<n+1;j++)
			{
				for(int i=1;i<n+1;i++)
				{
					int iGlobal = n*iIndex + (i-1);
					int jGlobal = n*jIndex + (j-1);
					int index   = this->ijToIndex(i,j);
					int resultIndex = iGlobal + jGlobal * n * pg.xNodes;
					socketResultArray[resultIndex] = (float) (processing[index + constants + dataPoint] / processing[index + constants]);
				}
			}
		}

		// find min/max value in socketResultArray   (u_min, u_max)
		float umin = socketResultArray[0];
		float umax = socketResultArray[0];
		for (int i=1; i<resultArraySize; i++)
		{
			umin = (socketResultArray[i] < umin) ? socketResultArray[i] : umin;
			umax = (socketResultArray[i] > umax) ? socketResultArray[i] : umax;
		}

		unsigned char *colorArray = (unsigned char *) malloc(resultArraySize * 3);
		
		// normalize socketResultArray
		// convert to color matrix (RGB * pixels)
		if (umax-umin == 0)
			printf("All array values are the same\n");
		else
		{
			for (int i=0; i<resultArraySize; i++)
			{
				ColorRGB rgb = HSL2RGB(((socketResultArray[i] - umin) / (umax-umin)),1.0,0.5);
				colorArray[i*3 + 0] = rgb.R;
				colorArray[i*3 + 1] = rgb.G;
				colorArray[i*3 + 2] = rgb.B;
			}
		}

		// convert to JPG/PNG
		// Write to file [or Stream to client]
		//int writerOutput = stbi_write_bmp("f.bmp", w, h, 1, colorArray);
		
		//if ( !tje_encode_to_file("out.jpg", w, h, 3, colorArray) )
		if ( !tje_encode_to_file_at_quality(filename.c_str(), 2,w, h, 3, colorArray) )
			printf("Could not write JPEG\n");
                if ( !tje_encode_to_file_at_quality(otherFile.c_str(), 2,w, h, 3, colorArray) )
                        printf("Could not write JPEG\n");
		/*
		FILE *imgf = fopen(filename.c_str(),"rb");
		fseek(imgf, 0L, SEEK_END);
		int imgSize = ftell(imgf);
		rewind(imgf);
		unsigned char * imgbuf = (unsigned char *) malloc(imgSize);
		int count = fread(imgbuf, 1, imgSize, imgf);

		fclose(imgf);
                */
		MPI_Free_mem(buffer);
	}
	MPI_Barrier(MPI_COMM_WORLD);
}

void SweptDiscretization2D::setInitCondition(void initFnc(int,int,InitPoint2D*))
{
	up->setInitCondition(initFnc);	
	//up->printFoundation();
}

void SweptDiscretization2D::updateSystem(void updateFnc(int,int,InitPoint2D*))
{
	up->updateSystem(updateFnc);	
	//up->printFoundation();
}
void SweptDiscretization2D::setOutputDirectory(string outputDirectory)
{
	this->outputDirectory.clear();
	this->outputDirectory += outputDirectory;		
}

/*
void SweptDiscretization2D::printFoundation(int dataPoint)
{
	dp->printFoundation(foundation,dataPoint);		
}
*/

void SweptDiscretization2D::printConstantFromWindow(int constNum)
{
	for(int i=0;i<n;i++)
	{
		for(int j=0;j<n;j++)
		{
			int index  = this->ijToConstantIndex(i,j);
			double value = this->remoteConstants[index + constNum];
			printf("%.1f ",value);
		}
		printf("\n");
	}
}

void SweptDiscretization2D::printConstantFromFoundation(int constNum)
{
	for(int j=1;j<n+1;j++)
	{
		for(int i=1;i<n+1;i++)
		{
			int index  = this->ijToIndex(i,j);
			double value = this->foundation[index + constNum];
			printf("%f ",value);
		}
		printf("\n");
	}
}

void SweptDiscretization2D::getFoundation(double *result,int dataPoint)
{
	dp->getFoundation(foundation,result,dataPoint);
}

void SweptDiscretization2D::setCheckForRemoteCommands(int cycles)
{
	this->checkForRemoteCycles = cycles;
}

void SweptDiscretization2D::setFileOutput(int cycles)
{
	this->outputToFile = cycles;
}

double SweptDiscretization2D::calculate(int cycles)
{
	this->converged = false;
	this->oldNorm = 0;
	double outputTime = 0;
	int execFnc = 0;
	double startTime = MPI_Wtime();
	for(int c=1;c<=cycles;c++)
	{	
		//Build the first Top Pyramid
		up->build(execFnc);
		MPI_Isend(up->getWestPanel() ,communicationSize,MPI_DOUBLE,pg.Nrank ,2,MPI_COMM_WORLD,&reqs[1]);		
		MPI_Isend(up->getNorthPanel(),communicationSize,MPI_DOUBLE,pg.Wrank,1,MPI_COMM_WORLD,&reqs[0]);
		MPI_Irecv(eastPanel,communicationSize,MPI_DOUBLE,pg.Srank,2,MPI_COMM_WORLD,&reqs[2]);	
		MPI_Irecv(southPanel,communicationSize,MPI_DOUBLE,pg.Erank,1,MPI_COMM_WORLD,&reqs[3]);
		
		//Build the fist pair of Bridges
		MPI_Wait(&reqs[2],MPI_STATUS_IGNORE);		
		hb->setEastWestPanels(eastPanel,up->getEastPanel());
		hb->build(execFnc);
		MPI_Isend(hb->getNorthPanel(),communicationSize,MPI_DOUBLE,pg.Wrank ,1,MPI_COMM_WORLD,&reqs[2]);

		MPI_Wait(&reqs[3],MPI_STATUS_IGNORE);
		vb->setNorthSouthPanels(up->getSouthPanel(),southPanel);
		vb->build(execFnc);
		MPI_Isend(vb->getWestPanel(),communicationSize,MPI_DOUBLE,pg.Nrank,2,MPI_COMM_WORLD,&reqs[3]);
		
		MPI_Wait(&reqs[0],MPI_STATUS_IGNORE);
		MPI_Wait(&reqs[1],MPI_STATUS_IGNORE);

		MPI_Irecv(southPanel,communicationSize,MPI_DOUBLE,pg.Erank,1,MPI_COMM_WORLD,&reqs[0]);
		MPI_Irecv(eastPanel,communicationSize,MPI_DOUBLE,pg.Srank,2,MPI_COMM_WORLD,&reqs[1]);

		MPI_Wait(&reqs[0],MPI_STATUS_IGNORE);
		MPI_Wait(&reqs[1],MPI_STATUS_IGNORE);
		MPI_Wait(&reqs[2],MPI_STATUS_IGNORE);
		MPI_Wait(&reqs[3],MPI_STATUS_IGNORE);
		
		//Build the firse Down Pyramid
		dp->setPanels(hb->getSouthPanel(),southPanel,eastPanel,vb->getEastPanel());
		dp->build(execFnc);
		execFnc += (n)/2;
		execFnc = execFnc % substeps;
		
		//Build the second Up Pyramid
		up->build(execFnc);
		MPI_Isend(up->getEastPanel() ,communicationSize,MPI_DOUBLE,pg.Srank ,1,MPI_COMM_WORLD,&reqs[0]);
		MPI_Isend(up->getSouthPanel(),communicationSize,MPI_DOUBLE,pg.Erank,2,MPI_COMM_WORLD,&reqs[1]);
		MPI_Irecv(eastPanel,communicationSize,MPI_DOUBLE,pg.Nrank,1,MPI_COMM_WORLD,&reqs[2]);
		MPI_Irecv(southPanel,communicationSize,MPI_DOUBLE,pg.Wrank,2,MPI_COMM_WORLD,&reqs[3]);
		
		//Build the second pair of Bridges
		MPI_Wait(&reqs[2],MPI_STATUS_IGNORE);
		hb->setEastWestPanels(up->getWestPanel(),eastPanel);
		hb->build(execFnc);
		MPI_Isend(hb->getSouthPanel(),communicationSize,MPI_DOUBLE,pg.Erank,1,MPI_COMM_WORLD,&reqs[2]);

		MPI_Wait(&reqs[3],MPI_STATUS_IGNORE);
		vb->setNorthSouthPanels(southPanel,up->getNorthPanel());
		vb->build(execFnc);
		MPI_Isend(vb->getEastPanel(),communicationSize,MPI_DOUBLE,pg.Srank,2,MPI_COMM_WORLD,&reqs[3]);
		
		MPI_Wait(&reqs[0],MPI_STATUS_IGNORE);
		MPI_Wait(&reqs[1],MPI_STATUS_IGNORE);
				
		MPI_Irecv(northPanel,communicationSize,MPI_DOUBLE,pg.Wrank,1,MPI_COMM_WORLD,&reqs[0]);
		MPI_Irecv(westPanel,communicationSize,MPI_DOUBLE,pg.Nrank,2,MPI_COMM_WORLD,&reqs[1]);

		MPI_Wait(&reqs[0],MPI_STATUS_IGNORE);
		MPI_Wait(&reqs[1],MPI_STATUS_IGNORE);
		MPI_Wait(&reqs[2],MPI_STATUS_IGNORE);
		MPI_Wait(&reqs[3],MPI_STATUS_IGNORE);

		//Build the second Down Pyramid, which completes the cycle
		dp->setPanels(northPanel,hb->getNorthPanel(),vb->getWestPanel(),westPanel);
		dp->build(execFnc);
		execFnc += (n)/2;
		execFnc = execFnc % substeps;

		if((outputToFile != -1) && (c % outputToFile == 0))
		{
			double outputStart = MPI_Wtime();
			//for(int i=0;i<this->outputLength;i++)
			for(int i=1;i<2;i++)
			{
				char filename[80];
				memset(filename,'\0',80);
				sprintf(filename,"output%d_%d.jpg",i,c);				
				string file(outputDirectory + "/" + filename);
				string otherFile(outputDirectory + "/" + "output.jpg");
				//printf("Generating Output File: %s\n",file.c_str());
				this->allGatherOutputToJpeg(i,file,otherFile);				
				//if(pg.rank == 0)printf("Generating Output File: %s - DONE!\n",file.c_str());
				if(pg.rank == 0)printf("Generating Output File - DONE!\n");
			}
			//printf("\n");
			outputTime += MPI_Wtime()-outputStart;
		}

		if((this->convergenceCheckFreq != -1) && (c % this->convergenceCheckFreq == 0))
		{
			this->reportConvergence();
			if(this->converged) break;
		}
	}	
	return (MPI_Wtime() - startTime) - outputTime;
}

void SweptDiscretization2D::allGatherOutputToFile(int dataPoint,string filename)
{

	void *buffer = NULL;
	FILE *output;
	if(pg.rank == 0)
	{
		MPI_Alloc_mem(foundationSize * pg.mpiSize * sizeof(double), MPI_INFO_NULL, &buffer);		
		output = fopen(filename.c_str(),"wb");
	}

	MPI_Win_fence((MPI_MODE_NOPUT | MPI_MODE_NOPRECEDE), foundationWindow);
	if(pg.rank == 0)
	{
		for(int r=0;r<pg.mpiSize;r++)
		{
			MPI_Get((char*)buffer + (r * foundationSize * sizeof(double)), foundationSize * sizeof(double), MPI_BYTE, r, 0, foundationSize * sizeof(double), MPI_BYTE, foundationWindow);			
		}
	}
	MPI_Win_fence(MPI_MODE_NOSUCCEED, foundationWindow);
	
	if(pg.rank == 0)
	{
		int w = (n * pg.xNodes);
		int h = (n * pg.yNodes);
		int resultArraySize = w * h;
		if(resultArray == NULL)
			resultArray = (double*) malloc(resultArraySize * sizeof(double));
		
		for(int r=0;r<pg.mpiSize;r++)
		{
			double *processing = (double*)buffer + (foundationSize * r);			
			int jIndex = (r % (pg.xNodes*pg.yNodes)) / pg.xNodes;
			int iIndex = r % pg.xNodes;
			for(int j=1;j<n+1;j++)
			{
				for(int i=1;i<n+1;i++)
				{
					int iGlobal = n*iIndex + (i-1);
					int jGlobal = n*jIndex + (j-1);
					int index   = this->ijToIndex(i,j);
					double val  = processing[index + constants + dataPoint];
					int resultIndex = (iGlobal + jGlobal * n * pg.xNodes);
					resultArray[resultIndex] = val;
					//printf("Result Index = %d -- Global[%d][%d] = %f\n",resultIndex,iGlobal,jGlobal,val);					
				}
			}		
		}
		fwrite((const void*)resultArray,sizeof(double),resultArraySize,output);
		fclose(output);
		MPI_Free_mem(buffer);
				
	}
	MPI_Barrier(MPI_COMM_WORLD);
}

void SweptDiscretization2D::printFullFoundation(int dataPoint)
{
	for(int j=0;j<=n-1+2;j++)
	{
		for(int i=0;i<=n-1+2;i++)
		{
			printf("%.1f ",foundation[ijToIndex(i,j) + constants + dataPoint]);
		}
		printf("\n");
	}
	printf("\n\n");
}


void SweptDiscretization2D::printFoundation(int dataPoint)
{
	for(int j=1;j<n-1+2;j++)
	{
		for(int i=1;i<n-1+2;i++)
		{
			printf("%.8f ",foundation[ijToIndex(i,j) + constants + dataPoint]);
		}
		printf("\n");
	}
	printf("\n\n");
}


void SweptDiscretization2D::printFoundationHex(int dataPoint)
{
	for(int j=1;j<n-1+2;j++)
	{
		for(int i=1;i<n-1+2;i++)
		{
			DebugUtils::printHex(foundation[ijToIndex(i,j) + constants + dataPoint]);
			printf(" ");
		}
		printf("\n");
	}
	printf("\n\n");
}

void SweptDiscretization2D::printFullFoundationHex(int dataPoint)
{
	for(int j=0;j<=n-1;j++)
	{
		for(int i=0;i<=n-1;i++)
		{
			DebugUtils::printHex(foundation[ijToIndex(i,j) + constants + dataPoint]);
			printf(" ");
		}
		printf("\n");
	}
	printf("\n\n");
}

SweptDiscretization2D::~SweptDiscretization2D(void)
{
	delete up;
	delete dp;
	delete hb;
	delete vb;
	delete[] staging;
	delete[] northPanel;
	delete[] southPanel;
	delete[] eastPanel;
	delete[] westPanel;
}
