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

# Add a new user.
def user_add(user, password):
    table = table_get()
    if user in table:
        print('user "{}" already exists'.format(user))
        return
    salted = password + 'The quick br0wn fox jump3d over the l4zy dog.'
    hashed = hashlib.sha256(salted.encode('utf-8')).hexdigest()
    table[user] = {'hashed':hashed,'file_table':{}}
    table_save(table)

# Find an existing user.
def user_find(user):
    table = table_get()
    if user in table:
        return table[user]
    print('user "{}" not found'.format(user))

# Add a file to a user's files.
def file_add(user, file_name, file_data):
    table = table_get()
    if not user in table:
        print('user "{}" not found'.format(user))
        return

    file_table = table[user]['file_table']
    if file_name in file_table:
        print('file "{}" already exists'.format(file_name))
        return

    table[user]['file_table'][file_name] = json.loads(file_data)
    table_save(table)

# Find a file for a user.
def file_find(user, method, key, exact=False):
    table = table_get()
    if not user in table:
        print('user "{}" not found'.format(user))
        return

    file_table = table[user]['file_table']
    results = []
    if method == 'file_name':
        for file_name in file_table:
            if not exact and file_name.startswith(key):
                results.append([file_name, file_table[file_name]])
            elif exact and file_name == key:
                results.append([file_name, file_table[file_name]])
    return results

# Remove a file from a user.
def file_remove(user, file_name):
    table = table_get()
    if not user in table:
        print('user "{}" not found'.format(user))
        return

    file_table = table[user]['file_table']
    if not file_name in file_table:
        print('file "{}" not found'.format(file_name))

    del table[user]['file_table'][file_name]
    table_save()

# Update a file for a user.
def file_update(user, file_name, file_data):
    table = table_get()
    if not user in table:
        print('user "{}" not found'.format(user))
        return

    file_table = table[user]['file_table']
    if not file_name in file_table:
        print('file "{}" cannot be updated, it must be added first'.format(file_name))
        return

    table[user]['file_table'][file_name] = file_data
    table_save()

def handle(sock):
    msg_size = 1
    while msg_size != 0:
        msg, msg_size = socketlib.recv_msg_w_size(sock)
        if msg_size == 0:
            return
        cmd = str(msg, 'utf-8')

        ### user_add ###
        if cmd == 'user_add':
            user = str(socketlib.recv_msg(sock), 'utf-8')
            password = str(socketlib.recv_msg(sock), 'utf-8')
            user_add(user, password)

        ### user_find ###
        elif cmd == 'user_find':
            user = str(socketlib.recv_msg(sock), 'utf-8')
            hashed = str(socketlib.recv_msg(sock), 'utf-8')
            table = table_get()
            if not user in table:
                socketlib.send_msg(sock, 'n')
            if table[user]['hashed'] == hashed:
                socketlib.send_msg(sock, 'y')
            else:
                socketlib.send_msg(sock, 'n')

        ### file_add ###
        elif cmd == 'file_add':
            user = str(socketlib.recv_msg(sock), 'utf-8')
            file_name = str(socketlib.recv_msg(sock), 'utf-8')
            file_data = socketlib.recv_msg(sock)
            file_add(user, file_name, file_data)

        ### file_delete ###
        elif cmd == 'file_delete':
            user = str(socketlib.recv_msg(sock), 'utf-8')
            file_name = str(socketlib.recv_msg(sock), 'utf-8')
            print('Searching {}\'s files for {}'.format(user, file_name))
            results = file_find(user, 'file_name', file_name, True)
            print('\t{} results found'.format(len(results)))
            byte_data = json.dumps(results).encode('utf-8')
            socketlib.send_msg(sock, byte_data)

            table = table_get()
            del table[user]['file_table'][file_name]
            table_save(table)

if __name__ == '__main__':
    serversock = socket.socket()
    serversock.bind((sys.argv[1], int(sys.argv[2])))
    serversock.listen(5)
    while True:
        print('listening on {}'.format(sys.argv[2]))
        sock, raddr = serversock.accept()
        print('accepted connection from {}'.format(raddr))
        handle(sock)
        sock.close()
    serversock.close()
    #user_table = init_table()
    #user_add('admin', 'admin')
