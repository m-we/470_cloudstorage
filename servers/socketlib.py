import os
import socket

def send_msg(sock, *msgs):
    for msg in msgs:
        if type(msg) == str:
            msg = bytes(msg, 'utf-8')
        elif type(msg) == int:
            msg = msg.to_bytes(4, 'big')

        sock.sendall(len(msg).to_bytes(4, 'big'))
        sock.sendall(msg)

def recv_b(sock, num):
    data = b''
    while len(data) < num:
        data += sock.recv(num-len(data))
    return data

def recv_msg_w_size(sock, typ=bytes):
    try:
        msg_size = int.from_bytes(recv_b(sock, 4), 'big')
    except:
        return b'', 0

    msg = recv_b(sock, msg_size)
    if typ == int:
        return int.from_bytes(msg, 'big'), msg_size
    elif typ == str:
        return str(msg, 'utf-8'), msg_size
    else:
        return msg, msg_size

def recv_msg(sock, typ=bytes):
    msg, msg_size = recv_msg_w_size(sock, typ)
    return msg

def send_file(sock, fname):
    fsize = os.stat(fname).st_size
    fsent = 0
    send_msg(sock, fname, fsize)
    with open(fname, 'rb') as fp:
        while fsent < fsize:
            msg_size = min(1024, fsize - fsent)
            msg = fp.read(msg_size)
            send_msg(sock, msg)
            fsent += msg_size

def recv_file(sock, fp):
    fname = recv_msg(sock, str)
    fsize = recv_msg(sock, int)

    frecv = 0
    while frecv < fsize:
        msg, msg_size = recv_msg_w_size(sock)
        fp.write(msg)
        frecv += msg_size
    return fname

def relay_file(sock, *dests):
    fname = recv_msg(sock, str)
    fsize = recv_msg(sock, int)

    for dest in dests:
        send_msg(dest, fname, fsize)
    
    frecv = 0
    while frecv < fsize:
        msg, msg_size = recv_msg_w_size(sock)
        for dest in dests:
            send_msg(dest, msg)
        frecv += msg_size
