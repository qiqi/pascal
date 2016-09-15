#ifndef SOCKET_H
#define SOCKET_H
#ifdef _WIN32

#include <WinSock2.h>
#include "string.h"
#include <string>
#include <Windows.h>
#include <ws2tcpip.h>
#pragma comment(lib, "Ws2_32.lib")

enum TypeSocket {BlockingSocket, NonBlockingSocket};
using namespace std;
class Socket {
public:
	Socket(SOCKET s);
	Socket();
	~Socket();
	int sendLine( std::string& );
	int recvLine( std::string& );  
	bool send(int msgSize,char* msg);
	bool recv(int msgSize,char* msg);
	void  close();
	void Start();
    void End();

protected:
  friend class ServerSocket;  

private:
	SOCKET s_;
};

#else

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <unistd.h>
#include <string>
#include <arpa/inet.h>
#include "SocketException.h"

const int MAXHOSTNAME = 200;
const int MAXCONNECTIONS = 5;
const int MAXRECV = 500;
//const int MSG_NOSIGNAL = 0; // defined by dgame

class Socket
{
public:
	Socket();
	~Socket();
	bool create();
	bool bind ( const int port );
	bool listen() const;
	bool accept ( Socket* );

	bool connect ( const std::string host, const int port );

	bool send ( const std::string ) const;
	bool send(int msgSize,char* msg);
	bool recv(int msgSize,char* msg);
	int recv ( std::string& ) const;
	bool is_valid() const { return m_sock != -1; }
	int sendLine( std::string& );
	int recvLine( std::string& );
	int recvLine2( std::string& );
	void  close();

private:
	int m_sock;
	sockaddr_in m_addr;
};

#endif
#endif

