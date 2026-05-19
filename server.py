#!/usr/bin/env python3
import socket
import threading
import paramiko
import sys
import os

HOST_KEY_PATH = os.path.join(os.path.dirname(__file__), 'host_key')

# ── ANSI ──────────────────────────────────────────────────────
R     = '\x1b[0m'
BOLD  = '\x1b[1m'
DIM   = '\x1b[2m'
CYAN  = '\x1b[96m'
BLUE  = '\x1b[94m'
GRAY  = '\x1b[90m'
WHITE = '\x1b[97m'

def cyan(s):  return f'{CYAN}{s}{R}'
def blue(s):  return f'{BLUE}{s}{R}'
def gray(s):  return f'{GRAY}{s}{R}'
def white(s): return f'{WHITE}{s}{R}'
def dim(s):   return f'{DIM}{s}{R}'
def bold(s):  return f'{BOLD}{s}{R}'

CLR  = '\x1b[2J\x1b[H'
HIDE = '\x1b[?25l'
SHOW = '\x1b[?25h'
RST  = '\x1bc'

# ── content ───────────────────────────────────────────────────
SECTIONS = ['Projects', 'Reflections', 'Contact']

CONTENT = {
    'Projects': [
        ('01', 'ssh-portfolio',  'this thing you are looking at'),
        ('02', 'your-project',   'replace with real project description'),
        ('03', 'another-thing',  'built it because nothing else did'),
    ],
    'Reflections': [
        ('2025-11', 'on learning in a language that is not yours'),
        ('2025-09', 'what makes a system feel alive'),
        ('2025-07', 'notes on starting over in a new city'),
    ],
    'Contact': [
        ('github', 'github.com/priyanshukapoor'),
        ('email',  'hi@priyanshukapoor.me'),
        ('web',    'priyanshukapoor.me'),
        ('ssh',    'ssh ssh.priyanshukapoor.me'),
    ],
}

# ── frame ─────────────────────────────────────────────────────
def strip_ansi(s):
    import re
    return re.sub(r'\x1b\[[0-9;]*m', '', s)

def center(s, w):
    vis = len(strip_ansi(s))
    lp = max(0, (w - vis) // 2)
    return ' ' * lp + s

def pad(s, n):
    vis = len(strip_ansi(s))
    return s + ' ' * max(0, n - vis)

def build_frame(selected, cols):
    W = max(60, min(cols, 110))
    rule = gray('─' * W)
    lines = []

    lines.append('')
    lines.append(center(cyan(bold('PRIYANSHU KAPOOR')), W))
    lines.append(center(gray('builder  ·  cs student  ·  curious about systems'), W))
    lines.append('')
    lines.append(rule)
    lines.append('')
    lines.append('  ' + white('studying Informatik, building things on the side,'))
    lines.append('  ' + dim('thinking about how technology shapes how we think.'))
    lines.append('  ' + dim('lorem ipsum dolor sit amet — replace this with your own words.'))
    lines.append('')
    lines.append(rule)
    lines.append('')

    # nav
    nav_parts = []
    for i, s in enumerate(SECTIONS):
        if i == selected:
            nav_parts.append(cyan('◆ ' + bold(s)))
        else:
            nav_parts.append(gray('  ' + s))
    lines.append('  ' + gray('   ·   ').join(nav_parts))
    lines.append('')

    # content
    section = SECTIONS[selected]
    items = CONTENT[section]

    if section == 'Projects':
        for key, name, desc in items:
            lines.append('  ' + gray(f'[{key}]') + '  ' + cyan(pad(name, 18)) + '  ' + dim(desc))
    elif section == 'Reflections':
        for key, name in items:
            lines.append('  ' + blue(pad(key, 10)) + '  ' + white(name))
    elif section == 'Contact':
        for key, name in items:
            lines.append('  ' + gray(pad(key, 8)) + '  ' + cyan(name))

    lines.append('')
    lines.append(rule)
    lines.append('')
    lines.append('  ' + dim('[') + gray(' ← → ') + dim('navigate') + gray('   ·   ') + dim('q ') + gray('quit') + dim(' ]'))
    lines.append('')

    return '\r\n'.join(lines)

# ── SSH server interface ───────────────────────────────────────
class PortfolioInterface(paramiko.ServerInterface):
    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_none(self, username):
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        return 'none,password,publickey'

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        self.cols = width or 100
        self.rows = height or 40
        return True

    def check_channel_shell_request(self, channel):
        return True

    def check_channel_window_change_request(self, channel, width, height, pixelwidth, pixelheight):
        self.cols = width
        self.rows = height
        return True

def handle_client(client_sock, addr):
    transport = None
    try:
        transport = paramiko.Transport(client_sock)
        host_key = paramiko.Ed25519Key(filename=HOST_KEY_PATH)
        transport.add_server_key(host_key)

        server = PortfolioInterface()
        server.cols = 100
        server.rows = 40
        transport.start_server(server=server)

        channel = transport.accept(20)
        if channel is None:
            return

        selected = 0
        cols = getattr(server, 'cols', 100)

        def send(s):
            try:
                channel.sendall(s.encode('utf-8'))
            except Exception:
                pass

        def draw():
            send(CLR + build_frame(selected, cols))

        send(HIDE + CLR + build_frame(selected, cols))

        # key loop
        while True:
            try:
                data = channel.recv(64)
            except Exception:
                break

            if not data:
                break

            key = data.decode('utf-8', errors='replace')

            # quit
            if key in ('q', 'Q', '\x03', '\x04'):
                send(SHOW + RST)
                channel.close()
                break

            prev = selected
            if key in ('\x1b[D', 'h'):   # left
                selected = (selected - 1) % len(SECTIONS)
            elif key in ('\x1b[C', 'l'): # right
                selected = (selected + 1) % len(SECTIONS)

            if selected != prev:
                draw()

    except Exception as e:
        print(f'[error] {addr}: {e}')
    finally:
        try:
            channel.close()
        except Exception:
            pass
        if transport:
            transport.close()
        client_sock.close()


def main():
    if not os.path.exists(HOST_KEY_PATH):
        print(f'[error] host key not found at {HOST_KEY_PATH}')
        print('generate one with: ssh-keygen -t ed25519 -f host_key -N ""')
        sys.exit(1)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind(("0.0.0.0", 22))
    sock.listen(10)
    print('[+] SSH portfolio listening on port 22')

    while True:
        try:
            client, addr = sock.accept()
            print(f'[+] connection from {addr}')
            t = threading.Thread(target=handle_client, args=(client, addr), daemon=True)
            t.start()
        except KeyboardInterrupt:
            print('\n[+] shutting down')
            break

    sock.close()

if __name__ == '__main__':
    main()
