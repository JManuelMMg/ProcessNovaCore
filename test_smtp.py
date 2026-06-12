import socket

hosts = [
    ('smtp.gmail.com', 465),
    ('smtp.gmail.com', 587),
]

for host, port in hosts:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect((host, port))
        print(f'{host}:{port} -> ABIERTO')
        s.close()
    except socket.timeout:
        print(f'{host}:{port} -> TIMEOUT (bloqueado)')
    except Exception as e:
        print(f'{host}:{port} -> ERROR: {e}')
    finally:
        s.close()

print('Test completado.')
