#ifndef SERVERSOCKET_H
#define SERVERSOCKET_H
#include "Socket.h"

class ServerSocket : public Socket 
{

public:
	ServerSocket(int port);  
	Socket *Accept();
};

#endif

