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

#ifndef H_PROCESSGRAPH
#define H_PROCESSGRAPH

typedef struct
{
	int rank;
	int iIndex;
	int jIndex;
	int xNodes;
	int yNodes;
	int mpiSize;
	int Nrank;
	int Srank;
	int Erank;
	int Wrank;
	int NErank;
	int NWrank;
	int SErank;
	int SWrank;

} ProcessGraph;

typedef struct
{
	unsigned char* data;
	char *hostname;
	int *isWriter;
	int *myWriter;
	int *myListLength;
	int *myList;
} IoInfo;

#endif
