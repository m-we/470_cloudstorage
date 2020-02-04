import os
import socket

# Communicates w/ a process by sending the message size in 4 bytes before
# sending the message. Integers & strings convered to bytes. Any number of
# args accepted, allowing multiple items to be sent in a single call.
def send_msg(sock, *msgs):
    for msg in msgs:
        if type(msg) == str:
            msg = bytes(msg, 'utf-8')
        elif type(msg) == int:
            msg = msg.to_bytes(4, 'big')

        sock.sendall(len(msg).to_bytes(4, 'big'))
        sock.sendall(msg)

# Comm. protocol: message size is sent in 4 bytes. Rest of message is then
# read and returned. Optional TYP will convert from bytes to str or int if
# specified. Message size also returned.
def recv_msg_w_size(sock, typ=bytes):
    try:
        msg_size = int.from_bytes(sock.recv(4), 'big')
    except:
        return b'', 0
    msg = sock.recv(msg_size)

    if typ == int:
        return int.from_bytes(msg, 'big'), msg_size
    elif typ == str:
        return str(msg, 'utf-8'), msg_size
    else:
        return msg, msg_size

# Calls revc_msg_w_size() and discards the returned message size.
def recv_msg(sock, typ=bytes):
    msg, msg_size = recv_msg_w_size(sock, typ)
    return msg

# Transmits a file through a socket using send_msg(). File name and size are
# sent, followed by the file's contents 1KB at a time. Does not notify the
# recipient that a file is incoming, the calling process needs to do this
# manually.
def send_file(sock, fname):
    #print('send {}:'.format(fname))
    fsize = os.stat(fname).st_size
    fsent = 0
    send_msg(sock, fname, fsize)
    with open(fname, 'rb') as fd:
        while fsent < fsize:
            msg_size = min(1024, fsize - fsent)
            msg = fd.read(msg_size)
            send_msg(sock, msg)
            fsent += msg_size

# Receives a file through a socket and writes to the file descriptor fd.
# File name is returned so that the receiving process can rename if desired.
def recv_file(sock, fd):
    fname = recv_msg(sock, str)
    fsize = recv_msg(sock, int)
    #print('receive: {}'.format(fname))

    frecv = 0
    while frecv < fsize:
        msg, msg_size = recv_msg_w_size(sock)
        fd.write(msg)
        frecv += msg_size
    return fname

# Relays a file sent through send_file() to one or more sockets.
def relay_file(sock, *dests):
    fname = recv_msg(sock, str)
    fsize = recv_msg(sock, int)
    #print('relay: {}'.format(fname))

    for dest in dests:
        send_msg(dest, fname, fsize)
    
    frecv = 0
    while frecv < fsize:
        msg, msg_size = recv_msg_w_size(sock)
        for dest in dests:
            send_msg(dest, msg)
        frecv += msg_size
        #print('{}/{} MB relayed'.format(round(frecv/1024**2,2), round(fsize/1024**2),2), end='\r')
    #print('')
