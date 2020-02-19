import getpass
import hashlib
import json
import os
import socket
import sys

import socketlib

# Salt & hash a string.
def hash_pwd(pwd):
    salted = pwd + 'The quick br0wn fox jump3d over the l4zy dog.'
    return hashlib.sha256(salted.encode('utf-8')).hexdigest()

def file_upload(sock, fname):
    fsize = os.stat(fname).st_size
    ftotl = fsize + 4 - (fsize % 4)
    socketlib.send_msg(sock, 'upload', fname, ftotl)

    fsent = 0
    with open(fname, 'rb') as fp:
        while fsent < fsize:
            sock.sendall(fp.read(min(1024,fsize-fsent)))
            fsent += min(1024,fsize-fsent)
    sock.sendall((4-fsize%4)*bytes(str(4-fsize%4),'utf-8')) # pad

def file_download(sock, fname):
    with open(fname, 'wb') as fp:
        while socketlib.recv_msg(sock, str) != 'end':
            socketlib.recv_file(sock, fp)

def handle_createaccount(sock, parts):
    socketlib.send_msg(sock, 'user_add', parts[1], hash_pwd(parts[2]))
    if socketlib.recv_msg(sock, str) == 'y':
        print('Account created')
    else:
        print('Account creation failed')

def handle_logout(sock):
    socketlib.send_msg(sock, 'logout')
    sock.close()
    exit()

def handle_list(sock):
    socketlib.send_msg(sock, 'list')
    for file in json.loads(socketlib.recv_msg(sock, str)):
        print(file)

def handle_upload(sock, file):
    if not os.path.isfile(file):
        print('Cannot find "{}"'.format(file))
        return
    socketlib.send_msg(sock, 'list')
    if os.path.basename(file) in json.loads(socketlib.recv_msg(sock, str)):
        print('The name "{}" is taken already'.format(file))
        return
    file_upload(sock, file)

def handle_delete(sock, file):
    socketlib.send_msg(sock, 'list')
    if not file in json.loads(socketlib.recv_msg(sock, str)):
        print('File "{}" not found, cannot delete'.format(file))
        return
    socketlib.send_msg(sock, 'delete', file)

def handle_download(sock, file):
    socketlib.send_msg(sock, 'download', file)
    if socketlib.recv_msg(sock, str) == 'n':
        print('File "{}" could not be retrieved'.format(file))
        return
    file_download(sock, file)

def handle_help():
    print("""### commands ###
list
    List all files uploaded for the current user.
upload <file>
    Upload a file to the server.
download <file>
    Download a file from the server.
delete <file>
    Delete a file from the server.
logout
    Log out of the server.
""")

def handle(sock, cmd):
    parts = cmd.split(' ')

    if parts[0] == 'createaccount':
        handle_createaccount(sock, parts)
    elif parts[0] == 'logout':
        handle_logout(sock)
    elif parts[0] == 'list':
        handle_list(sock)
    elif parts[0] == 'upload':
        del parts[0]
        for file in parts:
            handle_upload(sock, file)
    elif parts[0] == 'delete':
        del parts[0]
        for file in parts:
            handle_delete(sock, file)
    elif parts[0] == 'download':
        del parts[0]
        for file in parts:
            handle_download(sock, file)
    elif parts[0] == 'help':
        handle_help()
    else:
        print('unknown command, type help for a list of commands')

def main():
    sock = socket.socket()
    sock.connect((sys.argv[1], int(sys.argv[2])))

    user = input('username: ')
    pwd = getpass.getpass('password: ')
    hashed = hash_pwd(pwd)
    socketlib.send_msg(sock, 'login', user, hashed)

    if socketlib.recv_msg(sock, str) != 'y':
        print('Login failed')
        sock.close()
        return
    handle_help()

    while (cmd := input('> ')) != '':
        handle(sock, cmd)
    sock.close()

if __name__ == '__main__':
    main()
