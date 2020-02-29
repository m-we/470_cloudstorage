import datetime
import hashlib
import json
import os
import socket
import sys

import socketlib

# Get the DB table from users.json.
def table_get():
    if not os.path.isfile('users.json'):
        with open('users.json', 'w') as fd:
            fd.write('{}')
            return {}
    with open('users.json', 'r') as fd:
        return json.load(fd)

# Save the table to users.json.
def table_save(table):
    with open('users.json', 'w') as fd:
        json.dump(table, fd, indent=1, sort_keys=True)

# Add the username with pw hashed if it does not already exist. Send 0 to
# middleware server if successful, -1 if not.
def handle_createaccount(sock):
    table = table_get()
    user = socketlib.recv_msg(sock, str)
    hashed = socketlib.recv_msg(sock, str)
    if user in table:
        socketlib.send_msg(sock, -1)
        return
    table[user] = {'hashed': hashed, 'files': {}}
    table_save(table)
    socketlib.send_msg(sock, 0)

# AKA "login": check that the hash sent matches that in users.json for the given
# user. If it does, send 'y'. If not, 'n'.
def handle_user_find(sock):
    user = socketlib.recv_msg(sock, str)
    hashed = socketlib.recv_msg(sock, str)
    table = table_get()
    if not user in table:
        socketlib.send_msg(sock, 'n')
        return
    if table[user]['hashed'] == hashed:
        socketlib.send_msg(sock, 'y')
    else:
        socketlib.send_msg(sock, 'n')

# Send a list of uploaded files for the given user.
def handle_list(sock):
    user = socketlib.recv_msg(sock, str)
    table = table_get()
    file_list = [file for file in table[user]['files']]
    socketlib.send_msg(sock, json.dumps(file_list).encode('utf-8'))

# Add a chunk to the users.json list. Format is:
# {'admin': {
#       'hashed': 'abcdef...',
#       'files': {
#           'cat.jpg': {
#               '.A1': [0],
#               '.B1': [1],
def handle_upload(sock):
    user = socketlib.recv_msg(sock, str)
    fname = socketlib.recv_msg(sock, str)
    chunk_no = socketlib.recv_msg(sock, str)
    node_no = socketlib.recv_msg(sock, int)

    table = table_get()
    if not fname in table[user]['files']:
        table[user]['files'][fname] = {}
    if not chunk_no in table[user]['files'][fname]:
        table[user]['files'][fname][chunk_no] = [node_no]
    if not node_no in table[user]['files'][fname][chunk_no]:
        table[user]['files'][fname][chunk_no].append(node_no)
    table_save(table)

# Remove a file from users.json for user.
def handle_delete(sock):
    user = socketlib.recv_msg(sock, str)
    fname = socketlib.recv_msg(sock, str)

    table = table_get()
    byte_data = json.dumps(table[user]['files'][fname]).encode('utf-8')
    socketlib.send_msg(sock, byte_data)
    del table[user]['files'][fname]
    table_save(table)

# Get a file's list of chunks from users.json and send it.
def handle_download(sock):
    user = socketlib.recv_msg(sock, str)
    fname = socketlib.recv_msg(sock, str)

    table = table_get()
    if not user in table:
        socketlib.send_msg(sock, 'n')
        return
    if not fname in table[user]['files']:
        socketlib.send_msg(sock, 'n')
        return
    byte_data = json.dumps(table[user]['files'][fname]).encode('utf-8')
    socketlib.send_msg(sock, 'y', byte_data)

def handle(sock):
    msg_size = 1
    while msg_size != 0:
        cmd, msg_size = socketlib.recv_msg_w_size(sock, str)
        if msg_size == 0:
            return

        if cmd == 'createaccount':
            handle_createaccount(sock)
        elif cmd == 'user_find':
            handle_user_find(sock)
        elif cmd == 'list':
            handle_list(sock)
        elif cmd == 'upload':
            handle_upload(sock)
        elif cmd == 'delete':
            handle_delete(sock)
        elif cmd == 'download':
            handle_download(sock)

if __name__ == '__main__':
    serversoc = socket.socket()
    serversoc.bind((sys.argv[1], int(sys.argv[2])))
    serversoc.listen(5)
    while True:
        print('listening on {}'.format(sys.argv[2]))
        sock, raddr = serversoc.accept()
        print('accepted connection from {}'.format(raddr))
        handle(sock)
        sock.close()
    serversoc.close()
