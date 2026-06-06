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
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/>
<title>MyServer — Ubuntu Shell</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #0d1117;
    --bar: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --green: #3fb950;
    --blue: #58a6ff;
    --red: #f85149;
    --yellow: #d29922;
    --gray: #8b949e;
    --term-bg: #010409;
    --term-green: #39d353;
    --term-blue: #58a6ff;
    --term-red: #f85149;
    --term-yellow: #e3b341;
    --term-cyan: #39c5cf;
    --term-magenta: #bc8cff;
    --term-white: #e6edf3;
  }

  html, body {
    height: 100%;
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', system-ui, sans-serif;
    overflow: hidden;
  }

  /* ── TOP BAR ── */
  .topbar {
    height: 48px;
    background: var(--bar);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    padding: 0 12px;
    gap: 10px;
    flex-shrink: 0;
    position: fixed;
    top: 0; left: 0; right: 0;
    z-index: 100;
  }

  .logo {
    font-size: 15px;
    font-weight: 700;
    color: var(--blue);
    display: flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
  }

  .status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--green);
    flex-shrink: 0;
    animation: blink 2s infinite;
  }
  .status-dot.offline { background: var(--red); animation: none; }

  @keyframes blink {
    0%,100%{opacity:1} 50%{opacity:.3}
  }

  .status-text {
    font-size: 12px;
    color: var(--gray);
    display: none;
  }
  @media(min-width:400px){ .status-text { display: block; } }

  .spacer { flex: 1; }

  .topbar-btn {
    background: #21262d;
    border: 1px solid var(--border);
    color: var(--text);
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
    white-space: nowrap;
    -webkit-tap-highlight-color: transparent;
    touch-action: manipulation;
  }
  .topbar-btn:active { background: var(--border); }
  .topbar-btn.danger { border-color: var(--red); color: var(--red); }

  /* ── TERMINAL WRAPPER ── */
  .term-wrap {
    position: fixed;
    top: 48px;
    bottom: 44px;
    left: 0; right: 0;
    background: var(--term-bg);
    overflow-y: auto;
    overflow-x: hidden;
    -webkit-overflow-scrolling: touch;
    padding: 8px 4px 8px 8px;
  }

  /* ── OUTPUT ── */
  #output {
    font-family: 'Cascadia Code', 'Fira Code', 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-all;
    min-height: 100%;
  }
  @media(max-width:480px){ #output { font-size: 11px; } }

  /* ANSI colours */
  .c0  { color: #010409; }
  .c1  { color: var(--term-red); }
  .c2  { color: var(--term-green); }
  .c3  { color: var(--term-yellow); }
  .c4  { color: var(--term-blue); }
  .c5  { color: var(--term-magenta); }
  .c6  { color: var(--term-cyan); }
  .c7  { color: var(--term-white); }
  .c8  { color: #6e7681; }
  .c9  { color: #f85149; }
  .c10 { color: #56d364; }
  .c11 { color: #e3b341; }
  .c12 { color: #79c0ff; }
  .c13 { color: #d2a8ff; }
  .c14 { color: #56d8c8; }
  .c15 { color: #f0f6fc; }
  .bold { font-weight: bold; }
  .dim  { opacity: .5; }
  .cur  { display:inline-block; width:8px; background:var(--blue); animation: cur 1s step-end infinite; }
  @keyframes cur { 0%,100%{opacity:1} 50%{opacity:0} }

  /* ── BOTTOM BAR ── */
  .bottombar {
    position: fixed;
    bottom: 0; left: 0; right: 0;
    height: 44px;
    background: var(--bar);
    border-top: 1px solid var(--border);
    display: flex;
    align-items: center;
    padding: 0 8px;
    gap: 6px;
    z-index: 100;
  }

  #cmd {
    flex: 1;
    background: #21262d;
    border: 1px solid var(--border);
    color: var(--text);
    padding: 8px 10px;
    border-radius: 8px;
    font-family: 'Cascadia Code', 'Fira Code', monospace;
    font-size: 13px;
    outline: none;
    -webkit-appearance: none;
    min-width: 0;
  }
  #cmd:focus { border-color: var(--blue); }

  .send-btn {
    background: var(--blue);
    border: none;
    color: #000;
    width: 36px; height: 36px;
    border-radius: 8px;
    font-size: 18px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    -webkit-tap-highlight-color: transparent;
    touch-action: manipulation;
  }
  .send-btn:active { opacity: .7; }

  /* ── QUICK KEYS ── */
  .quickkeys {
    position: fixed;
    bottom: 44px;
    left: 0; right: 0;
    background: #0d1117;
    border-top: 1px solid var(--border);
    display: flex;
    overflow-x: auto;
    scrollbar-width: none;
    padding: 4px 6px;
    gap: 5px;
    z-index: 99;
    -webkit-overflow-scrolling: touch;
  }
  .quickkeys::-webkit-scrollbar { display:none; }
  .qk {
    background: #21262d;
    border: 1px solid var(--border);
    color: var(--text);
    padding: 4px 10px;
    border-radius: 5px;
    font-size: 12px;
    white-space: nowrap;
    cursor: pointer;
    flex-shrink: 0;
    font-family: monospace;
    -webkit-tap-highlight-color: transparent;
    touch-action: manipulation;
  }
  .qk:active { background: var(--border); }

  /* When keyboard is open, shift everything up */
  body.kb-open .quickkeys { bottom: 44px; }

  /* ── UPLOAD ── */
  #file-input { display: none; }

  /* ── MODAL ── */
  .modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,.7);
    z-index: 200;
    align-items: center;
    justify-content: center;
  }
  .modal-overlay.show { display: flex; }
  .modal {
    background: var(--bar);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    width: min(90vw, 340px);
  }
  .modal h3 { margin-bottom: 12px; font-size: 15px; }
  .modal p  { font-size: 13px; color: var(--gray); margin-bottom: 16px; line-height: 1.5; }
  .modal-btns { display:flex; gap:8px; justify-content: flex-end; }
  .modal-btns button {
    padding: 7px 16px;
    border-radius: 7px;
    border: 1px solid var(--border);
    background: #21262d;
    color: var(--text);
    font-size: 13px;
    cursor: pointer;
  }
  .modal-btns .primary {
    background: var(--blue);
    border-color: var(--blue);
    color: #000;
    font-weight: 600;
  }
</style>
</head>
<body>

<!-- TOP BAR -->
<div class="topbar">
  <div class="logo">🖥️ MyServer</div>
  <div class="status-dot" id="dot"></div>
  <span class="status-text" id="status-text">Connecting...</span>
  <div class="spacer"></div>
  <button class="topbar-btn" onclick="clearScreen()">🗑️</button>
  <label class="topbar-btn" for="file-input">📁</label>
  <button class="topbar-btn danger" onclick="reconnect()">↺</button>
</div>

<input type="file" id="file-input" onchange="uploadFile(this)"/>

<!-- TERMINAL OUTPUT -->
<div class="term-wrap" id="term-wrap">
  <div id="output"></div>
</div>

<!-- QUICK KEYS -->
<div class="quickkeys" id="quickkeys">
  <span class="qk" onclick="sendCtrl('c')">Ctrl+C</span>
  <span class="qk" onclick="sendCtrl('d')">Ctrl+D</span>
  <span class="qk" onclick="sendCtrl('l')">Clear</span>
  <span class="qk" onclick="sendCtrl('z')">Ctrl+Z</span>
  <span class="qk" onclick="insertText('ls\n')">ls</span>
  <span class="qk" onclick="insertText('pwd\n')">pwd</span>
  <span class="qk" onclick="insertText('cd ~\n')">cd ~</span>
  <span class="qk" onclick="insertText('cd ..\n')">cd ..</span>
  <span class="qk" onclick="insertText('clear\n')">clear</span>
  <span class="qk" onclick="insertText('python3 ')">python3</span>
  <span class="qk" onclick="insertText('pip install ')">pip</span>
  <span class="qk" onclick="insertText('nano ')">nano</span>
  <span class="qk" onclick="insertText('cat ')">cat</span>
  <span class="qk" onclick="insertText('sudo ')">sudo</span>
  <span class="qk" onclick="insertText('\t')">TAB</span>
  <span class="qk" onclick="historyUp()">▲</span>
  <span class="qk" onclick="historyDown()">▼</span>
</div>

<!-- BOTTOM BAR -->
<div class="bottombar">
  <input id="cmd" type="text" placeholder="Enter command..." autocomplete="off"
    autocorrect="off" autocapitalize="none" spellcheck="false"
    onkeydown="onKey(event)"/>
  <button class="send-btn" onclick="sendCmd()">➤</button>
</div>

<!-- MODAL -->
<div class="modal-overlay" id="modal">
  <div class="modal">
    <h3>⚠️ Disconnect</h3>
    <p>Lost connection to server. Want to reconnect?</p>
    <div class="modal-btns">
      <button onclick="closeModal()">Cancel</button>
      <button class="primary" onclick="reconnect();closeModal()">Reconnect</button>
    </div>
  </div>
</div>

<script>
// ── STATE ──
let ws = null;
let history = [];
let histIdx = -1;
let connected = false;
const out = document.getElementById('output');
const termWrap = document.getElementById('term-wrap');
const cmdInput = document.getElementById('cmd');
const dot = document.getElementById('dot');
const statusText = document.getElementById('status-text');

// ── ANSI PARSER ──
function ansiToHtml(str) {
  // Remove carriage returns (handle \r\n)
  str = str.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  // Escape HTML
  str = str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

  let result = '';
  let i = 0;
  let bold = false, dim = false, color = -1;

  const closeSpan = () => {
    if (bold || dim || color >= 0) { result += '</span>'; bold=false; dim=false; color=-1; }
  };

  while (i < str.length) {
    if (str[i] === '\x1b' && str[i+1] === '[') {
      // parse CSI
      let j = i+2;
      while (j < str.length && str[j] !== 'm' && str[j] !== 'K' && str[j] !== 'J' && str[j] !== 'A' && str[j] !== 'H' && str[j] !== 'G') j++;
      const seq = str.slice(i+2, j);
      const cmd = str[j];
      i = j+1;

      if (cmd === 'm') {
        const codes = seq.split(';').map(Number);
        let classes = [];
        for (let k=0; k<codes.length; k++) {
          const c = codes[k];
          if (c === 0) { closeSpan(); continue; }
          if (c === 1) { bold = true; }
          if (c === 2) { dim = true; }
          if (c >= 30 && c <= 37) { color = c-30; }
          if (c >= 90 && c <= 97) { color = c-90+8; }
          if (c === 39) { color = -1; }
        }
        closeSpan();
        const cls = [];
        if (bold) cls.push('bold');
        if (dim) cls.push('dim');
        if (color >= 0) cls.push('c'+color);
        if (cls.length) result += `<span class="${cls.join(' ')}">`;
      }
      // ignore other escape sequences
    } else {
      result += str[i];
      i++;
    }
  }
  closeSpan();
  return result;
}

// ── WRITE TO TERMINAL ──
function write(text) {
  const html = ansiToHtml(text);
  out.innerHTML += html;
  termWrap.scrollTop = termWrap.scrollHeight;
}

function writeLine(text, cls) {
  const span = cls ? `<span class="${cls}">` : '';
  const end = cls ? '</span>' : '';
  out.innerHTML += span + text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') + end + '\n';
  termWrap.scrollTop = termWrap.scrollHeight;
}

function clearScreen() {
  out.innerHTML = '';
}

// ── WEBSOCKET ──
function setStatus(ok, msg) {
  dot.className = 'status-dot' + (ok ? '' : ' offline');
  statusText.textContent = msg;
  connected = ok;
}

function connect() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(proto + '//' + location.host + '/ws');

  ws.onopen = () => {
    setStatus(true, 'Connected · Ubuntu');
    writeLine('\n✅  Connected to MyServer (Ubuntu Linux)', 'c2 bold');
    writeLine('💡  Type commands below or use quick keys\n', 'c8');
  };

  ws.onmessage = e => write(e.data);

  ws.onclose = () => {
    setStatus(false, 'Disconnected');
    if (connected) document.getElementById('modal').classList.add('show');
  };

  ws.onerror = () => setStatus(false, 'Error');
}

function reconnect() {
  if (ws) { try { ws.close(); } catch(e){} }
  clearScreen();
  setStatus(false, 'Reconnecting...');
  setTimeout(connect, 600);
}

function closeModal() {
  document.getElementById('modal').classList.remove('show');
}

// ── SEND ──
function sendRaw(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'input', data }));
  }
}

function sendCmd() {
  const val = cmdInput.value;
  if (val === '') return;
  history.unshift(val);
  histIdx = -1;
  sendRaw(val + '\n');
  cmdInput.value = '';
}

function insertText(text) {
  sendRaw(text);
  cmdInput.focus();
}

function sendCtrl(key) {
  const map = { c:'\x03', d:'\x04', l:'\x0c', z:'\x1a' };
  sendRaw(map[key] || key);
}

function historyUp() {
  if (history.length === 0) return;
  histIdx = Math.min(histIdx+1, history.length-1);
  cmdInput.value = history[histIdx];
}

function historyDown() {
  histIdx = Math.max(histIdx-1, -1);
  cmdInput.value = histIdx < 0 ? '' : history[histIdx];
}

function onKey(e) {
  if (e.key === 'Enter') { e.preventDefault(); sendCmd(); }
  if (e.key === 'ArrowUp') { e.preventDefault(); historyUp(); }
  if (e.key === 'ArrowDown') { e.preventDefault(); historyDown(); }
  if (e.key === 'Tab') { e.preventDefault(); sendRaw('\t'); }
}

// ── FILE UPLOAD ──
async function uploadFile(input) {
  const file = input.files[0];
  if (!file) return;
  writeLine(`\n📁 Uploading: ${file.name} ...`, 'c3');
  const fd = new FormData();
  fd.append('file', file);
  try {
    const res = await fetch('/upload', { method:'POST', body:fd });
    const d = await res.json();
    if (d.ok) {
      writeLine(`✅ Uploaded to: ${d.path}`, 'c2');
      sendRaw(`ls -lh "${d.path}"\n`);
    } else {
      writeLine(`❌ Error: ${d.error}`, 'c1');
    }
  } catch(e) {
    writeLine('❌ Upload failed', 'c1');
  }
  input.value = '';
}

// ── KEYBOARD VISIBILITY (mobile) ──
const origBottom = 44;
if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', () => {
    const kbHeight = window.innerHeight - window.visualViewport.height;
    const qk = document.getElementById('quickkeys');
    const bb = document.querySelector('.bottombar');
    const tw = document.getElementById('term-wrap');
    if (kbHeight > 100) {
      bb.style.bottom = kbHeight + 'px';
      qk.style.bottom = (kbHeight + 44) + 'px';
      tw.style.bottom = (kbHeight + 44 + 32) + 'px';
    } else {
      bb.style.bottom = '';
      qk.style.bottom = '';
      tw.style.bottom = '';
    }
    termWrap.scrollTop = termWrap.scrollHeight;
  });
}

// ── INIT ──
connect();
</script>
</body>
</html>
"""

async def handle_index(request):
    return web.Response(text=HTML, content_type='text/html', headers={
        'ngrok-skip-browser-warning': 'true'
    })

async def handle_upload(request):
    try:
        reader = await request.multipart()
        field = await reader.next()
        filename = os.path.basename(field.filename)
        upload_dir = os.path.expanduser('~/uploads')
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
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    pid, fd = pty.fork()

    if pid == 0:
        env = os.environ.copy()
        env['TERM'] = 'xterm-256color'
        env['SHELL'] = '/bin/bash'
        env['HOME'] = os.path.expanduser('~')
        env['LANG'] = 'en_US.UTF-8'
        os.execvpe('/bin/bash', ['/bin/bash', '--login'], env)
    else:
        loop = asyncio.get_event_loop()

        # Set initial terminal size
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 120, 0, 0))

        async def pty_reader():
            while True:
                try:
                    data = await loop.run_in_executor(None, lambda: os.read(fd, 8192))
                    if not data:
                        break
                    await ws.send_str(data.decode('utf-8', errors='replace'))
                except OSError:
                    break

        async def ws_reader():
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        pkt = json.loads(msg.data)
                        if pkt['type'] == 'input':
                            os.write(fd, pkt['data'].encode('utf-8'))
                        elif pkt['type'] == 'resize':
                            cols = int(pkt.get('cols', 120))
                            rows = int(pkt.get('rows', 40))
                            fcntl.ioctl(fd, termios.TIOCSWINSZ,
                                        struct.pack('HHHH', rows, cols, 0, 0))
                    except Exception:
                        pass
                elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                    break

        t1 = asyncio.ensure_future(pty_reader())
        t2 = asyncio.ensure_future(ws_reader())
        await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
        for t in (t1, t2):
            t.cancel()

        try:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        except Exception:
            pass
        try:
            os.close(fd)
        except Exception:
            pass

    return ws

def main():
    app = web.Application(client_max_size=200 * 1024 * 1024)
    app.router.add_get('/', handle_index)
    app.router.add_get('/ws', handle_ws)
    app.router.add_post('/upload', handle_upload)
    port = int(os.environ.get('PORT', 8080))
    print(f'🚀 MyServer on port {port}')
    web.run_app(app, host='0.0.0.0', port=port, access_log=None)

if __name__ == '__main__':
    main()
