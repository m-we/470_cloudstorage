import os
import socket

# Each message is sent with 4 bytes preceding containing the message size.
# Messages in str or int format are converted before sending.
def send_msg(sock, *msgs):
    for msg in msgs:
        if type(msg) == str:
            msg = bytes(msg, 'utf-8')
        elif type(msg) == int:
            msg = msg.to_bytes(4, 'big')

        sock.sendall(len(msg).to_bytes(4, 'big'))
        sock.sendall(msg)

# Added to ensure that recv_msg() and recv_msg_w_size() actually get the correct
# amount of data. Receives "num" bytes of data.
def recv_b(sock, num):
    data = b''
    while len(data) < num:
        data += sock.recv(num-len(data))
    return data

# Gets 4 bytes to determine the size of the following message, and then gets the
# message. "typ" can optionally be specified to convert to str or int. Both
# message and the message size are returned.
def recv_msg_w_size(sock, typ=bytes):
    try:
        msg_size = int.from_bytes(recv_b(sock, 4), 'big')
    except:
        return b'', 0

    msg = recv_b(sock, msg_size)
    if typ == int:
        return int.from_bytes(msg, 'big'), msg_size
    elif typ == str:
        return str(msg, 'utf-8'), msg_size
    else:
        return msg, msg_size

# Calls recv_msg_w_size() and discards the size.
def recv_msg(sock, typ=bytes):
    msg, msg_size = recv_msg_w_size(sock, typ)
    return msg

# Sends a file by transmitting: filename, filesize, and then filedata.
def send_file(sock, fname):
    fsize = os.stat(fname).st_size
    fsent = 0
    send_msg(sock, fname, fsize)
    with open(fname, 'rb') as fp:
        while fsent < fsize:
            msg_size = min(1024, fsize - fsent)
            msg = fp.read(msg_size)
            send_msg(sock, msg)
            fsent += msg_size

# Gets the filename and filesize. It then reads from the socket until the data
# received matches the filesize. Writes into a file pointer (fp) and returns
# the filename. This is done so that the receiving end is not locked into
# writing to a specific filename, but can choose to rename if it wishes.
def recv_file(sock, fp):
    fname = recv_msg(sock, str)
    fsize = recv_msg(sock, int)

    frecv = 0
    while frecv < fsize:
        msg, msg_size = recv_msg_w_size(sock)
        fp.write(msg)
        frecv += msg_size
    return fname
