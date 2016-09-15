#include "ServerSocket.h"
#include "Socket.h"
#ifdef _WIN32
ServerSocket::ServerSocket(int port) 
{
	Start();
	sockaddr_in sa;
	memset(&sa, 0, sizeof(sa));
	int connections = 1;

	sa.sin_family = PF_INET;             
	sa.sin_port = htons(port);          
	s_ = socket(AF_INET, SOCK_STREAM, 0);
	if (s_ == INVALID_SOCKET) 
	{
		throw "INVALID_SOCKET";
	}

	if (bind(s_, (sockaddr *)&sa, sizeof(sockaddr_in)) == SOCKET_ERROR) 
	{
		closesocket(s_);
		throw "INVALID_SOCKET";
	}
  
	listen(s_, connections);                               
}

Socket* ServerSocket::Accept() 
{
	SOCKET new_sock = accept(s_, 0, 0);  
	return new Socket(new_sock);	
}

#else

#include "SocketException.h"


ServerSocket::ServerSocket ( int port )
{
	if ( ! Socket::create() )
	{
		throw SocketException ( "Could not create server socket." );
	}


	if ( ! Socket::bind ( port ) )
	{
		throw SocketException ( "Could not bind to port." );
	}

	if ( ! Socket::listen() )
	{
		throw SocketException ( "Could not listen to socket." );
	}

}

Socket *ServerSocket::Accept ()
{
	Socket *sock = new Socket();
	if ( ! Socket::accept ( sock ) )
	{
		throw SocketException ( "Could not accept socket." );
	}

	return sock;
}

#endif
