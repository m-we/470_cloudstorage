import socket

def recv_msg_w_size(sock):
    try:
        msg_size = int.from_bytes(sock.recv(4), 'big')
    except:
        return b'', 0
    msg = sock.recv(msg_size)
    return msg, msg_size

def recv_msg(sock):
    msg, msg_size = recv_msg_w_size(sock)
    return msg

def send_msg(sock, *msgs):
    for msg in msgs:
        if type(msg) == str:
            msg = bytes(msg, 'utf-8')
        elif type(msg) == int:
            msg = msg.to_bytes(4, 'big')

        sock.sendall(len(msg).to_bytes(4, 'big'))
        sock.sendall(msg)
