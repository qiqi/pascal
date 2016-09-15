#ifndef _BASE64_H_
#define _BASE64_H_

#ifdef _WIN32
#include "inttypes.h"
#else
#include <inttypes.h>
#endif

#include <string>
#include "string.h"

#define WHITESPACE 64
#define EQUALS     65
#define INVALID    66
 
using namespace std;

int base64encode(const void* data_buf, size_t dataLength, char* result, size_t resultSize);
int base64encode(const void* data_buf, size_t dataLength, string& result);
int base64decode (char *in, size_t inLen, unsigned char *out, size_t *outLen);

#endif