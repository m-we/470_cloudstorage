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
def user_add(user, hashed):
    table = table_get()
    if user in table:
        print('user "{}" already exists'.format(user))
        return -1
    table[user] = {'hashed':hashed,'files':{}}
    table_save(table)
    return 0

def handle(sock):
    msg_size = 1
    while msg_size != 0:
        msg, msg_size = socketlib.recv_msg_w_size(sock)
        if msg_size == 0:
            return

        cmd = str(msg, 'utf-8')
        parts = cmd.split(' ')

        ### user_add ###
        if parts[0] == 'user_add':
            result = user_add(parts[1], parts[2])
            socketlib.send_msg(sock, result)

        ### user_find ###
        elif cmd == 'user_find':
            user = str(socketlib.recv_msg(sock), 'utf-8')
            hashed = str(socketlib.recv_msg(sock), 'utf-8')
            table = table_get()
            if not user in table:
                socketlib.send_msg(sock, 'n')
                continue
            if table[user]['hashed'] == hashed:
                socketlib.send_msg(sock, 'y')
            else:
                socketlib.send_msg(sock, 'n')

        ### list ###
        elif cmd == 'list':
            user = socketlib.recv_msg(sock, str)
            table = table_get()
            file_list = [file for file in table[user]['files']]
            byte_data = json.dumps(file_list).encode('utf-8')
            socketlib.send_msg(sock, byte_data)

        ### upload ###
        elif cmd == 'upload':
            user = socketlib.recv_msg(sock, str)
            fname = socketlib.recv_msg(sock, str)
            chunk_no = str(socketlib.recv_msg(sock, int))
            node_no = socketlib.recv_msg(sock, int)

            table = table_get()
            if not fname in table[user]['files']:
                table[user]['files'][fname] = {}
            if not chunk_no in table[user]['files'][fname]:
                table[user]['files'][fname][chunk_no] = [node_no]
            if not node_no in table[user]['files'][fname][chunk_no]:
                table[user]['files'][fname][chunk_no].append(node_no)
            table_save(table)

        ### delete ###
        elif cmd == 'delete':
            user = socketlib.recv_msg(sock, str)
            fname = socketlib.recv_msg(sock, str)

            table = table_get()
            byte_data = json.dumps(table[user]['files'][fname]).encode('utf-8')
            socketlib.send_msg(sock, byte_data)
            del table[user]['files'][fname]
            table_save(table)

        ### download ###
        elif cmd == 'download':
            user = socketlib.recv_msg(sock, str)
            fname = socketlib.recv_msg(sock, str)

            table = table_get()
            if not user in table:
                socketlib.send_msg(sock, 'n')
                continue
            if not fname in table[user]['files']:
                socketlib.send_msg(sock, 'n')
                continue
            byte_data = json.dumps(table[user]['files'][fname]).encode('utf-8')
            socketlib.send_msg(sock, 'y', byte_data)

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
    #user_table = init_table()
    #user_add('admin', 'admin')
