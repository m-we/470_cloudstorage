import hashlib
import json
import os
import socket
import sys

import socketlib

LOGGED_IN = ''

def is_active(sock):
    try:
        socketlib.send_msg(sock, 'test')
        return True
    except:
        return False

def route_2(nodes, n0, n1):
    if is_active(nodes[n0]):
        return n0
    elif is_active(nodes[n1]):
        return n1
    return None

def handle_createaccount(sock, sock_user):
    user = socketlib.recv_msg(sock)
    hashed = socketlib.recv_msg(sock)
    socketlib.send_msg(sock_user, 'user_add', user, hashed)
    if socketlib.recv_msg(sock_user, int) == 0:
        socketlib.send_msg(sock, 'y')
    else:
        socketlib.send_msg(sock, 'n')

def handle_login(sock, sock_user):
    global LOGGED_IN
    if LOGGED_IN != '':
        print('Repeat login attempt for unknown reason, closing connection')
        LOGGED_IN = ''
        sock.close()
        return

    user = socketlib.recv_msg(sock, str)
    hashed = socketlib.recv_msg(sock, str)
    print('Attempting login for {}, '.format(user), end='')
    socketlib.send_msg(sock_user, 'user_find', user, hashed)
    if socketlib.recv_msg(sock_user, str) == 'y':
        print('success')
        LOGGED_IN = user
        socketlib.send_msg(sock, 'y')
    else:
        print('failed')
        socketlib.send_msg(sock, 'n')
        sock.close()

def handle_list(sock, sock_user):
    socketlib.send_msg(sock_user, 'list', LOGGED_IN)
    socketlib.send_msg(sock, socketlib.recv_msg(sock_user))

def handle_upload(sock, sock_user, nodes):
    fname = os.path.basename(socketlib.recv_msg(sock, str))
    chunk_no = socketlib.recv_msg(sock, int)

    if chunk_no % 2 == 0:
        dest0 = nodes[0]
        dest1 = nodes[1]
        socketlib.send_msg(sock_user, 'upload', LOGGED_IN, fname, chunk_no, 0)
        socketlib.send_msg(sock_user, 'upload', LOGGED_IN, fname, chunk_no, 1)
    else:
        dest0 = nodes[2]
        dest1 = nodes[3]
        socketlib.send_msg(sock_user, 'upload', LOGGED_IN, fname, chunk_no, 2)
        socketlib.send_msg(sock_user, 'upload', LOGGED_IN, fname, chunk_no, 3)

    socketlib.send_msg(dest0, 'upload', LOGGED_IN)
    socketlib.send_msg(dest1, 'upload', LOGGED_IN)
    socketlib.relay_file(sock, dest0, dest1)

def handle_delete(sock, sock_user, nodes):
    fname = socketlib.recv_msg(sock, str)
    socketlib.send_msg(sock_user, 'delete', LOGGED_IN, fname)
    jsn = json.loads(socketlib.recv_msg(sock_user, str))

    for chunk in jsn:
        for node in jsn[chunk]:
            node_s = nodes[node]
            print('sending del req for chunk {} to node{}'.format(node, chunk))
            socketlib.send_msg(node_s, 'delete', LOGGED_IN, fname, int(chunk))

def handle_download(sock, user, nodes):
    fname = socketlib.recv_msg(sock, str)
    socketlib.send_msg(sock_user, 'download', LOGGED_IN, fname)
    if socketlib.recv_msg(sock_user, str) != 'y':
        socketlib.send_msg(sock, 'n')
        return

    jsn = {}
    jsn_wrong = json.loads(socketlib.recv_msg(sock_user, str))
    for c in jsn_wrong:
        jsn[int(c)] = jsn_wrong[c]
    jsn = sorted(jsn)

    print('json is {}'.format(jsn))
    # single-chunk
    if len(jsn) == 1:
        s0 = route_2(nodes, 0, 1)
        if s0 == None:
            socketlib.send_msg(sock, 'n')
            return
    # multi-chunk
    else:
        s0 = route_2(nodes, 0, 1)
        s1 = route_2(nodes, 2, 3)
        if s0 == None or s1 == None:
            socketlib.send_msg(sock, 'n')
            return

    socketlib.send_msg(sock, 'y')
    for chunk in jsn:
        if int(chunk) % 2 == 0:
            node_curr = s0
        else:
            node_curr = s1

        print('requesting chunk {} from node{}'.format(chunk, node_curr))
        socketlib.send_msg(nodes[node_curr], 'download', LOGGED_IN, fname, int(chunk))
        socketlib.send_msg(sock, 'download')
        socketlib.relay_file(nodes[node_curr], sock)
        print('finished chunk {}'.format(chunk))
    socketlib.send_msg(sock, 'end')

def handle(sock, sock_user, nodes):
    global LOGGED_IN
    msg_size = 1
    while msg_size != 0:
        msg, msg_size = socketlib.recv_msg_w_size(sock)
        if msg_size == 0:
            return
        try:
            cmd = str(msg, 'utf-8')
        except:
            print('Input not a string')
            return

        if LOGGED_IN == '' and cmd != 'login':
            return

        if cmd == 'user_add':
            handle_createaccount(sock, sock_user)
        elif cmd == 'login':
            handle_login(sock, sock_user)
        elif cmd == 'logout':
            LOGGED_IN = ''
            return
        elif cmd == 'list':
            handle_list(sock, sock_user)
        elif cmd == 'upload':
            handle_upload(sock, sock_user, nodes)
        elif cmd == 'delete':
            handle_delete(sock, sock_user, nodes)
        elif cmd == 'download':
            handle_download(sock, sock_user, nodes)

        else:
            print('Unexpected input')
            return

if __name__ == '__main__':
    sock_user = socket.socket()
    sock_user.connect((sys.argv[3], int(sys.argv[4])))

    # nodeserver host & port will be argv (5,6)...(11,12)
    nodes = []
    for x in range(4):
        s = socket.socket()
        s.connect((sys.argv[5+x*2],int(sys.argv[6+x*2])))
        nodes.append(s)
    
    serversoc = socket.socket()
    serversoc.bind((sys.argv[1], int(sys.argv[2])))
    serversoc.listen(5)
    while True:
        print('listening on {}'.format(sys.argv[2]))
        sock, raddr = serversoc.accept()
        print('accepted connection from {}'.format(raddr))
        handle(sock, sock_user, nodes)
        LOGGED_IN = ''
        sock.close()
    serversoc.close()

