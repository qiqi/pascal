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

#ifndef H_DEBUGUTILS
#define H_DEBUGUTILS

#include "stdio.h"

class DebugUtils
{
public:

	static inline void printHex(double a)
	{
		int i;
		unsigned char *b = (unsigned char *) &a;
		if(a<0)printf("-");
		else printf(" ");
		for(i = 0; i < 8; i++)
		{
			printf("%02X", b[7-i]);
		}	
	}	
};

#endif