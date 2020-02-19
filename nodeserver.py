import os
import socket
import sys

import socketlib

STORAGE_DIR = ''

def dest_get(user, file_name, chunk_no):
    if not os.path.isdir(STORAGE_DIR + '/' + user):
        os.makedirs(STORAGE_DIR + '/' + user)
    return '{}{}/{}{}'.format(STORAGE_DIR, user, file_name, chunk_no)

def handle_upload(sock):
    global STORAGE_DIR
    user = socketlib.recv_msg(sock, str)
    fdir = STORAGE_DIR + user + '/'
    if not os.path.isdir(fdir):
        os.makedirs(fdir)

    fd = open(fdir + 'tmp.dat', 'wb')
    fname = socketlib.recv_file(sock, fd)
    fd.close()
    os.rename(fdir + 'tmp.dat', fdir + fname)

def handle_delete(sock):
    user = socketlib.recv_msg(sock, str)
    fname = socketlib.recv_msg(sock, str)
    chunk_no = socketlib.recv_msg(sock, str)

    dest = dest_get(user, fname, chunk_no)
    print('deleting {}'.format(dest))
    if os.path.isfile(dest):
        os.remove(dest)
    else:
        print('\tnot found')

def handle_download(sock):
    user = socketlib.recv_msg(sock, str)
    fname = socketlib.recv_msg(sock, str)
    chunk_no = socketlib.recv_msg(sock, int)

    print('{}: {} chunk{} requested'.format(user, fname, chunk_no))
    dest = dest_get(user, fname, chunk_no)
    socketlib.send_file(sock, dest)

def handle(sock):
    msg_size = 1
    while msg_size != 0:
        cmd, msg_size = socketlib.recv_msg_w_size(sock, str)
        if msg_size == 0:
            return

        if cmd == 'upload':
            handle_upload(sock)
        elif cmd == 'delete':
            handle_delete(sock)
        elif cmd == 'download':
            handle_download(sock)
        elif cmd == 'test':
            pass

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
