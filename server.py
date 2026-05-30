#!/usr/bin/env python3
import socket
import threading
import paramiko
import sys
import os
import re

HOST_KEY_PATH = os.path.join(os.path.dirname(__file__), 'host_key')

# ── ANSI ──────────────────────────────────────────────────────
R      = '\x1b[0m'
BOLD   = '\x1b[1m'
DIM    = '\x1b[2m'
CYAN   = '\x1b[96m'
BLUE   = '\x1b[94m'
GRAY   = '\x1b[90m'
WHITE  = '\x1b[97m'
GREEN  = '\x1b[92m'
YELLOW = '\x1b[93m'

def cyan(s):   return f'{CYAN}{s}{R}'
def blue(s):   return f'{BLUE}{s}{R}'
def gray(s):   return f'{GRAY}{s}{R}'
def white(s):  return f'{WHITE}{s}{R}'
def dim(s):    return f'{DIM}{s}{R}'
def bold(s):   return f'{BOLD}{s}{R}'
def green(s):  return f'{GREEN}{s}{R}'
def yellow(s): return f'{YELLOW}{s}{R}'

CLR  = '\x1b[2J\x1b[H'
HIDE = '\x1b[?25l'
SHOW = '\x1b[?25h'
RST  = '\x1bc'

# ── content ───────────────────────────────────────────────────
SECTIONS     = ['About', 'Projects', 'Contact']
HEADER_LINES = 6  # blank + name + tagline + blank + rule + blank

ROCKET = [
    '          *          ',
    '         /|\\         ',
    '        / | \\        ',
    '       /  |  \\       ',
    '      /   |   \\      ',
    '     / [=====] \\     ',
    '    /   [===]   \\    ',
    '   /     [=]     \\   ',
    '  /       |       \\  ',
    ' /________|________\\ ',
    '          |          ',
    '         /|\\         ',
    '        / | \\        ',
    '       /  |  \\       ',
]

WHOAMI = [
    ('name',     'Priyanshu'),
    ('role',     'CS student'),
    ('focus',    'linux / infra / devops'),
    ('status',   'building quietly'),
    ('location', 'Germany'),
    ('uptime',   'still exploring...'),
    ('mood',     'somewhere between'),
    ('',         'terminals and mountains'),
]

PROJECTS = [
    {
        'name':   'Spartan Homelab',
        'status': 'ACTIVE',
        'desc':   'Remote self-hosted infra running in India, managed from Germany over Tailscale VPN. Nextcloud, Jellyfin, automated media stack, cross-continent Prometheus/Grafana monitoring.',
        'tags':   ['Debian', 'Docker', 'Tailscale', 'Grafana'],
        'github': 'github.com/DarkSpartan26',
    },
    {
        'name':   'SSH Portfolio',
        'status': 'LIVE',
        'desc':   'A Python SSH server that drops visitors into a TUI instead of a shell. No login needed — just SSH in.',
        'tags':   ['Python', 'paramiko', 'DigitalOcean', 'systemd'],
        'ssh':    'ssh ssh.priyanshukapoor.me',
        'github': 'github.com/DarkSpartan26',
    },
]

CONTACT = [
    ('github', 'github.com/DarkSpartan26'),
    ('email',  'hi@priyanshukapoor.me'),
    ('web',    'priyanshukapoor.me'),
    ('ssh',    'ssh ssh.priyanshukapoor.me'),
]

# ── helpers ───────────────────────────────────────────────────
def strip_ansi(s):
    return re.sub(r'\x1b\[[0-9;]*m', '', s)

def center(s, w):
    vis = len(strip_ansi(s))
    lp  = max(0, (w - vis) // 2)
    return ' ' * lp + s

def pad(s, n):
    vis = len(strip_ansi(s))
    return s + ' ' * max(0, n - vis)

def wrap_text(text, width):
    words = text.split()
    lines, current, cur_len = [], [], 0
    for word in words:
        need = len(word) + (1 if current else 0)
        if cur_len + need > width and current:
            lines.append(' '.join(current))
            current, cur_len = [word], len(word)
        else:
            if current:
                cur_len += 1
            current.append(word)
            cur_len += len(word)
    if current:
        lines.append(' '.join(current))
    return lines

# ── static header (drawn once) ────────────────────────────────
def build_header(W):
    rule  = gray('─' * W)
    parts = [
        '',
        center(cyan(bold('PRIYANSHU KAPOOR')), W),
        center(dim('CS student exploring systems, ideas, and the internet one rabbit hole at a time.'), W),
        '',
        rule,
        '',
    ]
    return '\r\n'.join(parts)

# ── nav — bottom right via absolute cursor position ───────────
def build_nav(selected, W, rows):
    parts = []
    for i, s in enumerate(SECTIONS):
        parts.append(cyan('◆ ' + bold(s)) if i == selected else gray('  ' + s))
    nav     = gray('   ·   ').join(parts)
    nav_vis = len(strip_ansi(nav))
    quit_h  = dim('[') + gray(' q ') + dim('quit') + dim(']')
    # last row: quit at left, nav flush right
    col = max(1, W - nav_vis)
    return (
        f'\x1b[{rows};1H'    + '  ' + quit_h +
        f'\x1b[{rows};{col}H' + nav
    )

# ── section renderers ─────────────────────────────────────────
def render_about(W):
    INDENT = '  '
    sep    = 6
    lcol   = (W - len(INDENT) - sep) // 2

    left  = [cyan(row) for row in ROCKET]
    right = ['', cyan('user@loki:~$ ') + white('whoami'), '']
    for key, val in WHOAMI:
        if key:
            right.append(cyan(pad(key, 10)) + '  ' + white(val))
        else:
            right.append(' ' * 12 + white(val))

    lines = []
    for i in range(max(len(left), len(right))):
        l = left[i]  if i < len(left)  else ''
        r = right[i] if i < len(right) else ''
        lines.append(INDENT + pad(l, lcol) + ' ' * sep + r)
    return lines

def render_projects(W):
    INDENT = '  '
    CW     = W - 4
    lines  = []
    for proj in PROJECTS:
        badge_col = green if proj['status'] == 'LIVE' else yellow
        badge     = badge_col(f"[{proj['status']}]")
        gap       = max(1, CW - len(proj['name']) - (len(proj['status']) + 2))
        lines.append(INDENT + white(bold(proj['name'])) + ' ' * gap + badge)
        lines.append('')
        for wline in wrap_text(proj['desc'], CW):
            lines.append(INDENT + dim(wline))
        lines.append('')
        lines.append(INDENT + '  '.join(gray(f'[{t}]') for t in proj['tags']))
        if 'ssh' in proj:
            lines.append(INDENT + dim('ssh  ') + cyan(proj['ssh']))
        lines.append(INDENT + dim('↗ ') + blue(proj['github']))
        lines.append('')
        lines.append(INDENT + gray('─' * CW))
        lines.append('')
    return lines

def render_contact(W):
    INDENT = '  '
    lines  = ['']
    for key, val in CONTACT:
        lines.append(INDENT + gray(pad(key, 8)) + '  ' + cyan(val))
    return lines

def get_section_lines(selected, W):
    if   selected == 0: return render_about(W)
    elif selected == 1: return render_projects(W)
    else:               return render_contact(W)

# ── draw functions ────────────────────────────────────────────
def full_draw(selected, cols, rows):
    W   = max(80, min(cols, 120))
    out = CLR + build_header(W) + '\r\n'
    for line in get_section_lines(selected, W):
        out += line + '\r\n'
    out += build_nav(selected, W, rows)
    return out

def partial_draw(selected, cols, rows):
    """Only redraws section content — header stays untouched."""
    W   = max(80, min(cols, 120))
    out = f'\x1b[{HEADER_LINES + 1};1H\x1b[J'  # jump after header, clear down
    for line in get_section_lines(selected, W):
        out += line + '\r\n'
    out += build_nav(selected, W, rows)
    return out

# ── SSH server ────────────────────────────────────────────────
class PortfolioInterface(paramiko.ServerInterface):
    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_none(self, u):        return paramiko.AUTH_SUCCESSFUL
    def check_auth_password(self, u, p): return paramiko.AUTH_SUCCESSFUL
    def check_auth_publickey(self, u, k):return paramiko.AUTH_SUCCESSFUL
    def get_allowed_auths(self, u):      return 'none,password,publickey'

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
        host_key  = paramiko.Ed25519Key(filename=HOST_KEY_PATH)
        transport.add_server_key(host_key)

        server = PortfolioInterface()
        server.cols = 100
        server.rows = 40
        transport.start_server(server=server)

        channel = transport.accept(20)
        if channel is None:
            return

        selected = 0

        def send(s):
            try:
                channel.sendall(s.encode('utf-8'))
            except Exception:
                pass

        def cols(): return getattr(server, 'cols', 100)
        def rows(): return getattr(server, 'rows', 40)

        send(HIDE + full_draw(selected, cols(), rows()))

        while True:
            try:
                data = channel.recv(64)
            except Exception:
                break
            if not data:
                break

            key = data.decode('utf-8', errors='replace')

            if key in ('q', 'Q', '\x03', '\x04'):
                send(SHOW + RST)
                channel.close()
                break

            prev = selected
            if key in ('\x1b[D', 'h'):
                selected = (selected - 1) % len(SECTIONS)
            elif key in ('\x1b[C', 'l'):
                selected = (selected + 1) % len(SECTIONS)

            if selected != prev:
                send(partial_draw(selected, cols(), rows()))

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

# version 1.4
