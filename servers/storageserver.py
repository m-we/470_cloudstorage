import json
import os
import socket
import sys

import socketlib

LOGGED_IN = ''

def is_active(sock):
    try:
        socketlib.send_msg(sock, 'test')
        return True
    except:
        return False

def route_2(nodes, n0, n1):
    if is_active(nodes[n0]):
        return n0
    elif is_active(nodes[n1]):
        return n1
    return None

def handle_createaccount(sock, sock_user):
    user = socketlib.recv_msg(sock)
    hashed = socketlib.recv_msg(sock)
    socketlib.send_msg(sock_user, 'user_add', user, hashed)
    if socketlib.recv_msg(sock_user, int) == 0:
        socketlib.send_msg(sock, 'y')
    else:
        socketlib.send_msg(sock, 'n')

def handle_login(sock, sock_user):
    global LOGGED_IN
    if LOGGED_IN != '':
        print('Repeat login attempt for unknown reason, closing connection')
        LOGGED_IN = ''
        sock.close()
        return

    user = socketlib.recv_msg(sock, str)
    hashed = socketlib.recv_msg(sock, str)
    print('Attempting login for {}, '.format(user), end='')
    socketlib.send_msg(sock_user, 'user_find', user, hashed)
    if socketlib.recv_msg(sock_user, str) == 'y':
        print('success')
        LOGGED_IN = user
        socketlib.send_msg(sock, 'y')
    else:
        print('failed')
        socketlib.send_msg(sock, 'n')
        sock.close()

def handle_list(sock, sock_user):
    socketlib.send_msg(sock_user, 'list', LOGGED_IN)
    socketlib.send_msg(sock, socketlib.recv_msg(sock_user))

def xor(b1, b2):
    return bytes([a^b for a, b in zip(b1, b2)])

def send_node(sock_user, nodes, fname, node_no, f_ext):
    socketlib.send_msg(sock_user, 'upload', LOGGED_IN, fname, f_ext, node_no)
    socketlib.send_msg(nodes[node_no], 'upload', LOGGED_IN)
    socketlib.send_file(nodes[node_no], fname + f_ext)
    os.remove(fname + f_ext)

def handle_delete(sock, sock_user, nodes):
    fname = socketlib.recv_msg(sock, str)
    socketlib.send_msg(sock_user, 'delete', LOGGED_IN, fname)
    jsn = json.loads(socketlib.recv_msg(sock_user, str))

    for chunk in jsn:
        for node in jsn[chunk]:
            node_s = nodes[node]
            print('sending del req for chunk {} to node{}'.format(node, chunk))
            socketlib.send_msg(node_s, 'delete', LOGGED_IN, fname, chunk)

def handle_upload(sock, sock_user, nodes):
    fname = os.path.basename(socketlib.recv_msg(sock, str))
    ftotl = socketlib.recv_msg(sock, int)
    print('Total is: {} bytes'.format(ftotl))
    frecv = 0

    exts = ['.A1','.A2','.B1','.B2']
    for x in range(4):
        with open(fname + exts[x], 'wb') as fp:
            while frecv < (x+1)*ftotl/4:
                data = socketlib.recv_b(sock, min(int((x+1)*ftotl/4)-frecv,1024))
                frecv += len(data)
                fp.write(data)
    print('file received')


    A1 = open(fname + '.A1', 'rb')
    A2 = open(fname + '.A2', 'rb')
    B1 = open(fname + '.B1', 'rb')
    B2 = open(fname + '.B2', 'rb')

    A1_XOR_B1 = open(fname + '.A1_XOR_B1', 'wb')
    A2_XOR_B2 = open(fname + '.A2_XOR_B2', 'wb')
    A2_XOR_B1 = open(fname + '.A2_XOR_B1', 'wb')
    A1_XOR_A2_XOR_B2 = open(fname + '.A1_XOR_A2_XOR_B2', 'wb')

    fdone = 0
    ftotl = int(ftotl / 4)
    while fdone < ftotl:
        b_a1 = A1.read(min(1024,ftotl-fdone))
        b_a2 = A2.read(min(1024,ftotl-fdone))
        b_b1 = B1.read(min(1024,ftotl-fdone))
        b_b2 = B2.read(min(1024,ftotl-fdone))

        b_a1_xor_b1 = xor(b_a1, b_b1)
        b_a2_xor_b2 = xor(b_a2, b_b2)
        b_a2_xor_b1 = xor(b_a2, b_b1)
        b_a1_xor_a2_xor_b2 = xor(xor(b_a1, b_a2), b_b2)

        A1_XOR_B1.write(b_a1_xor_b1)
        A2_XOR_B2.write(b_a2_xor_b2)
        A2_XOR_B1.write(b_a2_xor_b1)
        A1_XOR_A2_XOR_B2.write(b_a1_xor_a2_xor_b2)
        fdone += min(1024,ftotl-fdone)

    A1.close()
    A2.close()
    B1.close()
    B2.close()
    A1_XOR_B1.close()
    A2_XOR_B2.close()
    A2_XOR_B1.close()
    A1_XOR_A2_XOR_B2.close()

    send_node(sock_user, nodes, fname, 0, '.A1')
    send_node(sock_user, nodes, fname, 0, '.A2')
    send_node(sock_user, nodes, fname, 1, '.B1')
    send_node(sock_user, nodes, fname, 1, '.B2')
    send_node(sock_user, nodes, fname, 2, '.A1_XOR_B1')
    send_node(sock_user, nodes, fname, 2, '.A2_XOR_B2')
    send_node(sock_user, nodes, fname, 3, '.A2_XOR_B1')
    send_node(sock_user, nodes, fname, 3, '.A1_XOR_A2_XOR_B2')

exts = {0:['.A1','.A2'],1:['.B1','.B2'],2:['.A1_XOR_B1','.A2_XOR_B2'],
        3:['.A2_XOR_B1','.A1_XOR_A2_XOR_B2']}

def read(fpf, fp):
    while (x := fp.read(1024)) != b'':
        fpf.write(x)
    fp.seek(0)

def readx(fpf, fp0, fp1):
    while (x := fp0.read(1024)) != b'':
        fpf.write(xor(x, fp1.read(1024)))
    fp0.seek(0)
    fp1.seek(0)

def readxx(fpf, fp0, fp1, fp2):
    while (x := fp0.read(1024)) != b'':
        fpf.write(xor(xor(x, fp1.read(1024)), fp2.read(1024)))
    fp0.seek(0)
    fp1.seek(0)
    fp2.seek(0)

# B1 B2 <-> A2_XOR_B1 A1_XOR_A2_XOR_B2
def read3(fpf, fp0, fp1, fp2, fp3):
    while (x := fp0.read(1024)) != b'':
        fpf.write(xor(xor(xor(fp2.read(1024), x), fp3.read(1024)), fp1.read(1024)))
    fp0.seek(0, 0)
    fp1.seek(0, 0)
    fp2.seek(0, 0)
    fp3.seek(0, 0)

def recomb(nodes, avail, fname):
    nodes_done = 0
    np = []
    for n in avail:
        if nodes_done >= 2:
            break
        socketlib.send_msg(nodes[n], 'download', LOGGED_IN, fname, exts[n][0])
        with open(fname + exts[n][0], 'wb') as fp:
            socketlib.recv_file(nodes[n], fp)
        socketlib.send_msg(nodes[n], 'download', LOGGED_IN, fname, exts[n][1])
        with open(fname + exts[n][1], 'wb') as fp:
            socketlib.recv_file(nodes[n], fp)
        nodes_done += 1
        np.append(n)

    fp0 = open(fname + exts[np[0]][0], 'rb')
    fp1 = open(fname + exts[np[0]][1], 'rb')
    fp2 = open(fname + exts[np[1]][0], 'rb')
    fp3 = open(fname + exts[np[1]][1], 'rb')
    fpf = open(fname, 'wb')

    # A1 A2 <-> B1 B2
    if 0 in np and 1 in np:
        read(fpf, fp0)
        read(fpf, fp1)
        read(fpf, fp2)
        read(fpf, fp3)

    # A1 A2 <-> A1_XOR_B1 A2_XOR_B2
    elif 0 in np and 2 in np:
        read(fpf, fp0)
        read(fpf, fp1)
        readx(fpf, fp0, fp2)
        readx(fpf, fp1, fp3)

    # A1 A2 <-> A2_XOR_B1 A1_XOR_A2_XOR_B2
    elif 0 in np and 3 in np:
        read(fpf, fp0)
        read(fpf, fp1)
        readx(fpf, fp1, fp2)
        readxx(fpf, fp0, fp1, fp3)

    # B1 B2 <-> A1_XOR_B1 A2_XOR_B2
    elif 1 in np and 2 in np:
        readx(fpf, fp0, fp2)
        readx(fpf, fp1, fp3)
        read(fpf, fp2)
        read(fpf, fp3)

    # B1 B2 <-> A2_XOR_B1 A1_XOR_A2_XOR_B2
    elif 1 in np and 3 in np:
        read3(fpf, fp0, fp1, fp2, fp3)
        readx(fpf, fp2, fp0)
        read(fpf, fp0)
        read(fpf, fp1)

    # A1B1 A2B2 <-> A2B1 A1A2B2

    # A2B2 + A1A2B2 = A1

    # A2B2 + A1B1 = A1A2B1B2
    # A1A2B1B2 + A1A2B2 = B1
    # A2B1 + B1 = A2

    # A2B2 + A1B1 = A1A2B1B2
    # A1A2B1B2 + A1A2B2 = B1

    # A1A2B2 + A1B1 = A2B1B2
    # A2B1 + A2B1B2 = B2
    elif 2 in np and 3 in np:
        readx(fpf, fp1, fp3)
        read3(fpf, fp0, fp3, fp1, fp2)
        readxx(fpf, fp0, fp1, fp3)
        readxx(fpf, fp0, fp2, fp3)

    fp0.close()
    fp1.close()
    fp2.close()
    fp3.close()
    fpf.close()

    os.remove(fname + exts[np[0]][0])
    os.remove(fname + exts[np[0]][1])
    os.remove(fname + exts[np[1]][0])
    os.remove(fname + exts[np[1]][1])

    print('recomb finished')

def handle_download(sock, user, nodes):
    fname = socketlib.recv_msg(sock, str)

    avail = []
    for x in range(4):
        if is_active(nodes[x]):
            avail.append(x)

    if len(avail) < 2:
        socketlib.send_msg(sock, 'n')
        return
    recomb(nodes, avail, fname)

    # get rid of the padding bytes
    fp = open(fname, 'rb')
    fp.seek(0, 2) # go to end
    fp.seek(-1, 1) # go back 1
    pad = int(str(fp.read(1), 'utf-8'))
    print('padded by {} bytes'.format(pad))

    fp.seek(0, 0)
    fp2 = open(fname + '2', 'wb')
    totl = os.stat(fname).st_size - pad
    done = 0
    while done < totl:
        fp2.write(fp.read(min(1024,totl-done)))
        done += min(1024, totl-done)
    fp.close()
    fp2.close()
    os.remove(fname)
    os.rename(fname + '2', fname)

    socketlib.send_msg(sock, 'y')
    socketlib.send_file(sock, fname)
    os.remove(fname)
    print('all done with download')

'''def handle_download(sock, user, nodes):
    fname = socketlib.recv_msg(sock, str)
    socketlib.send_msg(sock_user, 'download', LOGGED_IN, fname)
    if socketlib.recv_msg(sock_user, str) != 'y':
        socketlib.send_msg(sock, 'n')
        return

    jsn = {}
    jsn_wrong = json.loads(socketlib.recv_msg(sock_user, str))
    for c in jsn_wrong:
        jsn[int(c)] = jsn_wrong[c]
    jsn = sorted(jsn)

    print('json is {}'.format(jsn))
    # single-chunk
    if len(jsn) == 1:
        s0 = route_2(nodes, 0, 1)
        if s0 == None:
            socketlib.send_msg(sock, 'n')
            return
    # multi-chunk
    else:
        s0 = route_2(nodes, 0, 1)
        s1 = route_2(nodes, 2, 3)
        if s0 == None or s1 == None:
            socketlib.send_msg(sock, 'n')
            return

    socketlib.send_msg(sock, 'y')
    for chunk in jsn:
        if int(chunk) % 2 == 0:
            node_curr = s0
        else:
            node_curr = s1

        print('requesting chunk {} from node{}'.format(chunk, node_curr))
        socketlib.send_msg(nodes[node_curr], 'download', LOGGED_IN, fname, int(chunk))
        socketlib.send_msg(sock, 'download')
        socketlib.relay_file(nodes[node_curr], sock)
        print('finished chunk {}'.format(chunk))
    socketlib.send_msg(sock, 'end')'''

def handle(sock, sock_user, nodes):
    global LOGGED_IN
    msg_size = 1
    while msg_size != 0:
        msg, msg_size = socketlib.recv_msg_w_size(sock)
        if msg_size == 0:
            return
        try:
            cmd = str(msg, 'utf-8')
        except:
            print('Input not a string')
            return

        if LOGGED_IN == '' and cmd != 'login':
            return

        if cmd == 'user_add':
            handle_createaccount(sock, sock_user)
        elif cmd == 'login':
            handle_login(sock, sock_user)
        elif cmd == 'logout':
            LOGGED_IN = ''
            return
        elif cmd == 'list':
            handle_list(sock, sock_user)
        elif cmd == 'upload':
            handle_upload(sock, sock_user, nodes)
        elif cmd == 'delete':
            handle_delete(sock, sock_user, nodes)
        elif cmd == 'download':
            handle_download(sock, sock_user, nodes)

        else:
            print('Unexpected input')
            return

if __name__ == '__main__':
    sock_user = socket.socket()
    sock_user.connect((sys.argv[3], int(sys.argv[4])))

    # nodeserver host & port will be argv (5,6)...(11,12)
    nodes = []
    for x in range(4):
        s = socket.socket()
        s.connect((sys.argv[5+x*2],int(sys.argv[6+x*2])))
        nodes.append(s)
    
    serversoc = socket.socket()
    serversoc.bind((sys.argv[1], int(sys.argv[2])))
    serversoc.listen(5)
    while True:
        print('listening on {}'.format(sys.argv[2]))
        sock, raddr = serversoc.accept()
        print('accepted connection from {}'.format(raddr))
        handle(sock, sock_user, nodes)
        LOGGED_IN = ''
        sock.close()
    serversoc.close()

