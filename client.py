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

# Upload a file to storageserver in 1 MB chunks. First, read 1 MB into a
# separate file, then call socketlib.send_file() on that file. Delete the file
# and increment chunk number.
def file_upload(sock, fname):
    fsize = os.stat(fname).st_size
    fsent = 0
    chunk_no = 0

    with open(fname, 'rb') as fr:
        while fsent < fsize:
            # file.txt.chunk27, file.txt.chunk28, etc.
            fwname = os.path.basename(fname) + '.chunk' + str(chunk_no)
            # If there is < 1 MB left to send, set the chunk_size to that.
            chunk_size = min(1024**2, fsize - fsent)
            # Track how many bytes of the current chunk have been sent.
            chunk_curr = 0

            with open(fwname, 'wb') as fw:
                while chunk_curr < chunk_size:
                    fw.write(fr.read(1024))
                    chunk_curr += 1024
            fsent += chunk_size

            # Let storageserver know a file is being uploaded. Include file
            # name and chunk_no so it can route to the correct node servers.
            socketlib.send_msg(sock, 'upload', fname, chunk_no)
            socketlib.send_file(sock, fwname)
            print('{}/{} MB sent'.format(round(fsent/1024**2,2),
                                         round(fsize/1024**2,2)), end='\r')
            chunk_no += 1
            # Remove the chunk file when finished.
            os.remove(fwname)
    print('')

# Downloading is much easier, just call socketlib.recv_file() into the same
# file descriptor until every chunk has been sent.
def file_download(sock, fname):
    with open(fname, 'wb') as fd:
        while socketlib.recv_msg(sock, str) != 'end':
            socketlib.recv_file(sock, fd)

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

def handle_upload(sock, parts):
    if not os.path.isfile(parts[1]):
        print('Cannot find that file')
        return

    socketlib.send_msg(sock, 'list')
    if os.path.basename(parts[1]) in json.loads(socketlib.recv_msg(sock, str)):
        print('A file of that name already exists, cannot upload')
        return

    file_upload(sock, parts[1])

def handle_delete(sock, parts):
    socketlib.send_msg(sock, 'delete', parts[1])

def handle_download(sock, parts):
    socketlib.send_msg(sock, 'download', parts[1])
    if socketlib.recv_msg(sock, str) == 'n':
        print('File could not be retrieved')
        return
    file_download(sock, parts[1])

def handle(sock, cmd):
    parts = cmd.split(' ')

    if parts[0] == 'createaccount':
        handle_createaccount(sock, parts)
    elif parts[0] == 'logout':
        handle_logout(sock)
    elif parts[0] == 'list':
        handle_list(sock)
    elif parts[0] == 'upload':
        handle_upload(sock, parts)
    elif parts[0] == 'delete':
        handle_delete(sock, parts)
    elif parts[0] == 'download':
        handle_download(sock, parts)
    elif parts[0] == 'help':
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

    while (cmd := input('> ')) != '':
        handle(sock, cmd)
    sock.close()

if __name__ == '__main__':
    main()
