import hashlib
import json
import os
import socket
import sys

import socketlib

LOGGED_IN = ''

def chunk_send(sock, fd, user, file_name, chunk_no, chunk_size):
    socketlib.send_msg(sock, 'ca', user, file_name, chunk_no, chunk_size)
    count = 0
    while count < chunk_size:
        msg = fd.read(1024)
        socketlib.send_msg(sock, msg)
        count += len(msg)

def file_upload(sock, user, file_name):
    chunk_dests = {}

    file_size = os.stat(file_name).st_size
    size_sent = 0

    with open(file_name, 'rb') as fd:
        chunk_no = 0
        while size_sent < file_size:
            msg_size = min(file_size - size_sent, 1024**2)
            chunk_send(sock, fd, user, file_name, chunk_no, msg_size)
            #chunk_dests.append('node0')
            chunk_dests[str(chunk_no)] = 'node0'
            chunk_no += 1
            size_sent += msg_size
            print('{} {} MB/{} MB'.format(file_name, round(size_sent/1024**2,2), round(file_size/1024**2,2)), end='\r')
    print('')
    return chunk_dests

def chunk_data_recv(sock):
    file_name = str(socketlib.recv_msg(sock), 'utf-8')
    chunk_no = int.from_bytes(socketlib.recv_msg(sock), 'big')
    print('incoming chunk:\n\tuser {}\n\tfile_name {}\n\tchunk_no {}'.format(LOGGED_IN, file_name, chunk_no))
    return file_name, chunk_no

def chunk_add(sock, nodes):
    print('relaying chunk:')
    file, chunk_no = chunk_data_recv(sock)
    chunk_size = int.from_bytes(socketlib.recv_msg(sock), 'big')

    if chunk_no % 2 == 0:
        sd0 = nodes[0]
        sd1 = nodes[1]
    else:
        sd0 = nodes[2]
        sd1 = nodes[3]

    socketlib.send_msg(sd0, 'upload', LOGGED_IN, file, chunk_no, chunk_size)
    socketlib.send_msg(sd1, 'upload', LOGGED_IN, file, chunk_no, chunk_size)

    data_left = chunk_size
    while data_left > 0:
        msg, msg_size = socketlib.recv_msg_w_size(sock)
        print('got {}/{} bytes'.format(chunk_size - data_left, chunk_size), end='\r')
        data_left -= msg_size
        socketlib.send_msg(sd0, msg)
        socketlib.send_msg(sd1, msg)
    print('got {}/{} bytes'.format(chunk_size - data_left, chunk_size))

'''def chunk_add(sock):
    print('chunk_add called')
    file_name, chunk_no = chunk_data_recv(sock)
    chunk_size = int.from_bytes(socketlib.recv_msg(sock), 'big')

    data_left = chunk_size
    dest_name = LOGGED_IN + '/' + file_name + '.chunk' + str(chunk_no)
    if not os.path.isdir(LOGGED_IN):
        os.mkdir(LOGGED_IN)

    msg_size = 1
    print('expecting {} bytes'.format(chunk_size))
    with open(dest_name, 'wb') as fd:
        while data_left > 0:
            msg, msg_size = socketlib.recv_msg_w_size(sock)
            print('got {}/{} bytes'.format(chunk_size - data_left, chunk_size), end='\r')
            data_left -= msg_size
            fd.write(msg)
        print('got {}/{} bytes'.format(chunk_size - data_left, chunk_size))
    print('')'''

def handle(sock, sock_user, nodes):
    global LOGGED_IN
    msg_size = 1
    while msg_size != 0:
        msg, msg_size = socketlib.recv_msg_w_size(sock)
        if msg_size == 0:
            return

        cmd = str(msg, 'utf-8')
        #parts = cmd.split(' ')

        if cmd == 'user_add':
            user = socketlib.recv_msg(sock)
            hashed = socketlib.recv_msg(sock)

            socketlib.send_msg(sock_user, 'user_add', user, hashed)
            reply = int.from_bytes(socketlib.recv_msg(sock_user), 'big')
            if reply == 0:
                socketlib.send_msg(sock, 'User "{}" created'.format(parts[1]))
            else:
                socketlib.send_msg(sock, 'User already exists')

        elif cmd == 'login':
            if LOGGED_IN != '':
                socketlib.send_msg(sock, 'You are already logged in as {}'.format(LOGGED_IN))
                continue
            user = str(socketlib.recv_msg(sock), 'utf-8')
            hashed = str(socketlib.recv_msg(sock), 'utf-8')
            print('Attempting login for {}'.format(user))
            
            socketlib.send_msg(sock_user, 'user_find', user, hashed)
            reply = str(socketlib.recv_msg(sock_user), 'utf-8')
            print('Reply from userdb was {}'.format(reply))

            if reply == 'y':
                LOGGED_IN = user
                socketlib.send_msg(sock, 'Login successful')
            else:
                socketlib.send_msg(sock, 'Login failed')
                sock.close()

        elif cmd == 'logout':
            LOGGED_IN = ''
            socketlib.send_msg(sock, 'Logged out')
            return

        elif cmd == 'list' or cmd == 'files':
            if LOGGED_IN == '':
                socketlib.send_msg(sock, 'You must be logged in to do this')
                return
            socketlib.send_msg(sock_user, 'list', LOGGED_IN)
            reply = socketlib.recv_msg(sock_user)
            socketlib.send_msg(sock, reply)

        ### upload ###
        elif cmd == 'upload':
            chunk_add(sock, nodes)

        '''cmd = str(msg, 'utf-8')
        parts = cmd.split(' ')

        if cmd.startswith('createaccount '):
            socketlib.send_msg(sock_user, 'user_add', parts[1], parts[2])

        elif cmd.startswith('login '):
            salted = parts[2] + 'The quick br0wn fox jump3d over the l4zy dog.'
            hashed = hashlib.sha256(salted.encode('utf-8')).hexdigest()
            socketlib.send_msg(sock_user, 'user_find', parts[1], hashed)
            reply = str(socketlib.recv_msg(sock_user), 'utf-8')
            if reply == 'y':
                print('Login successful')
                LOGGED_IN = parts[1]
                socketlib.send_msg(sock, 'login successful')
            else:
                print('Login failed')
                socketlib.send_msg(sock, 'login failed')
        elif cmd == 'logout':
            LOGGED_IN = ''

        elif cmd == 'list':
            if LOGGED_IN == '':
                print('you must log in to do this')
                return
            

        elif cmd.startswith('upload '):
            if LOGGED_IN == '':
                print('you must log in to do this')
                return
            chunk_dests = file_upload(sock_node0, LOGGED_IN, parts[1])
            byte_data = json.dumps(chunk_dests)
            socketlib.send_msg(sock_user, 'file_add', LOGGED_IN, parts[1], byte_data)

        elif cmd.startswith('delete '):
            if LOGGED_IN == '':
                print('you must log in to do this')
                return
            socketlib.send_msg(sock_user, 'file_delete', LOGGED_IN, parts[1])
            chunk_data = socketlib.recv_msg(sock_user)
            chunk_locs = json.loads(chunk_data)[0][1]
            for chunk in chunk_locs:
                if chunk_locs[chunk] == 'node0':
                    socketlib.send_msg(sock_node0, 'cd', LOGGED_IN, parts[1], int(chunk))
'''

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

