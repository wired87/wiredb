import socket

def get_local_ip():
    host_ip = socket.gethostbyname(socket.gethostname())
    return host_ip