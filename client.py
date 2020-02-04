import getpass
import hashlib
import json
import os
import socket
import sys

import socketlib

# Return the SHA-256 hash of a password after salting to avoid sending pwds
# in plaintext.
def hash_pwd(pwd):
    salted = pwd + 'The quick br0wn fox jump3d over the l4zy dog.'
    return hashlib.sha256(salted.encode('utf-8')).hexdigest()

# Read 1MB from a file and then transmit w/ send_file() until the entire file
# has been sent. Assign a number to each chunk that will be used for ID.
def file_upload(sock, fname):
    fsize = os.stat(fname).st_size
    fleft = fsize
    chunk_no = 0

    frb = open(fname, 'rb')
    while fleft > 0:
        fwr_name = '{}.chunk{}'.format(fname, chunk_no)
        fwr = open(fwr_name, 'wb')
        chunk_size = min(1024**2, fleft)
        chunk_curr = 0
        while chunk_curr < chunk_size:
            fwr.write(frb.read(1024))
            chunk_curr += 1024
        fleft -= chunk_size
        fwr.close()

        socketlib.send_msg(sock, 'upload', fname, chunk_no)
        socketlib.send_file(sock, fwr_name)

        print('{}/{} MB sent'.format(round((fsize-fleft)/1024**2,2), round(fsize/1024**2,2)), end='\r')
        
        chunk_no += 1
        os.remove(fwr_name)
    print('')
    frb.close()

def file_download(sock, fname):
    fd = open(fname, 'wb')
    while (st := socketlib.recv_msg(sock, str)) != 'end':
        socketlib.recv_file(sock, fd)

def process(sock, cmd):
    parts = cmd.split(' ')
    ### createaccount ###
    if parts[0] == 'createaccount':
        socketlib.send_msg(sock, 'user_add', parts[1], hash_pwd(parts[2]))
        print(socketlib.recv_msg(sock, str))

    ### logout ###
    elif parts[0] == 'logout':
        socketlib.send_msg(sock, 'logout')
        print(socketlib.recv_msg(sock, str))
        sock.close()

    ### list ###
    elif parts[0] == 'list':
        socketlib.send_msg(sock, 'list')
        reply = json.loads(socketlib.recv_msg(sock, str))
        for file in reply:
            print(file)

    ### upload ###
    elif parts[0] == 'upload':
        if not os.path.isfile(parts[1]):
            print('Cannot find that file')
            return
        socketlib.send_msg(sock, 'list')
        reply = json.loads(socketlib.recv_msg(sock, str))
        if parts[1] in reply:
            print('A file of that name already exists, cannot upload')
            return

        file_upload(sock, parts[1])

    ### delete ###
    elif parts[0] == 'delete':
        socketlib.send_msg(sock, 'delete', parts[1])

    ### download ###
    elif parts[0] == 'download':
        socketlib.send_msg(sock, 'download', parts[1])
        reply = socketlib.recv_msg(sock, str)
        if reply == 'n':
            print('File could not be retrieved')
        else:
            file_download(sock, parts[1])

    ### help ###
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
