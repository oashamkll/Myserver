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
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/>
<title>Termux</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #000000;
  --text: #ffffff;
  --green: #55ff55;
  --yellow: #ffff55;
  --cyan: #55ffff;
  --red: #ff5555;
  --gray: #aaaaaa;
  --btn-bg: #1a1a1a;
  --btn-border: #333333;
  --btn-text: #ffffff;
  --topbar-bg: #111111;
  --cursor: #55ff55;
}
html, body {
  height: 100%;
  background: var(--bg);
  color: var(--text);
  font-family: 'Courier New', 'DejaVu Sans Mono', monospace;
  overflow: hidden;
  -webkit-text-size-adjust: 100%;
}

/* ── TOP BAR (Termux style) ── */
.topbar {
  height: 36px;
  background: var(--topbar-bg);
  border-bottom: 1px solid #222;
  display: flex;
  align-items: center;
  padding: 0 10px;
  gap: 8px;
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 100;
}
.topbar-title {
  font-size: 13px;
  font-weight: bold;
  color: var(--green);
  font-family: 'Courier New', monospace;
  letter-spacing: 0.5px;
}
.topbar-session {
  font-size: 11px;
  color: var(--gray);
  font-family: 'Courier New', monospace;
}
.dot-alive {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--green);
  animation: blink 2s infinite;
  flex-shrink: 0;
}
.dot-alive.off { background: var(--red); animation: none; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.2} }
.spacer { flex: 1; }
.tbtn {
  background: transparent;
  border: none;
  color: var(--gray);
  font-size: 13px;
  padding: 4px 7px;
  cursor: pointer;
  border-radius: 4px;
  font-family: monospace;
  -webkit-tap-highlight-color: transparent;
}
.tbtn:active { background: #222; }

/* ── TERMINAL ── */
.term-wrap {
  position: fixed;
  top: 36px;
  bottom: 132px;
  left: 0; right: 0;
  background: var(--bg);
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
  padding: 6px 4px 4px 4px;
}
#output {
  font-family: 'Courier New', 'DejaVu Sans Mono', monospace;
  font-size: 13px;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-all;
  min-height: 100%;
  color: var(--text);
}
@media(max-width:480px){ #output { font-size: 12px; } }

/* ANSI colors */
.f0{color:#000000} .f1{color:#ff5555} .f2{color:#55ff55} .f3{color:#ffff55}
.f4{color:#5555ff} .f5{color:#ff55ff} .f6{color:#55ffff} .f7{color:#ffffff}
.f8{color:#555555} .f9{color:#ff5555} .f10{color:#55ff55} .f11{color:#ffff55}
.f12{color:#5555ff} .f13{color:#ff55ff} .f14{color:#55ffff} .f15{color:#ffffff}
.bold{font-weight:bold} .dim{opacity:.5} .underline{text-decoration:underline}

/* ── EXTRA KEYS BAR (Termux style) ── */
.extrakeys {
  position: fixed;
  bottom: 88px;
  left: 0; right: 0;
  height: 44px;
  background: #111111;
  border-top: 1px solid #222;
  display: flex;
  overflow-x: auto;
  scrollbar-width: none;
  padding: 4px 4px;
  gap: 4px;
  z-index: 99;
  -webkit-overflow-scrolling: touch;
  align-items: center;
}
.extrakeys::-webkit-scrollbar { display: none; }
.ek {
  background: #1e1e1e;
  border: 1px solid #333;
  color: #dddddd;
  padding: 4px 10px;
  border-radius: 3px;
  font-size: 12px;
  font-family: 'Courier New', monospace;
  white-space: nowrap;
  cursor: pointer;
  flex-shrink: 0;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
  min-width: 34px;
  text-align: center;
}
.ek:active { background: #333; }
.ek.spec { color: var(--yellow); border-color: #555; }
.ek.ctrl-key { color: var(--cyan); border-color: #555; }

/* ── BOTTOM INPUT BAR ── */
.bottombar {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: 88px;
  background: #111111;
  border-top: 1px solid #222;
  display: flex;
  flex-direction: column;
  z-index: 100;
}
.input-row {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 6px 6px 0 6px;
  gap: 5px;
}
#cmd {
  flex: 1;
  background: #1a1a1a;
  border: 1px solid #333;
  color: var(--text);
  padding: 8px 10px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  outline: none;
  -webkit-appearance: none;
  caret-color: var(--green);
}
#cmd:focus { border-color: #555; }
#cmd::placeholder { color: #444; }
.send-btn {
  background: #1e1e1e;
  border: 1px solid #444;
  color: var(--green);
  width: 40px; height: 36px;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  font-family: monospace;
  -webkit-tap-highlight-color: transparent;
}
.send-btn:active { background: #333; }
.action-row {
  display: flex;
  padding: 4px 6px 6px 6px;
  gap: 4px;
}
.act-btn {
  flex: 1;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  color: #888;
  font-size: 11px;
  padding: 4px 2px;
  border-radius: 3px;
  cursor: pointer;
  font-family: monospace;
  text-align: center;
  -webkit-tap-highlight-color: transparent;
}
.act-btn:active { background: #222; color: #ccc; }

#file-input { display: none; }

/* ── DISCONNECT OVERLAY ── */
.overlay {
  display: none;
  position: fixed; inset: 0;
  background: rgba(0,0,0,.85);
  z-index: 200;
  align-items: center; justify-content: center;
}
.overlay.show { display: flex; }
.card {
  background: #111;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 24px;
  width: min(88vw,300px);
  text-align: center;
  font-family: 'Courier New', monospace;
}
.card h3 { font-size: 15px; color: var(--green); margin-bottom: 8px; }
.card p  { font-size: 12px; color: var(--gray); margin-bottom: 16px; }
.card button {
  background: #1e1e1e;
  border: 1px solid #55ff55;
  color: var(--green);
  padding: 8px 20px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'Courier New', monospace;
  cursor: pointer;
  width: 100%;
}
.card button:active { background: #222; }
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-title">Termux</div>
  <div class="topbar-session">[1]</div>
  <div class="dot-alive" id="dot"></div>
  <span style="font-size:11px;color:#555;font-family:monospace" id="stext">connecting...</span>
  <div class="spacer"></div>
  <button class="tbtn" onclick="doCtrl('l')" title="Clear">✕</button>
  <label class="tbtn" for="file-input" title="Upload">⇧</label>
  <button class="tbtn" onclick="reconnect()" title="Reconnect">↺</button>
</div>
<input type="file" id="file-input" onchange="uploadFile(this)"/>

<div class="term-wrap" id="tw"><div id="output"></div></div>

<!-- Extra keys like Termux -->
<div class="extrakeys">
  <span class="ek ctrl-key" onclick="doCtrl('c')">Ctrl+C</span>
  <span class="ek ctrl-key" onclick="doCtrl('d')">Ctrl+D</span>
  <span class="ek ctrl-key" onclick="doCtrl('z')">Ctrl+Z</span>
  <span class="ek spec"    onclick="doCtrl('tab')">TAB</span>
  <span class="ek spec"    onclick="doHist(1)">▲</span>
  <span class="ek spec"    onclick="doHist(-1)">▼</span>
  <span class="ek"         onclick="typeCmd('| ')">|</span>
  <span class="ek"         onclick="typeCmd('> ')">></span>
  <span class="ek"         onclick="typeCmd('&& ')">&amp;&amp;</span>
  <span class="ek"         onclick="typeCmd('/')">  /  </span>
  <span class="ek"         onclick="typeCmd('~')">  ~  </span>
  <span class="ek"         onclick="typeCmd('-')">  -  </span>
  <span class="ek"         onclick="run('ls -la')">ls</span>
  <span class="ek"         onclick="run('pwd')">pwd</span>
  <span class="ek"         onclick="run('cd ~')">cd ~</span>
  <span class="ek"         onclick="run('cd ..')">cd ..</span>
  <span class="ek"         onclick="typeCmd('apt install -y ')">apt install</span>
  <span class="ek"         onclick="run('apt update')">apt update</span>
  <span class="ek"         onclick="typeCmd('python3 ')">python3</span>
  <span class="ek"         onclick="typeCmd('pip install ')">pip</span>
  <span class="ek"         onclick="typeCmd('nano ')">nano</span>
  <span class="ek"         onclick="typeCmd('cat ')">cat</span>
  <span class="ek"         onclick="run('whoami')">whoami</span>
  <span class="ek"         onclick="run('df -h')">df</span>
  <span class="ek"         onclick="run('free -h')">free</span>
  <span class="ek"         onclick="run('ps aux')">ps</span>
  <span class="ek"         onclick="run('uname -a')">uname</span>
  <span class="ek"         onclick="run('ifconfig')">ip</span>
</div>

<div class="bottombar">
  <div class="input-row">
    <input id="cmd" type="text" placeholder="$ type command..."
      autocomplete="off" autocorrect="off" autocapitalize="none" spellcheck="false"
      onkeydown="onKey(event)"/>
    <button class="send-btn" onclick="send()">↵</button>
  </div>
  <div class="action-row">
    <button class="act-btn" onclick="run('clear')">CLEAR</button>
    <button class="act-btn" onclick="run('ls')">FILES</button>
    <button class="act-btn" onclick="run('top -bn1 | head -20')">TOP</button>
    <button class="act-btn" onclick="run('df -h')">DISK</button>
    <button class="act-btn" onclick="run('free -h')">MEM</button>
    <button class="act-btn" onclick="doCtrl('c')">KILL</button>
  </div>
</div>

<div class="overlay" id="ov">
  <div class="card">
    <h3>~ disconnected ~</h3>
    <p>Connection lost.<br/>Tap to reconnect.</p>
    <button onclick="reconnect();closeOv()">↺ reconnect</button>
  </div>
</div>

<script>
let ws=null, hist=[], histIdx=-1, alive=false;
const out=document.getElementById('output');
const tw=document.getElementById('tw');
const inp=document.getElementById('cmd');
const dot=document.getElementById('dot');
const stxt=document.getElementById('stext');

// ── ANSI PARSER ──
function ansi(str){
  str=str.replace(/\r\n/g,'\n').replace(/\r/g,'\n');
  let html='',bold=false,dim=false,underline=false,fg=-1;
  const cls=()=>(bold||dim||underline||fg>=0)?'</span>':'';
  const opn=()=>{
    const c=[];
    if(bold)c.push('bold');
    if(dim)c.push('dim');
    if(underline)c.push('underline');
    if(fg>=0)c.push('f'+fg);
    return c.length?'<span class="'+c.join(' ')+'">':'';
  };
  let i=0;
  while(i<str.length){
    if(str[i]==='\x1b'&&str[i+1]==='['){
      let j=i+2;
      while(j<str.length&&!/[A-Za-z]/.test(str[j]))j++;
      const fin=str[j],seq=str.slice(i+2,j);
      i=j+1;
      if(fin==='m'){
        html+=cls();
        (seq||'0').split(';').forEach(s=>{
          const n=parseInt(s)||0;
          if(n===0){bold=dim=underline=false;fg=-1;}
          else if(n===1)bold=true;
          else if(n===2)dim=true;
          else if(n===4)underline=true;
          else if(n===22){bold=false;dim=false;}
          else if(n===24)underline=false;
          else if(n>=30&&n<=37)fg=n-30;
          else if(n>=90&&n<=97)fg=n-82;
          else if(n===39)fg=-1;
        });
        html+=opn();
      }
      // skip other escape sequences (cursor moves etc)
    } else {
      const ch=str[i++];
      html+=ch==='&'?'&amp;':ch==='<'?'&lt;':ch==='>'?'&gt;':ch;
    }
  }
  html+=cls();
  return html;
}

function write(t){
  out.innerHTML+=ansi(t);
  // keep output size manageable
  if(out.innerHTML.length>500000){
    out.innerHTML=out.innerHTML.slice(-400000);
  }
  tw.scrollTop=tw.scrollHeight;
}
function writeSys(m,c){
  out.innerHTML+='<span style="color:'+c+';font-style:italic">'+m.replace(/</g,'&lt;')+'</span>\n';
  tw.scrollTop=tw.scrollHeight;
}
function doCtrl(k){
  const m={c:'\x03',d:'\x04',z:'\x1a',l:'\x0c',tab:'\x09',a:'\x01',e:'\x05',u:'\x15',k:'\x0b'};
  sendRaw(m[k]||k); inp.focus();
}

// ── WEBSOCKET ──
function setOk(m){dot.className='dot-alive';stxt.textContent=m;alive=true;}
function setOff(m){dot.className='dot-alive off';stxt.textContent=m;alive=false;}

function connect(){
  const p=location.protocol==='https:'?'wss:':'ws:';
  ws=new WebSocket(p+'//'+location.host+'/ws');
  ws.onopen=()=>{
    setOk('root@localhost');
    writeSys('Welcome to Termux!','#55ff55');
    writeSys('Type commands below. You are ROOT on Ubuntu Linux.','#aaaaaa');
    writeSys('','#aaaaaa');
    sendPkt({type:'resize',cols:Math.floor(tw.clientWidth/7.8)||100,rows:Math.floor(tw.clientHeight/18)||30});
  };
  ws.onmessage=e=>write(e.data);
  ws.onclose=()=>{
    setOff('disconnected');
    if(alive) document.getElementById('ov').classList.add('show');
    alive=false;
  };
  ws.onerror=()=>setOff('error');
}

function reconnect(){
  try{ws&&ws.close();}catch(e){}
  out.innerHTML='';
  setOff('reconnecting...');
  setTimeout(connect,600);
}
function closeOv(){document.getElementById('ov').classList.remove('show');}

function sendPkt(o){if(ws&&ws.readyState===WebSocket.OPEN)ws.send(JSON.stringify(o));}
function sendRaw(d){sendPkt({type:'input',data:d});}

function send(){
  const v=inp.value;
  if(!v.trim())return;
  hist.unshift(v); histIdx=-1;
  sendRaw(v+'\n');
  inp.value='';
}
function run(cmd){sendRaw(cmd+'\n'); inp.focus();}
function typeCmd(txt){inp.value+=txt; inp.focus();}
function doHist(dir){
  if(!hist.length)return;
  histIdx=Math.max(-1,Math.min(hist.length-1,histIdx+dir));
  inp.value=histIdx<0?'':hist[histIdx];
}
function onKey(e){
  if(e.key==='Enter'){e.preventDefault();send();}
  else if(e.key==='ArrowUp'){e.preventDefault();doHist(1);}
  else if(e.key==='ArrowDown'){e.preventDefault();doHist(-1);}
  else if(e.key==='Tab'){e.preventDefault();doCtrl('tab');}
  else if(e.ctrlKey){
    const k=e.key.toLowerCase();
    const m={c:'\x03',d:'\x04',z:'\x1a',l:'\x0c',a:'\x01',e:'\x05',u:'\x15',k:'\x0b'};
    if(m[k]){e.preventDefault();sendRaw(m[k]);}
  }
}

// ── FILE UPLOAD ──
async function uploadFile(input){
  const file=input.files[0]; if(!file)return;
  writeSys('\n[*] Uploading: '+file.name+' ...','#ffff55');
  const fd=new FormData(); fd.append('file',file);
  try{
    const r=await fetch('/upload',{method:'POST',body:fd});
    const d=await r.json();
    if(d.ok){writeSys('[+] Saved: '+d.path,'#55ff55'); run('ls -lh "'+d.path+'"');}
    else writeSys('[-] Error: '+d.error,'#ff5555');
  }catch(e){writeSys('[-] Upload failed','#ff5555');}
  input.value='';
}

// ── MOBILE KEYBOARD ADJUST ──
if(window.visualViewport){
  window.visualViewport.addEventListener('resize',()=>{
    const kb=window.innerHeight-window.visualViewport.height;
    const bb=document.querySelector('.bottombar');
    const ek=document.querySelector('.extrakeys');
    if(kb>80){
      bb.style.bottom=kb+'px';
      ek.style.bottom=(kb+88)+'px';
      tw.style.bottom=(kb+132)+'px';
    } else {
      bb.style.bottom='';
      ek.style.bottom='';
      tw.style.bottom='';
    }
    tw.scrollTop=tw.scrollHeight;
  });
}

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
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    while True:
        pid, fd = pty.fork()

        if pid == 0:
            # Child process — exec bash as root
            env = {
                'TERM': 'xterm-256color',
                'SHELL': '/bin/bash',
                'HOME': '/root',
                'USER': 'root',
                'LOGNAME': 'root',
                'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin',
                'LANG': 'en_US.UTF-8',
                'DEBIAN_FRONTEND': 'noninteractive',
                # Termux-style green prompt
                'PS1': r'\[\033[0;32m\]$ \[\033[0m\]',
            }
            os.chdir('/root')
            os.execvpe('/bin/bash', ['/bin/bash', '--login'], env)
        else:
            loop = asyncio.get_event_loop()
            fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 120, 0, 0))
            shell_done = asyncio.Event()

            async def pty_reader():
                while True:
                    try:
                        data = await loop.run_in_executor(None, lambda: os.read(fd, 8192))
                        if not data:
                            break
                        if ws.closed:
                            break
                        await ws.send_str(data.decode('utf-8', errors='replace'))
                    except OSError:
                        break
                shell_done.set()

            async def ws_reader():
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            pkt = json.loads(msg.data)
                            if pkt['type'] == 'input':
                                os.write(fd, pkt['data'].encode('utf-8'))
                            elif pkt['type'] == 'resize':
                                cols = max(20, int(pkt.get('cols', 120)))
                                rows = max(5,  int(pkt.get('rows', 40)))
                                fcntl.ioctl(fd, termios.TIOCSWINSZ,
                                            struct.pack('HHHH', rows, cols, 0, 0))
                        except Exception:
                            pass
                    elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                        break
                shell_done.set()

            t1 = asyncio.ensure_future(pty_reader())
            t2 = asyncio.ensure_future(ws_reader())
            await shell_done.wait()
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

            if ws.closed:
                break

            # Shell exited — restart automatically
            await ws.send_str('\r\n\x1b[32m[*] shell restarted\x1b[0m\r\n')
            await asyncio.sleep(0.5)

    return ws

def main():
    app = web.Application(client_max_size=500 * 1024 * 1024)
    app.router.add_get('/', handle_index)
    app.router.add_get('/ws', handle_ws)
    app.router.add_post('/upload', handle_upload)
    port = int(os.environ.get('PORT', 8080))
    print(f'[*] Termux Server (ROOT) on :{port}')
    web.run_app(app, host='0.0.0.0', port=port, access_log=None)

if __name__ == '__main__':
    main()
