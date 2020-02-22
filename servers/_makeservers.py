import subprocess

if __name__ == '__main__':
    s0 = subprocess.Popen(['python', 'nodeserver.py','localhost','40000','node0/'])
    s1 = subprocess.Popen(['python', 'nodeserver.py','localhost','40001','node1/'])
    s2 = subprocess.Popen(['python', 'nodeserver.py','localhost','40002','node2/'])
    s3 = subprocess.Popen(['python', 'nodeserver.py','localhost','40003','node3/'])

    su = subprocess.Popen(['python', 'userdb.py', 'localhost', '50000'])
    ss = subprocess.Popen(['python', 'storageserver.py', 'localhost', '50001',
                           'localhost', '50000', 'localhost', '40000',
                           'localhost', '40001', 'localhost', '40002',
                           'localhost', '40003'])
