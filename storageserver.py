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

def route_2(nodes, jsn):
    for node in jsn['0']:
        if is_active(nodes[node]):
            return node
    return None

def route_4(nodes):
    n0 = n1 = None
    if is_active(nodes[0]):
        n0 = 0
    elif is_active(nodes[1]):
        n0 = 1
    if is_active(nodes[2]):
        n1 = 2
    elif is_active(nodes[3]):
        n2 = 3
    return n0, n1

def handle(sock, sock_user, nodes):
    global LOGGED_IN
    msg_size = 1
    while msg_size != 0:
        cmd, msg_size = socketlib.recv_msg_w_size(sock, str)
        if msg_size == 0:
            return

        ### createaccount ###
        if cmd == 'user_add':
            user = socketlib.recv_msg(sock)
            hashed = socketlib.recv_msg(sock)
            socketlib.send_msg(sock_user, 'user_add', user, hashed)
            reply = socketlib.recv_msg(sock_user, int)
            if reply == 0:
                socketlib.send_msg(sock, 'User "{}" created'.format(parts[1]))
            else:
                socketlib.send_msg(sock, 'User already exists')

        ### login ###
        elif cmd == 'login':
            if LOGGED_IN != '':
                socketlib.send_msg(sock, 'You are already logged in as {}'.format(LOGGED_IN))
                continue
            user = socketlib.recv_msg(sock, str)
            hashed = socketlib.recv_msg(sock, str)
            print('Attempting login for {}, '.format(user), end='')
            
            socketlib.send_msg(sock_user, 'user_find', user, hashed)
            reply = socketlib.recv_msg(sock_user, str)

            if reply == 'y':
                print('success')
                LOGGED_IN = user
                socketlib.send_msg(sock, 'Login successful')
            else:
                print('failed')
                socketlib.send_msg(sock, 'Login failed')
                sock.close()

        ### logout ###
        elif cmd == 'logout':
            LOGGED_IN = ''
            socketlib.send_msg(sock, 'Logged out')
            return

        ### list ###
        elif cmd == 'list':
            if LOGGED_IN == '':
                socketlib.send_msg(sock, 'You must be logged in to do this')
                return
            socketlib.send_msg(sock_user, 'list', LOGGED_IN)
            reply = socketlib.recv_msg(sock_user)
            socketlib.send_msg(sock, reply)

        ### upload ###
        elif cmd == 'upload':
            fname = socketlib.recv_msg(sock, str)
            chunk_no = socketlib.recv_msg(sock, int)
            #socketlib.send_msg(sock_user, 'upload', LOGGED_IN, fname, chunk_no, 0)

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

        ### delete ###
        elif cmd == 'delete':
            fname = socketlib.recv_msg(sock, str)
            socketlib.send_msg(sock_user, 'delete', LOGGED_IN, fname)
            reply = socketlib.recv_msg(sock_user, str)
            jsn = json.loads(reply)

            for chunk in jsn:
                for node in jsn[chunk]:
                    node_s = nodes[node]
                    print('sending del req for chunk {} to node{}'.format(node, chunk))
                    socketlib.send_msg(node_s, 'delete', LOGGED_IN, fname, int(chunk))

        ### download ###
        elif cmd == 'download':
            fname = socketlib.recv_msg(sock, str)
            socketlib.send_msg(sock_user, 'download', LOGGED_IN, fname)
            reply = socketlib.recv_msg(sock_user, str)
            if reply != 'y':
                socketlib.send_msg(sock, 'n')
                continue

            print('got back y from userdb')

            jsn = json.loads(socketlib.recv_msg(sock_user, str))
            print('json is {}'.format(jsn))
            # single-chunk
            if len(jsn) == 1:
                s0 = route_2(nodes, jsn)
                if s0 == None:
                    socketlib.send_msg(sock, 'n')
                    continue
            # multi-chunk
            else:
                s0, s1 = route_4(nodes)
                if s0 == None or s1 == None:
                    socketlib.send_msg(sock, 'n')
                    continue

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
            
            '''fname = socketlib.recv_msg(sock, str)
            socketlib.send_msg(sock_user, 'download', LOGGED_IN, fname)
            reply = socketlib.recv_msg(sock_user, str)
            if reply == 'y':
                socketlib.send_msg(sock, 'y')
                jsn = json.loads(socketlib.recv_msg(sock_user, str))
                for chunk in jsn:
                    node = nodes[jsn[chunk]]
                    print('requesting chunk {} from node{}'.format(chunk, jsn[chunk]))
                    socketlib.send_msg(node, 'download', LOGGED_IN, fname, int(chunk))
                    socketlib.send_msg(sock, 'download')
                    socketlib.relay_file(node, sock)
                socketlib.send_msg(sock, 'end')
            else:
                socketlib.send_msg(sock, 'n')'''
                
                

if __name__ == '__main__':
    sock_user = socket.socket()
    sock_user.connect((sys.argv[3], int(sys.argv[4])))

    # connect to node servers
    sock_node0 = socket.socket()
    sock_node1 = socket.socket()
    sock_node2 = socket.socket()
    sock_node3 = socket.socket()
    sock_node0.connect(('localhost', 40000))
    sock_node1.connect(('localhost', 40001))
    sock_node2.connect(('localhost', 40002))
    sock_node3.connect(('localhost', 40003))

    nodes = [sock_node0, sock_node1, sock_node2, sock_node3]
    
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

