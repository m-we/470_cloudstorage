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
    #sock = SOCKS[0]

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

def process(cmd, sock_user, sock_node0):
    global LOGGED_IN
    parts = cmd.split(' ')
    if cmd.startswith('newuser '):
        socketlib.send_msg(sock_user, 'user_add', parts[1], parts[2])

    elif cmd.startswith('login '):
        salted = parts[2] + 'The quick br0wn fox jump3d over the l4zy dog.'
        hashed = hashlib.sha256(salted.encode('utf-8')).hexdigest()
        socketlib.send_msg(sock_user, 'user_find', parts[1], hashed)
        reply = str(socketlib.recv_msg(sock_user), 'utf-8')
        if reply == 'y':
            print('Login successful')
            LOGGED_IN = parts[1]
        else:
            print('Login failed')

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

if __name__ == '__main__':
    sock_user = socket.socket()
    sock_user.connect(('localhost', 50000))
    sock_node0 = socket.socket()
    sock_node0.connect(('localhost', 50001))
    
    cmd = 1
    while cmd != '':
        cmd = input('> ')
        process(cmd, sock_user, sock_node0)
