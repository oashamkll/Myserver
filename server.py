#!/usr/bin/env python3
import asyncio
import os
import pty
import json
import signal
import struct
import fcntl
import termios
from aiohttp import web
import aiohttp

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover"/>
<title>Termux</title>
<!-- xterm.js CDN -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css"/>
<script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
<script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body {
  width: 100%; height: 100%;
  background: #000;
  overflow: hidden;
  font-family: 'Courier New', monospace;
  -webkit-text-size-adjust: 100%;
}

/* ── TOP BAR ── */
.topbar {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 38px;
  background: #111;
  border-bottom: 1px solid #1e1e1e;
  display: flex;
  align-items: center;
  padding: 0 10px;
  gap: 8px;
  z-index: 100;
  user-select: none;
}
.tb-title {
  font-size: 14px;
  font-weight: bold;
  color: #55ff55;
  font-family: 'Courier New', monospace;
}
.tb-session {
  font-size: 11px;
  color: #555;
  font-family: monospace;
  padding: 1px 6px;
  border: 1px solid #222;
  border-radius: 3px;
}
.tb-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #55ff55;
  flex-shrink: 0;
  animation: pulse 2s infinite;
}
.tb-dot.off { background: #ff5555; animation: none; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.25} }
.tb-status { font-size: 11px; color: #444; font-family: monospace; }
.tb-space { flex: 1; }
.tb-btn {
  background: none; border: none;
  color: #555; font-size: 14px;
  padding: 4px 8px; cursor: pointer;
  border-radius: 3px; font-family: monospace;
  -webkit-tap-highlight-color: transparent;
}
.tb-btn:active { background: #1a1a1a; color: #aaa; }

/* ── TERMINAL AREA ── */
#terminal-container {
  position: fixed;
  top: 38px;
  left: 0; right: 0;
  bottom: 90px;
  background: #000;
  overflow: hidden;
}
#terminal-container .xterm {
  height: 100%;
  padding: 4px;
}
#terminal-container .xterm-viewport {
  overflow-y: auto !important;
}
#terminal-container .xterm-screen {
  cursor: text;
}

/* ── EXTRA KEYS BAR ── */
.extrakeys {
  position: fixed;
  bottom: 46px; left: 0; right: 0;
  height: 44px;
  background: #0d0d0d;
  border-top: 1px solid #1a1a1a;
  display: flex;
  overflow-x: auto;
  scrollbar-width: none;
  gap: 3px;
  padding: 5px 4px;
  z-index: 99;
  -webkit-overflow-scrolling: touch;
  align-items: center;
}
.extrakeys::-webkit-scrollbar { display: none; }
.ek {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  color: #ccc;
  padding: 3px 9px;
  border-radius: 3px;
  font-size: 12px;
  font-family: 'Courier New', monospace;
  white-space: nowrap;
  cursor: pointer;
  flex-shrink: 0;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
  min-width: 32px;
  text-align: center;
  line-height: 1.5;
}
.ek:active { background: #2a2a2a; color: #fff; }
.ek.ctrl  { color: #55ffff; border-color: #1e3333; }
.ek.spec  { color: #ffff55; border-color: #33331e; }
.ek.grn   { color: #55ff55; border-color: #1e331e; }

/* ── BOTTOM ACTION BAR ── */
.actionbar {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: 46px;
  background: #0d0d0d;
  border-top: 1px solid #1a1a1a;
  display: flex;
  gap: 3px;
  padding: 5px 4px;
  z-index: 100;
  align-items: center;
}
.ab-btn {
  flex: 1;
  background: #1a1a1a;
  border: 1px solid #222;
  color: #888;
  font-size: 11px;
  padding: 5px 2px;
  border-radius: 3px;
  cursor: pointer;
  font-family: monospace;
  text-align: center;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
}
.ab-btn:active { background: #252525; color: #ccc; }
.ab-btn.red { color: #ff5555; border-color: #331a1a; }

/* ── DISCONNECT OVERLAY ── */
.overlay {
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,.9); z-index: 300;
  align-items: center; justify-content: center;
}
.overlay.show { display: flex; }
.ov-card {
  background: #0d0d0d;
  border: 1px solid #2a2a2a;
  border-radius: 6px;
  padding: 28px 24px;
  text-align: center;
  font-family: 'Courier New', monospace;
  min-width: 240px;
}
.ov-card h3 { color: #ff5555; font-size: 14px; margin-bottom: 10px; }
.ov-card p  { color: #555; font-size: 12px; margin-bottom: 20px; line-height: 1.6; }
.ov-card button {
  background: #1a1a1a; border: 1px solid #55ff55;
  color: #55ff55; padding: 9px 0; width: 100%;
  border-radius: 4px; font-size: 13px;
  font-family: 'Courier New', monospace; cursor: pointer;
}
.ov-card button:active { background: #1e2e1e; }

/* xterm theme overrides */
.xterm-cursor-block { background: #55ff55 !important; }
</style>
</head>
<body>

<!-- TOP BAR -->
<div class="topbar">
  <span class="tb-title">Termux</span>
  <span class="tb-session">[1] bash</span>
  <div class="tb-dot" id="dot"></div>
  <span class="tb-status" id="stext">connecting...</span>
  <div class="tb-space"></div>
  <button class="tb-btn" onclick="sendCtrl('l')" title="Clear">✕</button>
  <button class="tb-btn" onclick="reconnect()" title="Reconnect">↺</button>
</div>

<!-- TERMINAL -->
<div id="terminal-container"></div>

<!-- EXTRA KEYS -->
<div class="extrakeys">
  <span class="ek ctrl" onclick="sendCtrl('c')">Ctrl+C</span>
  <span class="ek ctrl" onclick="sendCtrl('d')">Ctrl+D</span>
  <span class="ek ctrl" onclick="sendCtrl('z')">Ctrl+Z</span>
  <span class="ek spec" onclick="sendRaw('\t')">TAB</span>
  <span class="ek spec" onclick="sendRaw('\x1b[A')">▲</span>
  <span class="ek spec" onclick="sendRaw('\x1b[B')">▼</span>
  <span class="ek spec" onclick="sendRaw('\x1b[C')">▶</span>
  <span class="ek spec" onclick="sendRaw('\x1b[D')">◀</span>
  <span class="ek" onclick="sendRaw('| ')">|</span>
  <span class="ek" onclick="sendRaw('> ')">&gt;</span>
  <span class="ek" onclick="sendRaw('&& ')">&amp;&amp;</span>
  <span class="ek" onclick="sendRaw('/')"> / </span>
  <span class="ek" onclick="sendRaw('~')"> ~ </span>
  <span class="ek" onclick="sendRaw('-')"> - </span>
  <span class="ek" onclick="sendRaw('.')"> . </span>
  <span class="ek" onclick="sendRaw('\x01')">Home</span>
  <span class="ek" onclick="sendRaw('\x05')">End</span>
  <span class="ek" onclick="sendRaw('\x7f')">DEL</span>
  <span class="ek grn" onclick="sendLine('ls -la')">ls</span>
  <span class="ek grn" onclick="sendLine('pwd')">pwd</span>
  <span class="ek grn" onclick="sendLine('cd ~')">cd ~</span>
  <span class="ek grn" onclick="sendLine('cd ..')">cd ..</span>
  <span class="ek grn" onclick="sendLine('clear')">clear</span>
  <span class="ek grn" onclick="sendLine('whoami')">whoami</span>
  <span class="ek grn" onclick="sendLine('uname -a')">uname</span>
  <span class="ek grn" onclick="sendLine('df -h')">df</span>
  <span class="ek grn" onclick="sendLine('free -h')">free</span>
  <span class="ek grn" onclick="sendLine('ps aux')">ps</span>
  <span class="ek grn" onclick="sendLine('apt update')">apt update</span>
  <span class="ek" onclick="sendRaw('apt install -y ')">apt install</span>
  <span class="ek" onclick="sendRaw('python3 ')">python3</span>
  <span class="ek" onclick="sendRaw('pip install ')">pip</span>
  <span class="ek" onclick="sendRaw('nano ')">nano</span>
  <span class="ek" onclick="sendRaw('cat ')">cat</span>
  <span class="ek" onclick="sendRaw('chmod +x ')">chmod</span>
  <span class="ek" onclick="sendRaw('kill ')">kill</span>
</div>

<!-- ACTION BAR -->
<div class="actionbar">
  <button class="ab-btn" onclick="sendLine('ls -la')">FILES</button>
  <button class="ab-btn" onclick="sendLine('top -bn1 | head -30')">TOP</button>
  <button class="ab-btn" onclick="sendLine('df -h && free -h')">SYS</button>
  <button class="ab-btn" onclick="sendLine('ifconfig 2>/dev/null || ip a')">NET</button>
  <button class="ab-btn" onclick="sendLine('history | tail -20')">HIST</button>
  <button class="ab-btn red" onclick="sendCtrl('c')">KILL</button>
</div>

<!-- DISCONNECT OVERLAY -->
<div class="overlay" id="ov">
  <div class="ov-card">
    <h3>~ disconnected ~</h3>
    <p>Lost connection to server.<br/>Tap to reconnect.</p>
    <button onclick="reconnect(); closeOv()">↺ reconnect</button>
  </div>
</div>

<script>
let ws = null;
let term = null;
let fitAddon = null;
let alive = false;

const dot   = document.getElementById('dot');
const stxt  = document.getElementById('stext');

function setOk(m) { dot.className = 'tb-dot'; stxt.textContent = m; alive = true; }
function setOff(m) { dot.className = 'tb-dot off'; stxt.textContent = m; alive = false; }

// ── INIT XTERM ──
function initTerm() {
  if (term) { term.dispose(); term = null; }

  term = new Terminal({
    theme: {
      background:   '#000000',
      foreground:   '#ffffff',
      cursor:       '#55ff55',
      cursorAccent: '#000000',
      black:        '#000000',
      red:          '#ff5555',
      green:        '#55ff55',
      yellow:       '#ffff55',
      blue:         '#5555ff',
      magenta:      '#ff55ff',
      cyan:         '#55ffff',
      white:        '#ffffff',
      brightBlack:  '#555555',
      brightRed:    '#ff5555',
      brightGreen:  '#55ff55',
      brightYellow: '#ffff55',
      brightBlue:   '#5555ff',
      brightMagenta:'#ff55ff',
      brightCyan:   '#55ffff',
      brightWhite:  '#ffffff',
    },
    fontFamily: "'DejaVu Sans Mono', 'Courier New', monospace",
    fontSize: 13,
    lineHeight: 1.2,
    cursorBlink: true,
    cursorStyle: 'block',
    scrollback: 5000,
    allowTransparency: false,
    convertEol: false,
    disableStdin: false,
    allowProposedApi: true,
  });

  fitAddon = new FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  term.open(document.getElementById('terminal-container'));

  try { fitAddon.fit(); } catch(e) {}

  // Send keypresses to server
  term.onData(data => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'input', data: data }));
    }
  });

  // Handle resize
  term.onResize(({ cols, rows }) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'resize', cols, rows }));
    }
  });

  // Focus terminal
  term.focus();
}

// ── WEBSOCKET ──
function connect() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(proto + '//' + location.host + '/ws');

  ws.onopen = () => {
    setOk('root@ubuntu · connected');
    term.focus();
    // Send initial size
    try { fitAddon.fit(); } catch(e) {}
    setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
      }
      term.focus();
    }, 300);
  };

  ws.onmessage = e => {
    term.write(e.data);
  };

  ws.onclose = () => {
    setOff('disconnected');
    if (alive) {
      term.write('\r\n\x1b[31m[connection lost]\x1b[0m\r\n');
      document.getElementById('ov').classList.add('show');
    }
    alive = false;
  };

  ws.onerror = () => {
    setOff('error');
    term.write('\r\n\x1b[31m[websocket error]\x1b[0m\r\n');
  };
}

function reconnect() {
  try { ws && ws.close(); } catch(e) {}
  setOff('reconnecting...');
  setTimeout(() => { initTerm(); connect(); }, 500);
}
function closeOv() { document.getElementById('ov').classList.remove('show'); }

// ── HELPERS ──
function sendRaw(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'input', data: data }));
  }
  term.focus();
}
function sendLine(cmd) { sendRaw(cmd + '\n'); }
function sendCtrl(key) {
  const map = {
    'c': '\x03', 'd': '\x04', 'z': '\x1a',
    'l': '\x0c', 'a': '\x01', 'e': '\x05',
    'u': '\x15', 'k': '\x0b'
  };
  sendRaw(map[key] || key);
}

// ── RESIZE HANDLER ──
function doResize() {
  try {
    fitAddon.fit();
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
    }
  } catch(e) {}
}

window.addEventListener('resize', doResize);
if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', () => {
    const kb = window.innerHeight - window.visualViewport.height;
    const tc = document.getElementById('terminal-container');
    const ek = document.querySelector('.extrakeys');
    const ab = document.querySelector('.actionbar');
    if (kb > 80) {
      ab.style.bottom = kb + 'px';
      ek.style.bottom = (kb + 46) + 'px';
      tc.style.bottom = (kb + 90) + 'px';
    } else {
      ab.style.bottom = '';
      ek.style.bottom = '';
      tc.style.bottom = '';
    }
    setTimeout(doResize, 100);
  });
}

// ── START ──
initTerm();
connect();
</script>
</body>
</html>
"""

async def handle_index(request):
    return web.Response(text=HTML, content_type='text/html', headers={
        'ngrok-skip-browser-warning': 'true',
        'Cache-Control': 'no-cache'
    })

async def handle_upload(request):
    try:
        reader = await request.multipart()
        field = await reader.next()
        filename = os.path.basename(field.filename)
        upload_dir = '/root/uploads'
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, 'wb') as f:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                f.write(chunk)
        return web.json_response({'ok': True, 'path': filepath})
    except Exception as e:
        return web.json_response({'ok': False, 'error': str(e)})

async def handle_ws(request):
    ws_resp = web.WebSocketResponse(max_msg_size=10 * 1024 * 1024)
    await ws_resp.prepare(request)

    while True:
        # Fork a PTY for bash
        pid, fd = pty.fork()

        if pid == 0:
            # ── CHILD: exec bash ──
            env = {
                'TERM':             'xterm-256color',
                'COLORTERM':        'truecolor',
                'SHELL':            '/bin/bash',
                'HOME':             '/root',
                'USER':             'root',
                'LOGNAME':          'root',
                'PATH':             '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin',
                'LANG':             'en_US.UTF-8',
                'LC_ALL':           'en_US.UTF-8',
                'DEBIAN_FRONTEND':  'noninteractive',
                'PS1':              r'\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ ',
            }
            try:
                os.chdir('/root')
            except Exception:
                pass
            os.execvpe('/bin/bash', ['/bin/bash', '--login'], env)
            os._exit(1)

        else:
            # ── PARENT: relay data ──
            loop = asyncio.get_event_loop()

            # default window size
            fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))

            shell_done = asyncio.Event()

            async def pty_to_ws():
                while True:
                    try:
                        data = await loop.run_in_executor(None, lambda: os.read(fd, 4096))
                        if not data:
                            break
                        if ws_resp.closed:
                            break
                        await ws_resp.send_str(data.decode('utf-8', errors='replace'))
                    except OSError:
                        break
                shell_done.set()

            async def ws_to_pty():
                async for msg in ws_resp:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            pkt = json.loads(msg.data)
                            t = pkt.get('type', '')
                            if t == 'input':
                                raw = pkt['data'].encode('utf-8')
                                os.write(fd, raw)
                            elif t == 'resize':
                                cols = max(10, int(pkt.get('cols', 80)))
                                rows = max(2,  int(pkt.get('rows', 24)))
                                fcntl.ioctl(fd, termios.TIOCSWINSZ,
                                            struct.pack('HHHH', rows, cols, 0, 0))
                        except Exception:
                            pass
                    elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                        break
                shell_done.set()

            t1 = asyncio.ensure_future(pty_to_ws())
            t2 = asyncio.ensure_future(ws_to_pty())

            await shell_done.wait()

            t1.cancel(); t2.cancel()
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass
            try:
                os.waitpid(pid, 0)
            except Exception:
                pass
            try:
                os.close(fd)
            except Exception:
                pass

            if ws_resp.closed:
                break

            # Shell died — restart it
            await ws_resp.send_str('\r\n\x1b[33m[shell restarted]\x1b[0m\r\n')
            await asyncio.sleep(0.3)

    return ws_resp


def main():
    app = web.Application(client_max_size=500 * 1024 * 1024)
    app.router.add_get('/',        handle_index)
    app.router.add_get('/ws',      handle_ws)
    app.router.add_post('/upload', handle_upload)
    port = int(os.environ.get('PORT', 8080))
    print(f'[*] Termux WebShell on :{port}')
    web.run_app(app, host='0.0.0.0', port=port, access_log=None)

if __name__ == '__main__':
    main()
