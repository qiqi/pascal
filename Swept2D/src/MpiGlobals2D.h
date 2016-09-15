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

#ifndef H_MPIGLOBALS2D
#define H_MPIGLOBALS2D

#include <mpi.h>
#include <algorithm>
#include <string>
#include "ProcessGraph.h"
#include "ServerSocket.h"
#include "SocketException.h"
#include <string>
#include <iostream>
#include <vector>
#include <cctype>
#include "base64.h"
#ifdef _WIN32
#include <Windows.h>
#else
#include <pthread.h>
#endif

ProcessGraph pg;
IoInfo ioInfo;
IoInfo *ioInfos;
vector<string> *ioHostnames;
vector<int>    *ioRanks;
string constantsArray;
string resultsArray;
vector<string> remoteCommands;
vector<int> remoteCodes;
Socket *connection;
SweptDiscretization2D *swept2d;
unsigned char* constantsArrayBytes;
int remoteConstantsBytes;
#ifdef _WIN32
HANDLE threadHd;
DWORD  threadId;
HANDLE remoteCommandsThreadMutexLock;
#else
pthread_t remoteCommandsThread;
pthread_mutex_t remoteCommandsThreadMutexLock;
#endif

bool addIfNew(vector<string> *hostnames,string hostname,int *index)
{
	for(int i=0;i<(int)hostnames->size();i++)
	{
		if((*hostnames)[i].compare(hostname) == 0)
		{
			*index = i;
			return false;
		}
	}
	*index = hostnames->size();
	hostnames->push_back(hostname);
	return true;
}

static inline std::string &ltrim(std::string &s) 
{
	s.erase(s.begin(), std::find_if(s.begin(), s.end(), std::not1(std::ptr_fun<int, int>(std::isspace))));
    return s;
}

static inline std::string &rtrim(std::string &s) 
{
	s.erase(std::find_if(s.rbegin(), s.rend(), std::not1(std::ptr_fun<int, int>(std::isspace))).base(), s.end());
    return s;
}

static inline std::string &trim(std::string &s) 
{
	return ltrim(rtrim(s));
}

int ijToIndex(int i,int j,int xNodes,int yNodes)
{
	int ii,jj;
	ii = i;
	jj = j;
	if(i==-1)      ii = xNodes-1;
	else if(i==xNodes) ii = 0;
	if(j==-1)      jj = yNodes-1;
	else if(j==yNodes) jj = 0;

	int index = jj * xNodes + ii;
	return index;
}

ProcessGraph getProcessGraph(int myrank,int xNodes,int yNodes,int size)
{
	ProcessGraph pg;
	pg.rank = myrank;
	int j = (myrank % (xNodes*yNodes)) / xNodes;
	int i = myrank % xNodes;
	
	pg.iIndex  = i;
	pg.jIndex  = j;
	pg.xNodes  = xNodes;
	pg.yNodes  = yNodes;
	pg.mpiSize = size;
	pg.Wrank   = ijToIndex(i-1,j,xNodes,yNodes);
	pg.Erank   = ijToIndex(i+1,j,xNodes,yNodes);
	pg.Srank   = ijToIndex(i,j+1,xNodes,yNodes);
	pg.Nrank   = ijToIndex(i,j-1,xNodes,yNodes);				
	return pg;
}

void getIoInfo()
{
	int hostnameLength = 256;
	int dataLength = hostnameLength + (3 * sizeof(int)) + (sizeof(int) * pg.mpiSize);
	//MPI_Alloc_mem(dataLength, MPI_INFO_NULL, &info->data);
	ioInfo.data = (unsigned char*) malloc(dataLength);
	memset(ioInfo.data,'\0',dataLength);	
	ioInfo.hostname      = (char*)ioInfo.data;
	ioInfo.isWriter      = (int*) (ioInfo.data + hostnameLength);
	ioInfo.myWriter      = (int*) (ioInfo.data + hostnameLength + sizeof(int));
	ioInfo.myListLength  = (int*) (ioInfo.data + hostnameLength + sizeof(int) + sizeof(int));
	ioInfo.myList        = (int*) (ioInfo.data + hostnameLength + sizeof(int) + sizeof(int) + sizeof(int));
	
	gethostname(ioInfo.hostname,hostnameLength);
	//printf("HostName = %s\n",ioInfo.hostname);
	unsigned char *allData;
	//MPI_Win ioWindow;
	//MPI_Win_create(info->data,dataLength,1, MPI_INFO_NULL,MPI_COMM_WORLD, &ioWindow);
	//MPI_Win_fence(MPI_MODE_NOPRECEDE, ioWindow);
	if(pg.rank == 0)
	{
		allData = (unsigned char*)malloc((pg.mpiSize-1) * dataLength);
		ioInfos = (IoInfo*) malloc(pg.mpiSize * sizeof(IoInfo));
		ioInfos[0].data = ioInfo.data;
		
		ioInfos[0].hostname      = (char*)ioInfos[0].data;
		ioInfos[0].isWriter      = (int*) (ioInfos[0].data + hostnameLength);
		ioInfos[0].myWriter      = (int*) (ioInfos[0].data + hostnameLength + sizeof(int));
		ioInfos[0].myListLength  = (int*) (ioInfos[0].data + hostnameLength + sizeof(int) + sizeof(int));
		ioInfos[0].myList        = (int*) (ioInfos[0].data + hostnameLength + sizeof(int) + sizeof(int) + sizeof(int));
		
		for(int i=0;i<pg.mpiSize-1;i++)
		{
			int r = i + 1;
			MPI_Recv(allData + (i*dataLength),dataLength,MPI_BYTE,r,1,MPI_COMM_WORLD,MPI_STATUS_IGNORE);
			ioInfos[r].data          = allData + (i*dataLength);
			ioInfos[r].hostname      = (char*)ioInfos[r].data;
			ioInfos[r].isWriter      = (int*) (ioInfos[r].data + hostnameLength);
			ioInfos[r].myWriter      = (int*) (ioInfos[r].data + hostnameLength + sizeof(int));
			ioInfos[r].myListLength  = (int*) (ioInfos[r].data + hostnameLength + sizeof(int) + sizeof(int));
			ioInfos[r].myList        = (int*) (ioInfos[r].data + hostnameLength + sizeof(int) + sizeof(int) + sizeof(int));
		}
		
		//All Hostnames are pupolated.  Process IO Assignment
		
		ioHostnames = new vector<string>();
		ioRanks     = new vector<int>();
		for(int r=0;r<pg.mpiSize;r++)
		{
			int hostIndex;
			bool isNewHost = addIfNew(ioHostnames,ioInfos[r].hostname,&hostIndex);						
			if(isNewHost)
			{
				ioRanks->push_back(r);
				ioInfos[r].isWriter[0]     = 1;
				ioInfos[r].myListLength[0] = 1;
				ioInfos[r].myWriter[0]     = r;
				ioInfos[r].myList[0]       = r;				
			}
			else
			{
				ioInfos[r].myWriter[0] = (*ioRanks)[hostIndex];
				ioInfos[(*ioRanks)[hostIndex]].myList[ioInfos[(*ioRanks)[hostIndex]].myListLength[0]] = r;
				ioInfos[(*ioRanks)[hostIndex]].myListLength[0] += 1;
			}
		}
		
		//End IO Processing
		
	}
	else
	{
		MPI_Send(ioInfo.data,dataLength,MPI_BYTE,0,1,MPI_COMM_WORLD);
	}
	
	if(pg.rank == 0)
	{
		for(int i=0;i<pg.mpiSize-1;i++)
		{
			int r = i + 1;
			MPI_Send(allData + (i*dataLength),dataLength,MPI_BYTE,r,1,MPI_COMM_WORLD);
		}
	}
	else
	{
		MPI_Recv(ioInfo.data,dataLength,MPI_BYTE,0,1,MPI_COMM_WORLD,MPI_STATUS_IGNORE);
	}
	MPI_Barrier(MPI_COMM_WORLD);
	//MPI_Win_fence((MPI_MODE_NOSTORE | MPI_MODE_NOSUCCEED), ioWindow);
	//MPI_Win_free(&ioWindow);
}

void initMPI(int argc, char* argv[],int xNodes,int yNodes,bool remoteService,int port)
{
	int myrank,size;
	MPI_Init(&argc, &argv);
	MPI_Comm_rank(MPI_COMM_WORLD,&myrank);
	MPI_Comm_size(MPI_COMM_WORLD,&size);
	pg = getProcessGraph(myrank,xNodes,yNodes,size);
	getIoInfo();	
}

void finMPI()
{
	MPI_Barrier(MPI_COMM_WORLD);
	MPI_Finalize();
}

#endif
