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

# ── Hack font (Termux uses Hack / DejaVu Sans Mono) embedded as base64 woff2
# We load it from jsDelivr which serves it reliably
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover"/>
<title>Termux</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css"/>
<script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
<script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
<script src="https://cdn.jsdelivr.net/npm/xterm-addon-web-links@0.9.0/lib/xterm-addon-web-links.js"></script>
<!-- Hack font — same as Termux default -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/hack-font@3.3.0/build/web/hack.css"/>
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
  width: 100%; height: 100%;
  background: #000;
  overflow: hidden;
  -webkit-text-size-adjust: 100%;
  touch-action: manipulation;
}

/* ── TOP BAR ── */
.topbar {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 36px;
  background: #000;
  border-bottom: 1px solid #111;
  display: flex;
  align-items: center;
  padding: 0 8px;
  gap: 6px;
  z-index: 100;
  user-select: none;
  -webkit-user-select: none;
}
.tb-logo {
  font-size: 13px;
  font-weight: bold;
  color: #50fa7b;
  font-family: 'Hack', 'DejaVu Sans Mono', monospace;
  letter-spacing: 0.3px;
}
.tb-badge {
  font-size: 10px;
  color: #555;
  font-family: 'Hack', monospace;
  background: #111;
  border: 1px solid #1e1e1e;
  padding: 1px 5px;
  border-radius: 3px;
}
.tb-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #50fa7b;
  flex-shrink: 0;
  animation: blink 2s infinite;
}
.tb-dot.off { background: #ff5555; animation: none; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.15} }
.tb-st { font-size: 10px; color: #333; font-family: 'Hack', monospace; }
.tb-sp { flex: 1; }
.tb-btn {
  background: none; border: none;
  color: #333; font-size: 15px;
  padding: 3px 7px; cursor: pointer;
  border-radius: 3px;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
  line-height: 1;
}
.tb-btn:active { background: #111; color: #888; }

/* ── TERMINAL ── */
#term-wrap {
  position: fixed;
  top: 36px; bottom: 88px;
  left: 0; right: 0;
  background: #000;
  overflow: hidden;
}
#term-wrap .xterm {
  width: 100%; height: 100%;
  padding: 2px 3px;
}
#term-wrap .xterm-viewport { overflow-y: hidden !important; }
#term-wrap .xterm-screen { cursor: text; }

/* ── EXTRA KEYS ── */
.xkeys {
  position: fixed;
  bottom: 44px; left: 0; right: 0;
  height: 44px;
  background: #000;
  border-top: 1px solid #111;
  display: flex;
  overflow-x: auto;
  scrollbar-width: none;
  gap: 3px;
  padding: 5px 4px;
  z-index: 99;
  -webkit-overflow-scrolling: touch;
  align-items: center;
}
.xkeys::-webkit-scrollbar { display: none; }
.xk {
  background: #0d0d0d;
  border: 1px solid #1e1e1e;
  color: #bbb;
  padding: 4px 9px;
  border-radius: 3px;
  font-size: 12px;
  font-family: 'Hack', 'DejaVu Sans Mono', monospace;
  white-space: nowrap;
  cursor: pointer;
  flex-shrink: 0;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
  min-width: 32px;
  text-align: center;
  user-select: none;
  -webkit-user-select: none;
}
.xk:active { background: #1a1a1a; color: #fff; }
.xk.c  { color: #8be9fd; border-color: #1a2a2a; }  /* ctrl - cyan */
.xk.y  { color: #f1fa8c; border-color: #2a2a1a; }  /* special - yellow */
.xk.g  { color: #50fa7b; border-color: #1a2a1a; }  /* commands - green */
.xk.r  { color: #ff5555; border-color: #2a1a1a; }  /* kill - red */

/* ── ACTION BAR ── */
.abar {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: 44px;
  background: #000;
  border-top: 1px solid #111;
  display: flex;
  gap: 2px;
  padding: 5px 4px;
  z-index: 100;
  align-items: center;
}
.ab {
  flex: 1;
  background: #0d0d0d;
  border: 1px solid #1a1a1a;
  color: #555;
  font-size: 10px;
  padding: 5px 1px;
  border-radius: 3px;
  cursor: pointer;
  font-family: 'Hack', monospace;
  text-align: center;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
  user-select: none;
  -webkit-user-select: none;
  letter-spacing: 0;
}
.ab:active { background: #1a1a1a; color: #ccc; }
.ab.r { color: #ff5555; border-color: #2a1111; }

/* ── OVERLAY ── */
.ov {
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,.92); z-index: 300;
  align-items: center; justify-content: center;
}
.ov.show { display: flex; }
.ov-box {
  background: #0d0d0d; border: 1px solid #222;
  border-radius: 6px; padding: 28px 22px;
  text-align: center; font-family: 'Hack', monospace;
  min-width: 230px;
}
.ov-box h3 { color: #ff5555; font-size: 13px; margin-bottom: 8px; }
.ov-box p  { color: #444; font-size: 11px; margin-bottom: 18px; line-height: 1.7; }
.ov-box button {
  background: #0d0d0d; border: 1px solid #50fa7b;
  color: #50fa7b; padding: 8px 0; width: 100%;
  border-radius: 4px; font-size: 12px;
  font-family: 'Hack', monospace; cursor: pointer;
}
.ov-box button:active { background: #111; }
</style>
</head>
<body>

<!-- TOP BAR -->
<div class="topbar">
  <span class="tb-logo">Termux</span>
  <span class="tb-badge">[1] bash</span>
  <div class="tb-dot" id="dot"></div>
  <span class="tb-st" id="stext">connecting…</span>
  <div class="tb-sp"></div>
  <button class="tb-btn" onclick="sk('l')" title="Clear">✕</button>
  <button class="tb-btn" onclick="reconnect()" title="Reconnect">↺</button>
</div>

<!-- TERMINAL -->
<div id="term-wrap"></div>

<!-- EXTRA KEYS -->
<div class="xkeys">
  <span class="xk c" onclick="sk('c')">Ctrl+C</span>
  <span class="xk c" onclick="sk('d')">Ctrl+D</span>
  <span class="xk c" onclick="sk('z')">Ctrl+Z</span>
  <span class="xk y" onclick="sr('\t')">TAB</span>
  <span class="xk y" onclick="sr('\x1b[A')">▲</span>
  <span class="xk y" onclick="sr('\x1b[B')">▼</span>
  <span class="xk y" onclick="sr('\x1b[C')">▶</span>
  <span class="xk y" onclick="sr('\x1b[D')">◀</span>
  <span class="xk y" onclick="sr('\x1b[3~')">DEL</span>
  <span class="xk y" onclick="sr('\x01')">HOME</span>
  <span class="xk y" onclick="sr('\x05')">END</span>
  <span class="xk"   onclick="sr('| ')">|</span>
  <span class="xk"   onclick="sr('> ')">&gt;</span>
  <span class="xk"   onclick="sr('&& ')">&amp;&amp;</span>
  <span class="xk"   onclick="sr(' ')">SPC</span>
  <span class="xk"   onclick="sr('/')"> / </span>
  <span class="xk"   onclick="sr('~')"> ~ </span>
  <span class="xk"   onclick="sr('-')"> - </span>
  <span class="xk"   onclick="sr('.')"> . </span>
  <span class="xk g" onclick="sl('ls -la')">ls</span>
  <span class="xk g" onclick="sl('pwd')">pwd</span>
  <span class="xk g" onclick="sl('cd ~')">cd ~</span>
  <span class="xk g" onclick="sl('cd ..')">cd ..</span>
  <span class="xk g" onclick="sl('clear')">clear</span>
  <span class="xk g" onclick="sl('whoami')">whoami</span>
  <span class="xk g" onclick="sl('uname -a')">uname</span>
  <span class="xk g" onclick="sl('df -h')">df</span>
  <span class="xk g" onclick="sl('free -h')">free</span>
  <span class="xk g" onclick="sl('ps aux')">ps</span>
  <span class="xk g" onclick="sl('apt update')">apt update</span>
  <span class="xk"   onclick="sr('apt install -y ')">apt install</span>
  <span class="xk"   onclick="sr('python3 ')">python3</span>
  <span class="xk"   onclick="sr('pip install ')">pip</span>
  <span class="xk"   onclick="sr('nano ')">nano</span>
  <span class="xk"   onclick="sr('vim ')">vim</span>
  <span class="xk"   onclick="sr('cat ')">cat</span>
  <span class="xk"   onclick="sr('chmod +x ')">chmod</span>
  <span class="xk"   onclick="sr('kill ')">kill</span>
  <span class="xk"   onclick="sr('screen -r ')">screen</span>
</div>

<!-- ACTION BAR -->
<div class="abar">
  <button class="ab" onclick="sl('ls -la')">FILES</button>
  <button class="ab" onclick="sl('ps aux --no-header | grep -v grep | head -20')">PROCS</button>
  <button class="ab" onclick="sl('df -h && echo --- && free -h')">SYS</button>
  <button class="ab" onclick="sl('cat /tmp/.autorun_list 2>/dev/null || echo no autorun')">AUTO</button>
  <button class="ab" onclick="sl('ip a 2>/dev/null || ifconfig')">NET</button>
  <button class="ab r" onclick="sk('c')">KILL</button>
</div>

<!-- OVERLAY -->
<div class="ov" id="ov">
  <div class="ov-box">
    <h3>~ disconnected ~</h3>
    <p>Connection lost.<br/>Server may be restarting…<br/>Tap to reconnect.</p>
    <button onclick="reconnect(); closeOv()">↺ reconnect</button>
  </div>
</div>

<script>
'use strict';
let ws = null, term = null, fit = null, alive = false;
const dot  = document.getElementById('dot');
const stxt = document.getElementById('stext');

function setOk(m) { dot.className='tb-dot'; stxt.textContent=m; alive=true; }
function setOff(m){ dot.className='tb-dot off'; stxt.textContent=m; alive=false; }

// ── INIT XTERM ──────────────────────────────────────────────
function initTerm() {
  if (term) { try { term.dispose(); } catch(e){} term=null; }

  term = new Terminal({
    theme: {
      background:    '#000000',
      foreground:    '#f8f8f2',
      cursor:        '#50fa7b',
      cursorAccent:  '#000000',
      selectionBackground: '#44475a',
      black:         '#000000',
      red:           '#ff5555',
      green:         '#50fa7b',
      yellow:        '#f1fa8c',
      blue:          '#6272a4',
      magenta:       '#ff79c6',
      cyan:          '#8be9fd',
      white:         '#bfbfbf',
      brightBlack:   '#4d4d4d',
      brightRed:     '#ff6e6e',
      brightGreen:   '#69ff94',
      brightYellow:  '#ffffa5',
      brightBlue:    '#d6acff',
      brightMagenta: '#ff92df',
      brightCyan:    '#a4ffff',
      brightWhite:   '#ffffff',
    },
    // Hack — the exact font Termux ships
    fontFamily: "'Hack', 'DejaVu Sans Mono', 'Courier New', monospace",
    fontSize: 13,
    lineHeight: 1.18,
    letterSpacing: 0,
    cursorBlink: true,
    cursorStyle: 'block',
    scrollback: 10000,
    allowTransparency: false,
    convertEol: false,
    disableStdin: false,
    allowProposedApi: true,
    fastScrollModifier: 'alt',
  });

  fit = new FitAddon.FitAddon();
  term.loadAddon(fit);

  try {
    const wl = new WebLinksAddon.WebLinksAddon();
    term.loadAddon(wl);
  } catch(e) {}

  term.open(document.getElementById('term-wrap'));
  doResize();
  term.focus();

  term.onData(data => {
    if (ws && ws.readyState === WebSocket.OPEN)
      ws.send(JSON.stringify({ type:'input', data }));
  });
  term.onResize(({ cols, rows }) => {
    if (ws && ws.readyState === WebSocket.OPEN)
      ws.send(JSON.stringify({ type:'resize', cols, rows }));
  });
}

// ── WEBSOCKET ────────────────────────────────────────────────
function connect() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(proto + '//' + location.host + '/ws');

  ws.onopen = () => {
    setOk('root@ubuntu');
    term.focus();
    setTimeout(() => {
      doResize();
      term.focus();
    }, 250);
  };

  ws.onmessage = e => { term.write(e.data); };

  ws.onclose = () => {
    setOff('disconnected');
    if (alive) {
      term.write('\r\n\x1b[31m[!] connection lost\x1b[0m\r\n');
      document.getElementById('ov').classList.add('show');
    }
    alive = false;
  };

  ws.onerror = () => {
    setOff('error');
  };
}

function reconnect() {
  try { ws && ws.close(); } catch(e) {}
  setOff('reconnecting…');
  setTimeout(() => { initTerm(); connect(); }, 600);
}
function closeOv() { document.getElementById('ov').classList.remove('show'); }

// ── HELPERS ─────────────────────────────────────────────────
function sr(data) {   // send raw
  if (ws && ws.readyState === WebSocket.OPEN)
    ws.send(JSON.stringify({ type:'input', data }));
  term.focus();
}
function sl(cmd) { sr(cmd + '\n'); }  // send line
function sk(key) {                     // send ctrl key
  const m = { c:'\x03', d:'\x04', z:'\x1a', l:'\x0c',
               a:'\x01', e:'\x05', u:'\x15', k:'\x0b' };
  sr(m[key] || key);
}

// ── RESIZE ──────────────────────────────────────────────────
function doResize() {
  try {
    fit.fit();
    if (ws && ws.readyState === WebSocket.OPEN)
      ws.send(JSON.stringify({ type:'resize', cols:term.cols, rows:term.rows }));
  } catch(e) {}
}
window.addEventListener('resize', doResize);

// Mobile keyboard
if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', () => {
    const kb = window.innerHeight - window.visualViewport.height;
    const tw = document.getElementById('term-wrap');
    const xk = document.querySelector('.xkeys');
    const ab = document.querySelector('.abar');
    if (kb > 80) {
      ab.style.bottom = kb + 'px';
      xk.style.bottom = (kb + 44) + 'px';
      tw.style.bottom  = (kb + 88) + 'px';
    } else {
      ab.style.bottom = xk.style.bottom = tw.style.bottom = '';
    }
    setTimeout(doResize, 120);
  });
}

// ── BOOT ────────────────────────────────────────────────────
initTerm();
connect();
</script>
</body>
</html>
"""

# ──────────────────────────────────────────────────────────────────────────────

async def handle_index(request):
    return web.Response(text=HTML, content_type='text/html', headers={
        'ngrok-skip-browser-warning': 'true',
        'Cache-Control': 'no-cache',
    })

async def handle_upload(request):
    try:
        reader   = await request.multipart()
        field    = await reader.next()
        filename = os.path.basename(field.filename)
        updir    = '/root/uploads'
        os.makedirs(updir, exist_ok=True)
        fpath    = os.path.join(updir, filename)
        with open(fpath, 'wb') as f:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                f.write(chunk)
        return web.json_response({'ok': True, 'path': fpath})
    except Exception as e:
        return web.json_response({'ok': False, 'error': str(e)})

async def handle_ws(request):
    ws = web.WebSocketResponse(max_msg_size=16 * 1024 * 1024)
    await ws.prepare(request)

    while True:
        pid, fd = pty.fork()

        if pid == 0:
            # ── child: exec bash ──
            env = {
                'TERM':            'xterm-256color',
                'COLORTERM':       'truecolor',
                'SHELL':           '/bin/bash',
                'HOME':            '/root',
                'USER':            'root',
                'LOGNAME':         'root',
                'PATH':            '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin',
                'LANG':            'en_US.UTF-8',
                'LC_ALL':          'en_US.UTF-8',
                'DEBIAN_FRONTEND': 'noninteractive',
                'PS1':             r'\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ ',
            }
            try:
                os.chdir('/root')
            except Exception:
                pass
            os.execvpe('/bin/bash', ['/bin/bash', '--login'], env)
            os._exit(1)

        # ── parent: relay ──
        loop = asyncio.get_event_loop()
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
        done = asyncio.Event()

        async def pty_reader():
            while True:
                try:
                    data = await loop.run_in_executor(None, lambda: os.read(fd, 4096))
                    if not data or ws.closed:
                        break
                    await ws.send_str(data.decode('utf-8', errors='replace'))
                except OSError:
                    break
            done.set()

        async def ws_reader():
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        pkt = json.loads(msg.data)
                        if pkt['type'] == 'input':
                            os.write(fd, pkt['data'].encode('utf-8'))
                        elif pkt['type'] == 'resize':
                            cols = max(10, int(pkt.get('cols', 80)))
                            rows = max(2,  int(pkt.get('rows', 24)))
                            fcntl.ioctl(fd, termios.TIOCSWINSZ,
                                        struct.pack('HHHH', rows, cols, 0, 0))
                    except Exception:
                        pass
                elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                    break
            done.set()

        t1 = asyncio.ensure_future(pty_reader())
        t2 = asyncio.ensure_future(ws_reader())
        await done.wait()
        t1.cancel(); t2.cancel()

        for sig in (signal.SIGKILL,):
            try:
                os.kill(pid, sig)
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

        if ws.closed:
            break

        await ws.send_str('\r\n\x1b[33m[shell restarted]\x1b[0m\r\n')
        await asyncio.sleep(0.3)

    return ws


def main():
    app = web.Application(client_max_size=512 * 1024 * 1024)
    app.router.add_get('/',        handle_index)
    app.router.add_get('/ws',      handle_ws)
    app.router.add_post('/upload', handle_upload)
    port = int(os.environ.get('PORT', 8080))
    print(f'[*] Termux WebShell on :{port}')
    web.run_app(app, host='0.0.0.0', port=port, access_log=None)

if __name__ == '__main__':
    main()
