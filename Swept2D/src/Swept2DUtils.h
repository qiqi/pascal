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

#ifndef H_SWEPT2DUTILS
#define H_SWEPT2DUTILS

class Swept2DUtils
{
public:

	static inline int ijToIndex(int n,int i,int j,int dataPointSize,int constants)
	{
		int index = j * n + i;
		int constToAdd = (index * constants);
		index = index * dataPointSize;
		index += constToAdd;
		return index;
	}

	static inline int getShrinkingIndex(int n,int level,int dataPointSize,int constants)
	{
		int indexStart = 0;
		for(int c=0;c<level;c++)
		{
			indexStart += (n-2) - (2*c);
		}
		indexStart *= 2;
		int constantsToAdd = indexStart * constants;
		indexStart *= (dataPointSize);	
		indexStart += constantsToAdd;	
		return indexStart;
	}

	static inline int getGrowingIndex(int n,int level,int dataPointSize,int constants)
	{
		int indexStart = 0;
		for(int c=0;c<=level;c++)
		{
			indexStart += (2*c);
		}
		indexStart *= 2;
		int constantsToAdd = indexStart * constants;
		indexStart *= (dataPointSize);	
		indexStart += constantsToAdd;
		return indexStart;
	}
};

#endif