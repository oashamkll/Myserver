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
<title>MyServer — Ubuntu Root Shell</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #0d1117; --bar: #161b22; --border: #30363d;
  --text: #e6edf3; --green: #3fb950; --blue: #58a6ff;
  --red: #f85149; --yellow: #d29922; --gray: #8b949e;
  --term-bg: #010409;
}
html, body { height: 100%; background: var(--bg); color: var(--text);
  font-family: 'Segoe UI', system-ui, sans-serif; overflow: hidden; }

.topbar {
  height: 48px; background: var(--bar); border-bottom: 1px solid var(--border);
  display: flex; align-items: center; padding: 0 12px; gap: 10px;
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
}
.logo { font-size: 15px; font-weight: 700; color: var(--red);
  display: flex; align-items: center; gap: 6px; white-space: nowrap; }
.dot { width: 8px; height: 8px; border-radius: 50%;
  background: var(--green); flex-shrink: 0; animation: blink 2s infinite; }
.dot.off { background: var(--red); animation: none; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }
.stext { font-size: 12px; color: var(--gray); }
.root-badge {
  background: var(--red); color: #fff; font-size: 10px;
  font-weight: 700; padding: 2px 6px; border-radius: 4px; letter-spacing: 0.5px;
}
.spacer { flex: 1; }
.tbtn {
  background: #21262d; border: 1px solid var(--border); color: var(--text);
  padding: 5px 10px; border-radius: 6px; font-size: 12px; cursor: pointer;
  white-space: nowrap; -webkit-tap-highlight-color: transparent; touch-action: manipulation;
}
.tbtn:active { background: var(--border); }
.tbtn.red { border-color: var(--red); color: var(--red); }

.term-wrap {
  position: fixed; top: 48px; bottom: 88px; left: 0; right: 0;
  background: var(--term-bg); overflow-y: auto; overflow-x: hidden;
  -webkit-overflow-scrolling: touch; padding: 8px;
}
#output {
  font-family: 'Cascadia Code','Fira Code','Courier New',monospace;
  font-size: 13px; line-height: 1.5;
  white-space: pre-wrap; word-break: break-all; min-height: 100%;
}
@media(max-width:480px){ #output { font-size: 11px; } }

.f0{color:#010409} .f1{color:#f85149} .f2{color:#3fb950} .f3{color:#e3b341}
.f4{color:#58a6ff} .f5{color:#bc8cff} .f6{color:#39c5cf} .f7{color:#e6edf3}
.f8{color:#6e7681} .f9{color:#f85149} .f10{color:#56d364} .f11{color:#e3b341}
.f12{color:#79c0ff} .f13{color:#d2a8ff} .f14{color:#56d8c8} .f15{color:#f0f6fc}
.bold{font-weight:bold} .dim{opacity:.5}

.qkbar {
  position: fixed; bottom: 44px; left: 0; right: 0; height: 44px;
  background: #0d1117; border-top: 1px solid var(--border);
  display: flex; overflow-x: auto; scrollbar-width: none;
  padding: 5px 6px; gap: 5px; z-index: 99;
  -webkit-overflow-scrolling: touch; align-items: center;
}
.qkbar::-webkit-scrollbar { display: none; }
.qk {
  background: #21262d; border: 1px solid var(--border); color: var(--text);
  padding: 4px 10px; border-radius: 5px; font-size: 12px; white-space: nowrap;
  cursor: pointer; flex-shrink: 0; font-family: monospace;
  -webkit-tap-highlight-color: transparent; touch-action: manipulation;
}
.qk:active { background: var(--border); }
.qk.ctrl { border-color: var(--red); color: var(--red); }
.qk.apt  { border-color: var(--yellow); color: var(--yellow); }

.bottombar {
  position: fixed; bottom: 0; left: 0; right: 0; height: 44px;
  background: var(--bar); border-top: 1px solid var(--border);
  display: flex; align-items: center; padding: 0 8px; gap: 6px; z-index: 100;
}
#cmd {
  flex: 1; background: #21262d; border: 1px solid var(--border); color: var(--text);
  padding: 8px 10px; border-radius: 8px;
  font-family: 'Cascadia Code','Fira Code',monospace; font-size: 13px;
  outline: none; -webkit-appearance: none; min-width: 0;
}
#cmd:focus { border-color: var(--red); }
.sbtn {
  background: var(--red); border: none; color: #fff; width: 36px; height: 36px;
  border-radius: 8px; font-size: 18px; cursor: pointer;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  -webkit-tap-highlight-color: transparent; touch-action: manipulation;
}
.sbtn:active { opacity: .7; }

#file-input { display: none; }

.overlay {
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,.75); z-index: 200;
  align-items: center; justify-content: center;
}
.overlay.show { display: flex; }
.card {
  background: var(--bar); border: 1px solid var(--border);
  border-radius: 12px; padding: 24px; width: min(88vw,320px); text-align: center;
}
.card h3 { font-size: 16px; margin-bottom: 10px; }
.card p  { font-size: 13px; color: var(--gray); margin-bottom: 18px; }
.card button {
  background: var(--red); border: none; color: #fff;
  padding: 9px 24px; border-radius: 8px; font-size: 14px;
  font-weight: 600; cursor: pointer; width: 100%;
}
</style>
</head>
<body>

<div class="topbar">
  <div class="logo">🖥️ MyServer</div>
  <span class="root-badge">ROOT</span>
  <div class="dot" id="dot"></div>
  <span class="stext" id="stext">Connecting...</span>
  <div class="spacer"></div>
  <button class="tbtn" onclick="doCtrl('l')">🗑️</button>
  <label class="tbtn" for="file-input">📁</label>
  <button class="tbtn red" onclick="reconnect()">↺</button>
</div>
<input type="file" id="file-input" onchange="uploadFile(this)"/>

<div class="term-wrap" id="tw"><div id="output"></div></div>

<div class="qkbar">
  <span class="qk ctrl" onclick="doCtrl('c')">Ctrl+C</span>
  <span class="qk ctrl" onclick="doCtrl('d')">Ctrl+D</span>
  <span class="qk ctrl" onclick="doCtrl('z')">Ctrl+Z</span>
  <span class="qk ctrl" onclick="doCtrl('l')">Clear</span>
  <span class="qk" onclick="doCtrl('tab')">TAB</span>
  <span class="qk" onclick="doHist(1)">▲</span>
  <span class="qk" onclick="doHist(-1)">▼</span>
  <span class="qk" onclick="run('ls -la')">ls</span>
  <span class="qk" onclick="run('pwd')">pwd</span>
  <span class="qk" onclick="run('cd ~')">cd ~</span>
  <span class="qk" onclick="run('cd ..')">cd ..</span>
  <span class="qk apt" onclick="type('apt install -y ')">apt install</span>
  <span class="qk apt" onclick="run('apt update')">apt update</span>
  <span class="qk apt" onclick="type('apt remove -y ')">apt remove</span>
  <span class="qk" onclick="type('python3 ')">python3</span>
  <span class="qk" onclick="type('pip install ')">pip</span>
  <span class="qk" onclick="type('nano ')">nano</span>
  <span class="qk" onclick="type('cat ')">cat</span>
  <span class="qk" onclick="type('chmod +x ')">chmod</span>
  <span class="qk" onclick="run('whoami')">whoami</span>
  <span class="qk" onclick="run('df -h')">disk</span>
  <span class="qk" onclick="run('free -h')">RAM</span>
  <span class="qk" onclick="run('ps aux')">ps</span>
  <span class="qk" onclick="type('kill ')">kill</span>
  <span class="qk" onclick="type('| ')">|</span>
  <span class="qk" onclick="type('> ')">></span>
  <span class="qk" onclick="type('&& ')">&&</span>
</div>

<div class="bottombar">
  <input id="cmd" type="text" placeholder="Enter command..."
    autocomplete="off" autocorrect="off" autocapitalize="none" spellcheck="false"
    onkeydown="onKey(event)"/>
  <button class="sbtn" onclick="send()">➤</button>
</div>

<div class="overlay" id="ov">
  <div class="card">
    <h3>🔌 Disconnected</h3>
    <p>Lost connection to server.<br/>Click to reconnect.</p>
    <button onclick="reconnect();closeOv()">↺ Reconnect</button>
  </div>
</div>

<script>
let ws=null, hist=[], histIdx=-1, alive=false;
const out=document.getElementById('output');
const tw=document.getElementById('tw');
const inp=document.getElementById('cmd');
const dot=document.getElementById('dot');
const stxt=document.getElementById('stext');

// ─── ANSI PARSER ───────────────────────────────
function ansi(str){
  str=str.replace(/\\r\\n/g,'\\n').replace(/\\r/g,'\\n');
  let html='',bold=false,dim=false,fg=-1;
  const cls=()=>(bold||dim||fg>=0)?'</span>':'';
  const opn=()=>{
    const c=[];
    if(bold)c.push('bold');if(dim)c.push('dim');if(fg>=0)c.push('f'+fg);
    return c.length?'<span class="'+c.join(' ')+'">':'';
  };
  let i=0;
  while(i<str.length){
    if(str[i]==='\\x1b'&&str[i+1]==='['){
      let j=i+2;
      while(j<str.length&&!/[A-Za-z]/.test(str[j]))j++;
      const fin=str[j],seq=str.slice(i+2,j);
      i=j+1;
      if(fin==='m'){
        html+=cls();
        (seq||'0').split(';').forEach(s=>{
          const n=parseInt(s)||0;
          if(n===0){bold=dim=false;fg=-1;}
          else if(n===1)bold=true;
          else if(n===2)dim=true;
          else if(n===22){bold=false;dim=false;}
          else if(n>=30&&n<=37)fg=n-30;
          else if(n>=90&&n<=97)fg=n-82;
          else if(n===39)fg=-1;
        });
        html+=opn();
      }
    } else {
      const ch=str[i++];
      html+=ch==='&'?'&amp;':ch==='<'?'&lt;':ch==='>'?'&gt;':ch;
    }
  }
  html+=cls();
  return html;
}

function write(t){ out.innerHTML+=ansi(t); tw.scrollTop=tw.scrollHeight; }
function writeSys(m,c){ out.innerHTML+='<span style="color:'+c+';font-style:italic">'+m.replace(/</g,'&lt;')+'</span>\\n'; tw.scrollTop=tw.scrollHeight; }
function doCtrl(k){
  const m={c:'\\x03',d:'\\x04',z:'\\x1a',l:'\\x0c',tab:'\\x09',a:'\\x01',e:'\\x05',u:'\\x15',k:'\\x0b'};
  sendRaw(m[k]||k); inp.focus();
}

// ─── WS ────────────────────────────────────────
function setOk(m){dot.className='dot';stxt.textContent=m;alive=true;}
function setOff(m){dot.className='dot off';stxt.textContent=m;alive=false;}

function connect(){
  const p=location.protocol==='https:'?'wss:':'ws:';
  ws=new WebSocket(p+'//'+location.host+'/ws');
  ws.onopen=()=>{
    setOk('root@ubuntu · Connected');
    writeSys('\\n✅  Connected — Ubuntu Linux (ROOT)', '#3fb950');
    writeSys('🔴  You are ROOT — apt install, apt update, все команды работают!', '#f85149');
    writeSys('💡  Используй быстрые кнопки внизу\\n', '#8b949e');
    sendPkt({type:'resize',cols:Math.floor(tw.clientWidth/7.2)||100,rows:40});
  };
  ws.onmessage=e=>write(e.data);
  ws.onclose=()=>{
    setOff('Disconnected');
    if(alive) document.getElementById('ov').classList.add('show');
    alive=false;
  };
  ws.onerror=()=>setOff('Error');
}

function reconnect(){
  try{ws&&ws.close();}catch(e){}
  out.innerHTML=''; setOff('Reconnecting...');
  setTimeout(connect,500);
}
function closeOv(){document.getElementById('ov').classList.remove('show');}

function sendPkt(o){if(ws&&ws.readyState===WebSocket.OPEN)ws.send(JSON.stringify(o));}
function sendRaw(d){sendPkt({type:'input',data:d});}

function send(){
  const v=inp.value; if(!v.trim())return;
  hist.unshift(v); histIdx=-1;
  sendRaw(v+'\\n'); inp.value='';
}
function run(cmd){sendRaw(cmd+'\\n'); inp.focus();}
function type(txt){inp.value+=txt; inp.focus();}
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
    const m={c:'\\x03',d:'\\x04',z:'\\x1a',l:'\\x0c',a:'\\x01',e:'\\x05',u:'\\x15',k:'\\x0b'};
    if(m[k]){e.preventDefault();sendRaw(m[k]);}
  }
}

// ─── UPLOAD ────────────────────────────────────
async function uploadFile(input){
  const file=input.files[0];if(!file)return;
  writeSys('\\n📁 Uploading: '+file.name+' ...','#d29922');
  const fd=new FormData();fd.append('file',file);
  try{
    const r=await fetch('/upload',{method:'POST',body:fd});
    const d=await r.json();
    if(d.ok){writeSys('✅ Saved: '+d.path,'#3fb950');run('ls -lh "'+d.path+'"');}
    else writeSys('❌ '+d.error,'#f85149');
  }catch(e){writeSys('❌ Upload failed','#f85149');}
  input.value='';
}

// ─── MOBILE KEYBOARD ───────────────────────────
if(window.visualViewport){
  window.visualViewport.addEventListener('resize',()=>{
    const kb=window.innerHeight-window.visualViewport.height;
    const qk=document.querySelector('.qkbar');
    const bb=document.querySelector('.bottombar');
    if(kb>80){
      bb.style.bottom=kb+'px';
      qk.style.bottom=(kb+44)+'px';
      tw.style.bottom=(kb+88)+'px';
    } else {
      bb.style.bottom=qk.style.bottom=tw.style.bottom='';
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
            # Run bash as root in /root
            env = {
                'TERM': 'xterm-256color',
                'SHELL': '/bin/bash',
                'HOME': '/root',
                'USER': 'root',
                'LOGNAME': 'root',
                'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin',
                'LANG': 'en_US.UTF-8',
                'DEBIAN_FRONTEND': 'noninteractive',
                'PS1': r'\[\033[01;31m\]root@ubuntu\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]# ',
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
            await ws.send_str('\r\n\x1b[33m⟳  Shell restarted\x1b[0m\r\n')
            await asyncio.sleep(0.5)

    return ws

def main():
    app = web.Application(client_max_size=500 * 1024 * 1024)
    app.router.add_get('/', handle_index)
    app.router.add_get('/ws', handle_ws)
    app.router.add_post('/upload', handle_upload)
    port = int(os.environ.get('PORT', 8080))
    print(f'🚀 MyServer (ROOT) on :{port}')
    web.run_app(app, host='0.0.0.0', port=port, access_log=None)

if __name__ == '__main__':
    main()

