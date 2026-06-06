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

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🖥️ MyServer — Linux Shell</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css"/>
    <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0d1117;
            color: #c9d1d9;
            font-family: 'Segoe UI', sans-serif;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .topbar {
            background: #161b22;
            border-bottom: 1px solid #30363d;
            padding: 10px 20px;
            display: flex;
            align-items: center;
            gap: 15px;
            flex-shrink: 0;
        }
        .logo {
            font-size: 20px;
            font-weight: bold;
            color: #58a6ff;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .status {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            color: #8b949e;
        }
        .dot {
            width: 8px; height: 8px;
            border-radius: 50%;
            background: #3fb950;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        .spacer { flex: 1; }
        .btn {
            background: #21262d;
            border: 1px solid #30363d;
            color: #c9d1d9;
            padding: 6px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            transition: background 0.2s;
        }
        .btn:hover { background: #30363d; }
        .btn-danger { border-color: #f85149; color: #f85149; }
        .btn-danger:hover { background: #f8514920; }
        #terminal-container {
            flex: 1;
            padding: 10px;
            overflow: hidden;
        }
        .upload-bar {
            background: #161b22;
            border-top: 1px solid #30363d;
            padding: 8px 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 13px;
            color: #8b949e;
            flex-shrink: 0;
        }
        #file-input { display: none; }
        .upload-label {
            background: #21262d;
            border: 1px solid #30363d;
            color: #c9d1d9;
            padding: 4px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
        }
        .upload-label:hover { background: #30363d; }
        #upload-status { color: #3fb950; }
    </style>
</head>
<body>
    <div class="topbar">
        <div class="logo">🖥️ MyServer</div>
        <div class="status">
            <div class="dot"></div>
            Ubuntu Linux Shell
        </div>
        <div class="spacer"></div>
        <button class="btn" onclick="clearTerminal()">🗑️ Clear</button>
        <button class="btn btn-danger" onclick="reconnect()">🔄 Reconnect</button>
    </div>

    <div id="terminal-container"></div>

    <div class="upload-bar">
        <label class="upload-label" for="file-input">📁 Upload File</label>
        <input type="file" id="file-input" onchange="uploadFile(this)"/>
        <span id="upload-status"></span>
        <div class="spacer"></div>
        <span>Press Ctrl+C to interrupt · Ctrl+L to clear</span>
    </div>

    <script>
        const term = new Terminal({
            theme: {
                background: '#0d1117',
                foreground: '#c9d1d9',
                cursor: '#58a6ff',
                cursorAccent: '#0d1117',
                selection: '#264f78',
                black: '#0d1117',
                red: '#f85149',
                green: '#3fb950',
                yellow: '#d29922',
                blue: '#58a6ff',
                magenta: '#bc8cff',
                cyan: '#39c5cf',
                white: '#c9d1d9',
                brightBlack: '#6e7681',
                brightRed: '#f85149',
                brightGreen: '#3fb950',
                brightYellow: '#d29922',
                brightBlue: '#58a6ff',
                brightMagenta: '#bc8cff',
                brightCyan: '#39c5cf',
                brightWhite: '#ffffff',
            },
            fontFamily: '"Cascadia Code", "Fira Code", "Courier New", monospace',
            fontSize: 14,
            lineHeight: 1.4,
            cursorBlink: true,
            cursorStyle: 'bar',
            scrollback: 5000,
            allowTransparency: true,
        });

        const fitAddon = new FitAddon.FitAddon();
        term.loadAddon(fitAddon);
        term.open(document.getElementById('terminal-container'));
        fitAddon.fit();

        let ws = null;

        function connect() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws`);

            ws.onopen = () => {
                term.writeln('\r\n\x1b[32m✅ Connected to MyServer!\x1b[0m\r\n');
                sendResize();
            };

            ws.onmessage = (e) => {
                term.write(e.data);
            };

            ws.onclose = () => {
                term.writeln('\r\n\x1b[31m❌ Disconnected. Click Reconnect to try again.\x1b[0m\r\n');
            };

            ws.onerror = () => {
                term.writeln('\r\n\x1b[31m⚠️ Connection error.\x1b[0m\r\n');
            };
        }

        function sendResize() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'resize',
                    cols: term.cols,
                    rows: term.rows
                }));
            }
        }

        term.onData((data) => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'input', data: data }));
            }
        });

        window.addEventListener('resize', () => {
            fitAddon.fit();
            sendResize();
        });

        function clearTerminal() {
            term.clear();
        }

        function reconnect() {
            if (ws) ws.close();
            term.writeln('\r\n\x1b[33m🔄 Reconnecting...\x1b[0m\r\n');
            setTimeout(connect, 500);
        }

        async function uploadFile(input) {
            const file = input.files[0];
            if (!file) return;
            const status = document.getElementById('upload-status');
            status.textContent = `Uploading ${file.name}...`;
            const formData = new FormData();
            formData.append('file', file);
            try {
                const res = await fetch('/upload', { method: 'POST', body: formData });
                const data = await res.json();
                if (data.ok) {
                    status.textContent = `✅ Uploaded: ${data.path}`;
                    term.writeln(`\r\n\x1b[32m📁 File uploaded: ${data.path}\x1b[0m\r\n`);
                } else {
                    status.textContent = `❌ Error: ${data.error}`;
                }
            } catch(e) {
                status.textContent = '❌ Upload failed';
            }
            input.value = '';
        }

        connect();
    </script>
</body>
</html>
"""

clients = {}

async def handle_index(request):
    return web.Response(text=HTML, content_type='text/html')

async def handle_upload(request):
    try:
        reader = await request.multipart()
        field = await reader.next()
        filename = field.filename
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

    # Spawn a real bash shell via PTY
    pid, fd = pty.fork()

    if pid == 0:
        # Child: exec bash
        env = os.environ.copy()
        env['TERM'] = 'xterm-256color'
        env['SHELL'] = '/bin/bash'
        env['HOME'] = os.path.expanduser('~')
        env['USER'] = os.environ.get('USER', 'runner')
        os.execvpe('/bin/bash', ['/bin/bash', '--login'], env)
    else:
        # Parent: relay between websocket and PTY
        loop = asyncio.get_event_loop()

        async def pty_to_ws():
            while True:
                try:
                    data = await loop.run_in_executor(None, lambda: os.read(fd, 4096))
                    if not data:
                        break
                    await ws.send_str(data.decode('utf-8', errors='replace'))
                except OSError:
                    break

        async def ws_to_pty():
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        packet = json.loads(msg.data)
                        if packet['type'] == 'input':
                            os.write(fd, packet['data'].encode())
                        elif packet['type'] == 'resize':
                            cols = packet.get('cols', 80)
                            rows = packet.get('rows', 24)
                            fcntl.ioctl(fd, termios.TIOCSWINSZ,
                                        struct.pack('HHHH', rows, cols, 0, 0))
                    except Exception:
                        pass
                elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                    break

        pty_task = asyncio.ensure_future(pty_to_ws())
        ws_task = asyncio.ensure_future(ws_to_pty())

        done, pending = await asyncio.wait(
            [pty_task, ws_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

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
    app = web.Application(client_max_size=100 * 1024 * 1024)  # 100MB upload
    app.router.add_get('/', handle_index)
    app.router.add_get('/ws', handle_ws)
    app.router.add_post('/upload', handle_upload)

    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 MyServer running on port {port}")
    web.run_app(app, host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()
