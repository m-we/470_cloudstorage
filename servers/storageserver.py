import json
import os
import socket
import sys

import socketlib

LOGGED_IN = ''

# Return True if a socket is available.
def is_active(sock):
    try:
        socketlib.send_msg(sock, 'test')
        return True
    except:
        return False

# Pass on user and hashed to userdb. Send the result to the client.
def handle_createaccount(sock, sock_user):
    user = socketlib.recv_msg(sock)
    hashed = socketlib.recv_msg(sock)
    socketlib.send_msg(sock_user, 'createaccount', user, hashed)
    if socketlib.recv_msg(sock_user, int) == 0:
        socketlib.send_msg(sock, 'y')
    else:
        socketlib.send_msg(sock, 'n')

# Check that the hash sent is correct. If yes, set LOGGED_IN and allow further
# commands. If the login fails, close the connection.
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

# Send the list command to userdb and forward the result to client.
def handle_list(sock, sock_user):
    socketlib.send_msg(sock_user, 'list', LOGGED_IN)
    socketlib.send_msg(sock, socketlib.recv_msg(sock_user))

# Get the list of chunks for the given filename. Send delete commands to
# every node with a chunk. Send the delete command to userdb.
def handle_delete(sock, sock_user, nodes):
    avail = []
    for x in range(4):
        if is_active(nodes[x]):
            avail.append(x)
    if len(avail) == 4:
        socketlib.send_msg(sock, 'y')
    else:
        socketlib.send_msg(sock, 'n')
        return
    
    fname = socketlib.recv_msg(sock, str)
    socketlib.send_msg(sock_user, 'delete', LOGGED_IN, fname)
    jsn = json.loads(socketlib.recv_msg(sock_user, str))

    for chunk in jsn:
        for node in jsn[chunk]:
            node_s = nodes[node]
            print('sending del req for chunk {} to node{}'.format(node, chunk))
            socketlib.send_msg(node_s, 'delete', LOGGED_IN, fname, chunk)

# XOR two byte strings.
def xor(b1, b2):
    return bytes([a^b for a, b in zip(b1, b2)])

# Used by handle_upload(). Tells userdb to add a chunk to users.json. Then
# uploads the chunk to the given node. The fname is the base name of the file,
# e.g. 'cat.jpg', and f_ext is the chunk name, for example, '.A1'.
def send_node(sock_user, nodes, fname, node_no, f_ext):
    socketlib.send_msg(sock_user, 'upload', LOGGED_IN, fname, f_ext, node_no)
    socketlib.send_msg(nodes[node_no], 'upload', LOGGED_IN)
    socketlib.send_file(nodes[node_no], fname + f_ext)
    os.remove(fname + f_ext)

# Receives the file and splits into .A1, .A2, .B1, and .B2.
# Then, creates the XOR chunks (.A1_XOR_B1, .A2_XOR_B2, etc...).
# Then, uploads each chunk to the relevant nodeserver.
def handle_upload(sock, sock_user, nodes):
    avail = []
    for x in range(4):
        if is_active(nodes[x]):
            avail.append(x)
    if len(avail) == 4:
        socketlib.send_msg(sock, 'y')
    else:
        socketlib.send_msg(sock, 'n')
        return

    
    # The client sends the basename anyways, but get the basename again just
    # to make sure.
    fname = os.path.basename(socketlib.recv_msg(sock, str))
    ftotl = socketlib.recv_msg(sock, int)
    print('Total is: {} bytes'.format(ftotl))
    frecv = 0

    # Receives each quarter of the file into the relevant chunk.
    # (x+1)*ftotl/4 means:
    # exts[0], .A1, will read until ftotl/4
    # exts[1], .A2, will read until ftotl/2
    exts = ['.A1','.A2','.B1','.B2']
    for x in range(4):
        with open(fname + exts[x], 'wb') as fp:
            while frecv < (x+1)*ftotl/4:
                # Read in 1024-byte chunks, or however much is left, whichever
                # is smaller.
                data = socketlib.recv_b(sock, min(int((x+1)*ftotl/4)-frecv,1024))
                frecv += len(data)
                fp.write(data)
    print('file received')

    # Open each chunk for reading and each XOR chunk for writing.
    A1 = open(fname + '.A1', 'rb')
    A2 = open(fname + '.A2', 'rb')
    B1 = open(fname + '.B1', 'rb')
    B2 = open(fname + '.B2', 'rb')
    A1_XOR_B1 = open(fname + '.A1_XOR_B1', 'wb')
    A2_XOR_B2 = open(fname + '.A2_XOR_B2', 'wb')
    A2_XOR_B1 = open(fname + '.A2_XOR_B1', 'wb')
    A1_XOR_A2_XOR_B2 = open(fname + '.A1_XOR_A2_XOR_B2', 'wb')

    # Write all 4 at the same time since they're all the same size.
    fdone = 0
    ftotl = int(ftotl / 4)
    while fdone < ftotl:
        b_a1 = A1.read(min(1024,ftotl-fdone))
        b_a2 = A2.read(min(1024,ftotl-fdone))
        b_b1 = B1.read(min(1024,ftotl-fdone))
        b_b2 = B2.read(min(1024,ftotl-fdone))

        A1_XOR_B1.write(xor(b_a1, b_b1))
        A2_XOR_B2.write(xor(b_a2, b_b2))
        A2_XOR_B1.write(xor(b_a2, b_b1))
        A1_XOR_A2_XOR_B2.write(xor(xor(b_a1, b_a2), b_b2))
        fdone += min(1024,ftotl-fdone)

    A1.close()
    A2.close()
    B1.close()
    B2.close()
    A1_XOR_B1.close()
    A2_XOR_B2.close()
    A2_XOR_B1.close()
    A1_XOR_A2_XOR_B2.close()

    # Send each chunk to the correct node. send_node() will delete the chunk
    # from the middleware server afterwards.
    send_node(sock_user, nodes, fname, 0, '.A1')
    send_node(sock_user, nodes, fname, 0, '.A2')
    send_node(sock_user, nodes, fname, 1, '.B1')
    send_node(sock_user, nodes, fname, 1, '.B2')
    send_node(sock_user, nodes, fname, 2, '.A1_XOR_B1')
    send_node(sock_user, nodes, fname, 2, '.A2_XOR_B2')
    send_node(sock_user, nodes, fname, 3, '.A2_XOR_B1')
    send_node(sock_user, nodes, fname, 3, '.A1_XOR_A2_XOR_B2')

# Stores where each chunk is located.
exts = {0:['.A1','.A2'],1:['.B1','.B2'],2:['.A1_XOR_B1','.A2_XOR_B2'],
        3:['.A2_XOR_B1','.A1_XOR_A2_XOR_B2']}

# Read from a file pointer into a destination fp.
def read(fpf, fp):
    while (x := fp.read(1024)) != b'':
        fpf.write(x)
    fp.seek(0)

# Read from two file pointers, XOR the data, and write into a dest fp.
def readx(fpf, fp0, fp1):
    while (x := fp0.read(1024)) != b'':
        fpf.write(xor(x, fp1.read(1024)))
    fp0.seek(0)
    fp1.seek(0)

# Read from 3 file pointers, XOR all 3, and write the data into a dest fp.
def readxx(fpf, fp0, fp1, fp2):
    while (x := fp0.read(1024)) != b'':
        fpf.write(xor(xor(x, fp1.read(1024)), fp2.read(1024)))
    fp0.seek(0)
    fp1.seek(0)
    fp2.seek(0)

# Read from 4 file pointers, XOR all 4, and write the data into a dest fp.
def read3(fpf, fp0, fp1, fp2, fp3):
    while (x := fp0.read(1024)) != b'':
        fpf.write(xor(xor(xor(fp2.read(1024), x), fp3.read(1024)), fp1.read(1024)))
    fp0.seek(0, 0)
    fp1.seek(0, 0)
    fp2.seek(0, 0)
    fp3.seek(0, 0)

# Used by handle_download(). Given a list of nodes, a list of which are online,
# and a filename, grabs the required chunks and combines them to reconstruct
# the file.
def recomb(nodes, avail, fname):
    # Pick the 2 nodes which will be used to recombine. Prioritizes them from
    # 0 to 3. Gets the 2 chunks each node has.
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
    print('nodes picked {} and {}'.format(np[0], np[1]))

    # Open all 4 chunks to recombine into the final file.
    print('fp0: {}'.format(fname + exts[np[0]][0]))
    print('fp1: {}'.format(fname + exts[np[0]][1]))
    print('fp2: {}'.format(fname + exts[np[1]][0]))
    print('fp3: {}'.format(fname + exts[np[1]][1]))
    fp0 = open(fname + exts[np[0]][0], 'rb')
    fp1 = open(fname + exts[np[0]][1], 'rb')
    fp2 = open(fname + exts[np[1]][0], 'rb')
    fp3 = open(fname + exts[np[1]][1], 'rb')
    # Destination fp.
    fpf = open(fname, 'wb')

    # Calls read(), readx(), readxx(), and read3() based on which nodes were
    # picked. Each of these functions will write into fpf. Once all 4 have been
    # called, the file is completely reassembled.

    # A1 A2 <-> B1 B2
    # The simplest, just read from the chunks into the final.
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
        read(fpf, fp0)
        read(fpf, fp1)

    # B1 B2 <-> A2_XOR_B1 A1_XOR_A2_XOR_B2
    elif 1 in np and 3 in np:
        read3(fpf, fp0, fp1, fp2, fp3)
        readx(fpf, fp2, fp0)
        read(fpf, fp0)
        read(fpf, fp1)

    # A1B1 A2B2 <-> A2B1 A1A2B2

    # A2B2 (+) A1A2B2 = A1

    # A2B2 (+) A1B1 = A1A2B1B2
    # A1A2B1B2 (+) A1A2B2 = B1
    # A2B1 (+) B1 = A2

    # A2B2 (+) A1B1 = A1A2B1B2
    # A1A2B1B2 (+) A1A2B2 = B1

    # A1A2B2 (+) A1B1 = A2B1B2
    # A2B1 (+) A2B1B2 = B2

    # This is the most complicated recombination. Read and XOR according to
    # the equations above to get each chunk.
    elif 2 in np and 3 in np:
        readx(fpf, fp1, fp3)
        read3(fpf, fp0, fp3, fp1, fp2)
        readxx(fpf, fp0, fp1, fp3)
        readxx(fpf, fp0, fp2, fp3)

    # Close every fp and delete the chunks.
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

# Determines which nodeservers are active. Calls recomb() to get the chunks
# and combine into the complete file. Removes the padded bytes and sends to
# the client.
def handle_download(sock, user, nodes):
    fname = socketlib.recv_msg(sock, str)

    avail = []
    for x in range(4):
        if is_active(nodes[x]):
            avail.append(x)

    # Download is only possible if at least 2 nodes are available.
    if len(avail) < 2:
        socketlib.send_msg(sock, 'n')
        return
    recomb(nodes, avail, fname)

    # Remove the padding bytes. Get the final byte to determine how many
    # bytes were added.
    fp = open(fname, 'rb')
    fp.seek(0, 2) # go to end
    fp.seek(-1, 1) # go back 1
    pad = int(str(fp.read(1), 'utf-8'))
    print('padded by {} bytes'.format(pad))

    # Write every byte in the file into a new fp until the bytes done is equal
    # to the total size minus the number of padded bytes.
    fp.seek(0, 0)
    fp2 = open(fname + '2', 'wb')
    totl = os.stat(fname).st_size - pad
    done = 0
    while done < totl:
        fp2.write(fp.read(min(1024,totl-done)))
        done += min(1024, totl-done)
    fp.close()
    fp2.close()

    # Replace the file with the non-padded version and send to the client.
    os.remove(fname)
    os.rename(fname + '2', fname)

    socketlib.send_msg(sock, 'y')
    socketlib.send_file(sock, fname)
    os.remove(fname)
    print('all done with download')

# Handle commands from the client.
def handle(sock, sock_user, nodes):
    global LOGGED_IN
    msg_size = 1
    # msg_size = 0 means connection has been closed.
    while msg_size != 0:
        msg, msg_size = socketlib.recv_msg_w_size(sock)
        if msg_size == 0:
            return

        # If the client has an error or has been modified, it may send bytes
        # that can't be turned into a string (e.g. image file data). If this
        # happens, disregard what it sent to avoid crashing the server.
        try:
            cmd = str(msg, 'utf-8')
        except:
            print('Input not a string')
            return

        # Don't allow any commands from the client unless they have logged in.
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

    # argv[1] is middleware host, argv[2] is port
    # argv[3] and argv[4] are userdb host and port
    # argv[5] and argv[6] are nodeserver 0 host and port
    # ...argv[11] and argv[12] are nodeserver 3 host and port
    nodes = []
    for x in range(4):
        s = socket.socket()
        try:
            s.connect((sys.argv[5+x*2],int(sys.argv[6+x*2])))
        except:
            pass
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

