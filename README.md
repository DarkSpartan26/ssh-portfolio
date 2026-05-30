# ssh-portfolio

A Python SSH server that drops visitors into an interactive TUI instead of a shell. No login needed — just SSH in.

```
ssh ssh.priyanshukapoor.me
```

## What it is

Built with [paramiko](https://www.paramiko.org/). When someone connects, they land in a terminal UI with three sections — About, Projects, and Contact — navigable with arrow keys or `h`/`l`. No authentication required.

## Run it yourself

**Requirements**

```
pip install paramiko
```

**Generate a host key**

```
ssh-keygen -t ed25519 -f host_key -N ""
```

**Start the server**

```
python server.py
```

Listens on port 22 by default. On a cloud server you'll need to run it as root or with `CAP_NET_BIND_SERVICE`, or change the port and use a redirect rule.

## Deployment

Deployed on a DigitalOcean droplet, managed via systemd, and live at `ssh.priyanshukapoor.me`.

## Stack

- Python
- paramiko
- DigitalOcean
- systemd

## License

MIT
