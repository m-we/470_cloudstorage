import os
import socket
import sys

import socketlib

STORAGE_DIR = ''

def dest_get(user, file_name, chunk_no):
    if not os.path.isdir(STORAGE_DIR + '/' + user):
        os.makedirs(STORAGE_DIR + '/' + user)
    return '{}/{}/{}.chunk{}'.format(STORAGE_DIR, user, file_name, chunk_no)

def chunk_data_recv(sock):
    user = str(socketlib.recv_msg(sock), 'utf-8')
    file_name = str(socketlib.recv_msg(sock), 'utf-8')
    chunk_no = int.from_bytes(socketlib.recv_msg(sock), 'big')
    print('incoming chunk:\n\tuser {}\n\tfile_name {}\n\tchunk_no {}\n'.format(user, file_name, chunk_no))
    return user, file_name, chunk_no

def chunk_add(sock):
    print('chunk_add called')
    user, file_name, chunk_no = chunk_data_recv(sock)
    chunk_size = int.from_bytes(socketlib.recv_msg(sock), 'big')

    data_left = chunk_size
    dest_name = dest_get(user, file_name, chunk_no)
    msg_size = 1
    print('expecting {} bytes'.format(chunk_size))
    with open(dest_name, 'wb') as fd:
        while data_left > 0:
            msg, msg_size = socketlib.recv_msg_w_size(sock)
            print('got {}/{} bytes'.format(chunk_size - data_left, chunk_size), end='\r')
            data_left -= msg_size
            fd.write(msg)
        print('got {}/{} bytes'.format(chunk_size - data_left, chunk_size))
    print('')

def chunk_delete(sock):
    user, file_name, chunk_no = chunk_data_recv(sock)
    dest_name = dest_get(user, file_name, chunk_no)
    if not os.path.isfile(dest_name):
        print('chunk "{}" not found'.format(dest_name))
        return
    os.remove(dest_name)

def chunk_load(sock):
    user, file_name, chunk_no = chunk_data_recv(sock)
    dest_name = dest_get(user, file_name, chunk_no)
    with open(dest_name, 'rb') as fd:
        while (msg := fd.read(1024)) != b'':
            socketlib.send_msg(sock, msg)

def handle(sock):
    msg_size = 1
    while msg_size != 0:
        msg, msg_size = socketlib.recv_msg_w_size(sock)
        if msg_size == 0:
            return
        cmd = str(msg, 'utf-8')
        if cmd == 'ca':
            chunk_add(sock)
        elif cmd == 'cd':
            chunk_delete(sock)
        elif cmd == 'cl':
            chunk_load(sock)

if __name__ == '__main__':
    STORAGE_DIR = sys.argv[3] + '/'
    if not os.path.isdir(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)
    serversoc = socket.socket()
    serversoc.bind((sys.argv[1], int(sys.argv[2])))
    serversoc.listen(5)
    while True:
        print('listening on {}'.format(sys.argv[2]))
        commsoc, raddr = serversoc.accept()
        handle(commsoc)
        commsoc.close()
    serversoc.close()
