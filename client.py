import getpass
import hashlib
import json
import os
import socket
import sys

import socketlib

def hash_pwd(pwd):
    salted = pwd + 'The quick br0wn fox jump3d over the l4zy dog.'
    return hashlib.sha256(salted.encode('utf-8')).hexdigest()

def chunk_send(sock, fd, file_name, chunk_no, chunk_size):
    socketlib.send_msg(sock, 'upload', file_name, chunk_no, chunk_size)
    count = 0
    while count < chunk_size:
        msg = fd.read(1024)
        socketlib.send_msg(sock, msg)
        count += len(msg)

def file_upload(sock, file_name):
    file_size = os.stat(file_name).st_size
    size_sent = 0

    with open(file_name, 'rb') as fd:
        chunk_no = 0
        while size_sent < file_size:
            msg_size = min(file_size - size_sent, 1024**2)
            chunk_send(sock, fd, file_name, chunk_no, msg_size)
            chunk_no += 1
            size_sent += msg_size
            print('{} {} MB/{} MB'.format(file_name, round(size_sent/1024**2,2), round(file_size/1024**2,2)), end='\r')
    print('')
            

def process(sock, cmd):
    parts = cmd.split(' ')
    ### createaccount ###
    if parts[0] == 'createaccount':
        socketlib.send_msg(sock, 'user_add', parts[1], hash_pwd(parts[2]))
        print(str(socketlib.recv_msg(sock), 'utf-8'))

    ### logout ###
    elif parts[0] == 'logout':
        socketlib.send_msg(sock, 'logout')
        print(str(socketlib.recv_msg(sock), 'utf-8'))
        sock.close()

    ### list ###
    elif parts[0] == 'list' or parts[0] == 'files':
        socketlib.send_msg(sock, 'list')
        reply = json.loads(str(socketlib.recv_msg(sock), 'utf-8'))
        for file in reply:
            print(file)

    ### upload ###
    elif parts[0] == 'upload':
        #socketlib.send_msg(sock, 'upload')
        file_upload(sock, parts[1])

if __name__ == '__main__':
    sock = socket.socket()
    sock.connect((sys.argv[1], int(sys.argv[2])))

    user = input('username: ')
    pwd = getpass.getpass('password: ')
    hashed = hash_pwd(pwd)

    socketlib.send_msg(sock, 'login', user, hashed)
    reply = str(socketlib.recv_msg(sock), 'utf-8')
    if reply == 'Login successful':
        cmd = 1
        while cmd != '':
            cmd = input('> ')
            process(sock, cmd)
