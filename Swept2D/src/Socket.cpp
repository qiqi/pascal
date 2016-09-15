#include "Socket.h"
#include <iostream>

using namespace std;

int sendUnit = 1024;
#ifdef _WIN32

void Socket::Start() 
{
    WSADATA info;
    if (WSAStartup(MAKEWORD(2,0), &info)) 
	{
      throw "Could not start WSA";
    }  
}

void Socket::End() 
{
	WSACleanup();
}

Socket::Socket()
{
	s_ = 0;	
	s_ = socket(AF_INET,SOCK_STREAM,0);
	if (s_ == INVALID_SOCKET) 
	{
		throw "INVALID_SOCKET";
	}
}

Socket::Socket(SOCKET s)
{
  s_ = s;
}

Socket::~Socket() 
{
	close();  	
}

void Socket::close() 
{
	closesocket(s_);
}

bool Socket::send(int msgSize,char* msg)
{
	int loopEnd = msgSize/sendUnit;
	int remaining = msgSize%sendUnit;
	for(int x=0;x<loopEnd;x++)
	{
		::send ( s_, msg+x*sendUnit, sendUnit, 0 );
	}
	int status = 0;
	if(remaining != 0)
		status = ::send ( s_, msg+loopEnd*sendUnit, remaining, 0 );
	if ( status == -1 )
		return false;
	else
		return true;
}

bool Socket::recv(int msgSize,char *msg)
{
	int loopEnd = msgSize/sendUnit;
	int remaining = msgSize%sendUnit;
	for(int x=0;x<loopEnd;x++)
	{
		int got = ::recv(s_,msg+x*sendUnit, sendUnit,MSG_WAITALL);
		//printf("Got: %d\n",got);
	}
	int status = 0;
	if(remaining != 0)
		status = ::recv( s_, msg+loopEnd*sendUnit, remaining, MSG_WAITALL);
	if ( status == -1 )
		return false;
	else
		return true;
}

int Socket::sendLine( std::string& s)
{
	s.append("\r\n");
	int sent = ::send(s_,s.c_str(),(int)s.length(),0);		
	return 0;
}

int Socket::recvLine( std::string& s)
{
	while (1) 
	{
		char r;
		switch(::recv(s_, &r, 1, MSG_WAITALL)) 
		{
			case 0: 
				return -1;
			case -1:
				return -1;
		}
		if (r == '\n')
		{
			s += r;
			return 0;
		}
		else
		{
			s += r;
		}			
	}
}
#else
#include "string.h"
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/tcp.h>
#include <stdio.h>

Socket::Socket() : m_sock ( -1 )
{
	memset ( &m_addr,0,sizeof ( m_addr ) );
}

Socket::~Socket()
{
	if ( is_valid() )
		::close ( m_sock );
}

bool Socket::create()
{
	m_sock = socket ( AF_INET,SOCK_STREAM,0 );
	if ( ! is_valid() )
	{
		return false;
	}

	int on = 1;
	setsockopt(m_sock, IPPROTO_TCP, TCP_NODELAY, (char *) &on, sizeof(int));
	if ( setsockopt ( m_sock, SOL_SOCKET, SO_REUSEADDR, ( const char* ) &on, sizeof ( on ) ) == -1 )
	{
		return false;
	}
	
	return true;
}

bool Socket::bind ( const int port )
{
	if ( ! is_valid() )
	{
		return false;
	}
	
	m_addr.sin_family = AF_INET;
	m_addr.sin_addr.s_addr = INADDR_ANY;
	m_addr.sin_port = htons ( port );

	int bind_return = ::bind ( m_sock,( struct sockaddr * ) &m_addr,sizeof ( m_addr ) );

	if ( bind_return == -1 )
	{
		return false;
	}

	return true;
}

bool Socket::listen() const
{
	if ( ! is_valid() )
    {
		return false;
	}    

	int listen_return = ::listen ( m_sock, MAXCONNECTIONS );
	if ( listen_return == -1 )
    {
		return false;
	}
	return true;
}

bool Socket::accept ( Socket *new_socket)
{
	int addr_length = sizeof ( m_addr );
	new_socket->m_sock = ::accept ( m_sock, ( sockaddr * ) &m_addr, ( socklen_t * ) &addr_length );
	return true;  
}

bool Socket::send ( const std::string s ) const
{
	//int status = ::send ( m_sock, s.c_str(), s.size(), MSG_NOSIGNAL );
	int msgSize = s.size();
    int loopEnd = msgSize/sendUnit;
    int remaining = msgSize%sendUnit;
    //printf("SEND: MsgSize: %d - Loop End: %d - remaining: %d\n",msgSize,loopEnd,remaining);
	for(int x=0;x<loopEnd;x++)
	{
		::send ( m_sock, (char*)s.c_str()+x*sendUnit, sendUnit, MSG_WAITALL );
	}
	//printf("Sending: %s\n",s.c_str());
	int status = ::send ( m_sock, (char*)s.c_str()+loopEnd*sendUnit, remaining, MSG_WAITALL );
       	

	if ( status == -1 )
	{
		return false;
    }
	else
    {
		return true;
    }
}

bool Socket::send(int msgSize,char* msg)
{
	int loopEnd = msgSize/sendUnit;
	int remaining = msgSize%sendUnit;
	for(int x=0;x<loopEnd;x++)
	{
		::send ( m_sock, msg+x*sendUnit, sendUnit, MSG_WAITALL );
	}
	int status = 0;
	if(remaining != 0)
	  status = ::send ( m_sock, msg+loopEnd*sendUnit, remaining, MSG_WAITALL );
	if ( status == -1 )
		return false;
	else
		return true;
}

bool Socket::recv(int msgSize,char *msg)
{
	int loopEnd = msgSize/sendUnit;
	int remaining = msgSize%sendUnit;
	for(int x=0;x<loopEnd;x++)
	{
		int got = ::recv(m_sock,msg+x*sendUnit, sendUnit,MSG_WAITALL);
		//printf("Got %d\n",got);
	}
	int status = 0;
	if(remaining != 0)
		status = ::recv( m_sock, msg+loopEnd*sendUnit, remaining, MSG_WAITALL);
	if ( status == -1 )
		return false;
	else
		return true;
}
	

int Socket::recv ( std::string& s ) const
{
	char buf [ MAXRECV + 1 ];
	s = "";
	memset ( buf, 0, MAXRECV + 1 );
	int status = ::recv ( m_sock, buf, MAXRECV, MSG_WAITALL );
	if ( status == -1 )
	{
		std::cout << "status == -1   errno == " << errno << "  in Socket::recv\n";
		return 0;
	}
	else if ( status == 0 )
	{
		return 0;
	}
	else
	{
		s = buf;
	}
	return status;
}

int Socket::sendLine( std::string& s )
{
	s.append("\r\n");
	if ( ! Socket::send ( s ) )
	{
		return -1;
		//throw SocketException ( "Could not write to socket." );
    }
	return 0;
}

int Socket::recvLine( std::string& s )
{
        char r[1];

        while (1)
        {
                int status = ::recv( m_sock, r, 1, 0 );
                if(status == -1 || status == 0)
                {
                        return -1;
                }
                else if (*r == '\n')
                {
                        s += *r;
			//printf("Line Compelted! - %s\n",s.c_str());
                        return 0;
                }
                else
                {
                        s += *r;
                }
        }
}

void Socket::close() 
{
	::close(m_sock);
}

#endif
