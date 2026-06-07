#!/usr/bin/env python3
import asyncio, os, pty, json, signal, struct, fcntl, termios
from aiohttp import web
import aiohttp

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover"/>
<title>Ubuntu</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css"/>
<script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
<script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
<script src="https://cdn.jsdelivr.net/npm/xterm-addon-web-links@0.9.0/lib/xterm-addon-web-links.js"></script>
<script src="https://cdn.jsdelivr.net/npm/xterm-addon-canvas@0.7.0/lib/xterm-addon-canvas.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/hack-font@3.3.0/build/web/hack.css"/>
<style>
/* ── RESET ── */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{
  width:100%;height:100%;
  background:#000;
  overflow:hidden;
  -webkit-text-size-adjust:100%;
  /* GPU acceleration for whole page */
  -webkit-transform:translateZ(0);
  transform:translateZ(0);
}

/* ── TOP BAR ── */
.topbar{
  position:fixed;top:0;left:0;right:0;
  /* safe area for notch phones */
  padding-top:env(safe-area-inset-top,0px);
  height:calc(38px + env(safe-area-inset-top,0px));
  background:#000;
  border-bottom:1px solid #1a1a1a;
  display:flex;align-items:flex-end;
  padding-left:10px;padding-right:10px;padding-bottom:6px;
  gap:8px;z-index:100;
  user-select:none;-webkit-user-select:none;
  /* GPU layer */
  will-change:transform;
  -webkit-transform:translateZ(0);transform:translateZ(0);
}
.tb-logo{
  font-size:15px;font-weight:700;
  color:#e95420; /* Ubuntu orange */
  font-family:'Hack','DejaVu Sans Mono',monospace;
  letter-spacing:.5px;
}
.tb-badge{
  font-size:10px;color:#444;font-family:'Hack',monospace;
  background:#0d0d0d;border:1px solid #1e1e1e;
  padding:1px 6px;border-radius:3px;
}
.tb-dot{
  width:6px;height:6px;border-radius:50%;
  background:#50fa7b;flex-shrink:0;
  animation:blink 2s infinite;
}
.tb-dot.off{background:#ff5555;animation:none}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.15}}
.tb-st{font-size:10px;color:#2a2a2a;font-family:'Hack',monospace;white-space:nowrap}
.tb-sp{flex:1}
.tb-btn{
  background:none;border:none;color:#333;font-size:16px;
  padding:2px 8px;cursor:pointer;border-radius:3px;line-height:1;
  -webkit-tap-highlight-color:transparent;touch-action:manipulation;
}
.tb-btn:active{background:#111;color:#aaa}

/* ── TERMINAL WRAPPER ── */
#tw{
  position:fixed;
  top:calc(38px + env(safe-area-inset-top,0px));
  bottom:90px;
  left:env(safe-area-inset-left,0px);
  right:env(safe-area-inset-right,0px);
  background:#000;overflow:hidden;
  /* critical for smooth scrolling */
  will-change:transform;
  -webkit-transform:translateZ(0);transform:translateZ(0);
  contain:strict;
}
/* xterm overrides for performance */
#tw .xterm{
  width:100%;height:100%;
  padding:3px 5px;
  /* GPU layer */
  will-change:transform;
  -webkit-transform:translateZ(0);transform:translateZ(0);
}
#tw .xterm-viewport{
  overflow-y:scroll!important;
  /* smooth momentum scrolling on iOS */
  -webkit-overflow-scrolling:touch;
  scroll-behavior:auto; /* NOT smooth — avoids jank */
  overscroll-behavior:contain;
  will-change:scroll-position;
}
#tw .xterm-screen{
  cursor:text;
  will-change:transform;
  -webkit-transform:translateZ(0);transform:translateZ(0);
}

/* ── EXTRA KEYS ── */
.xkeys{
  position:fixed;
  bottom:calc(46px + env(safe-area-inset-bottom,0px));
  left:0;right:0;height:44px;
  background:#000;border-top:1px solid #111;
  display:flex;overflow-x:auto;scrollbar-width:none;
  gap:3px;padding:5px 4px;z-index:99;
  -webkit-overflow-scrolling:touch;align-items:center;
  /* GPU */
  will-change:transform;
  -webkit-transform:translateZ(0);transform:translateZ(0);
}
.xkeys::-webkit-scrollbar{display:none}
.xk{
  background:#0d0d0d;border:1px solid #1c1c1c;color:#bbb;
  padding:4px 10px;border-radius:3px;font-size:12px;
  font-family:'Hack','DejaVu Sans Mono',monospace;
  white-space:nowrap;cursor:pointer;flex-shrink:0;
  -webkit-tap-highlight-color:transparent;touch-action:manipulation;
  min-width:34px;text-align:center;
  user-select:none;-webkit-user-select:none;
  /* instant tap response */
  -webkit-touch-callout:none;
}
.xk:active{background:#1e1e1e;color:#fff}

.xk.ctrl-btn{
  color:#8be9fd;border-color:#1a2a2a;font-weight:700;min-width:52px;
}
.xk.ctrl-btn.latched{
  background:#061a28;border-color:#8be9fd;color:#8be9fd;
  box-shadow:0 0 8px #8be9fd66;
  animation:cpulse 1s infinite;
}
@keyframes cpulse{0%,100%{box-shadow:0 0 5px #8be9fd33}50%{box-shadow:0 0 12px #8be9fd88}}

.xk.c{color:#8be9fd;border-color:#1a2a2a}
.xk.y{color:#f1fa8c;border-color:#2a2a1a}
.xk.g{color:#50fa7b;border-color:#1a2a1a}
.xk.p{color:#ff79c6;border-color:#2a1a2a}

/* ── ACTION BAR ── */
.abar{
  position:fixed;
  bottom:env(safe-area-inset-bottom,0px);
  left:0;right:0;
  height:calc(46px + env(safe-area-inset-bottom,0px));
  background:#000;border-top:1px solid #111;
  display:flex;gap:2px;
  padding:5px 4px;
  padding-bottom:calc(5px + env(safe-area-inset-bottom,0px));
  z-index:100;align-items:flex-start;
  will-change:transform;
  -webkit-transform:translateZ(0);transform:translateZ(0);
}
.ab{
  flex:1;background:#0d0d0d;border:1px solid #1a1a1a;color:#444;
  font-size:10px;padding:5px 1px;border-radius:3px;cursor:pointer;
  font-family:'Hack',monospace;text-align:center;
  -webkit-tap-highlight-color:transparent;touch-action:manipulation;
  user-select:none;-webkit-user-select:none;
}
.ab:active{background:#1a1a1a;color:#ccc}
.ab.r{color:#ff5555;border-color:#2a1111}
.ab.p{color:#ff79c6;border-color:#2a1a2a}

/* ── CTRL HINT ── */
#ctrl-hint{
  display:none;position:fixed;
  bottom:90px;left:0;right:0;
  background:#061a28;border-top:1px solid #8be9fd;border-bottom:1px solid #8be9fd;
  padding:5px 12px;z-index:150;
  font-family:'Hack',monospace;font-size:11px;color:#8be9fd;text-align:center;
  pointer-events:none;letter-spacing:.3px;
}
#ctrl-hint.show{display:block}

/* ── DISCONNECT OVERLAY ── */
.ov{
  display:none;position:fixed;inset:0;
  background:rgba(0,0,0,.92);z-index:300;
  align-items:center;justify-content:center;
}
.ov.show{display:flex}
.ov-box{
  background:#050505;border:1px solid #222;border-radius:6px;
  padding:28px 22px;text-align:center;font-family:'Hack',monospace;min-width:240px;
}
.ov-box h3{color:#e95420;font-size:14px;margin-bottom:8px}
.ov-box p{color:#333;font-size:11px;margin-bottom:18px;line-height:1.7}
.ov-box button{
  background:#050505;border:1px solid #e95420;color:#e95420;
  padding:9px 0;width:100%;border-radius:4px;font-size:12px;
  font-family:'Hack',monospace;cursor:pointer;
}
.ov-box button:active{background:#1a0a00}
</style>
</head>
<body>

<!-- TOP BAR -->
<div class="topbar">
  <span class="tb-logo">Ubuntu</span>
  <span class="tb-badge">[1] bash</span>
  <div class="tb-dot" id="dot"></div>
  <span class="tb-st" id="stext">connecting…</span>
  <div class="tb-sp"></div>
  <button class="tb-btn" onclick="sk('l')">✕</button>
  <button class="tb-btn" onclick="reconnect()">↺</button>
</div>

<!-- TERMINAL -->
<div id="tw"></div>

<!-- CTRL HINT -->
<div id="ctrl-hint">⌨ CTRL зажат — нажми букву на клавиатуре (ещё раз CTRL = отмена)</div>

<!-- EXTRA KEYS -->
<div class="xkeys">
  <span class="xk ctrl-btn" id="ctrl-btn" onclick="toggleCtrl()">CTRL</span>
  <span class="xk y" onclick="sr('\x1b[A')">▲</span>
  <span class="xk y" onclick="sr('\x1b[B')">▼</span>
  <span class="xk y" onclick="sr('\x1b[D')">◀</span>
  <span class="xk y" onclick="sr('\x1b[C')">▶</span>
  <span class="xk y" onclick="sr('\t')">TAB</span>
  <span class="xk y" onclick="sr('\x1b[3~')">DEL</span>
  <span class="xk y" onclick="sr('\x01')">HOME</span>
  <span class="xk y" onclick="sr('\x05')">END</span>
  <span class="xk c" onclick="sk('c')">^C</span>
  <span class="xk c" onclick="sk('d')">^D</span>
  <span class="xk c" onclick="sk('z')">^Z</span>
  <span class="xk" onclick="sr('| ')">|</span>
  <span class="xk" onclick="sr('> ')">&gt;</span>
  <span class="xk" onclick="sr('&amp;&amp; ')">&amp;&amp;</span>
  <span class="xk" onclick="sr(' ')">SPC</span>
  <span class="xk" onclick="sr('/')"> / </span>
  <span class="xk" onclick="sr('~')"> ~ </span>
  <span class="xk" onclick="sr('-')"> - </span>
  <span class="xk" onclick="sr('.')"> . </span>
  <span class="xk" onclick="sr('_')"> _ </span>
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
  <span class="xk"  onclick="sr('apt install -y ')">apt install</span>
  <span class="xk"  onclick="sr('python3 ')">python3</span>
  <span class="xk"  onclick="sr('pip install ')">pip</span>
  <span class="xk"  onclick="sr('nano ')">nano</span>
  <span class="xk"  onclick="sr('vim ')">vim</span>
  <span class="xk"  onclick="sr('cat ')">cat</span>
  <span class="xk"  onclick="sr('chmod +x ')">chmod</span>
  <span class="xk"  onclick="sr('kill ')">kill</span>
  <span class="xk"  onclick="sr('screen -r ')">screen</span>
  <span class="xk p" onclick="sl('help')">HELP</span>
</div>

<!-- ACTION BAR -->
<div class="abar">
  <button class="ab" onclick="sl('ls -la')">FILES</button>
  <button class="ab" onclick="sl('screen -ls')">SCREEN</button>
  <button class="ab" onclick="sl('df -h && free -h')">SYS</button>
  <button class="ab" onclick="sl('autorun list 2>/dev/null || echo нет')">AUTO</button>
  <button class="ab" onclick="sl('ip a 2>/dev/null | grep inet || ifconfig')">NET</button>
  <button class="ab r" onclick="sk('c')">KILL</button>
</div>

<!-- DISCONNECT -->
<div class="ov" id="ov">
  <div class="ov-box">
    <h3>Ubuntu — disconnected</h3>
    <p>Соединение потеряно.<br/>Сервер может перезапускаться…</p>
    <button onclick="reconnect();closeOv()">↺ Переподключиться</button>
  </div>
</div>

<script>
'use strict';
let ws=null, term=null, fit=null, canvasAddon=null, alive=false;
let ctrlLatched=false;

const dot     = document.getElementById('dot');
const stxt    = document.getElementById('stext');
const ctrlBtn = document.getElementById('ctrl-btn');
const ctrlHint= document.getElementById('ctrl-hint');
const tw      = document.getElementById('tw');

function setOk(m) { dot.className='tb-dot';     stxt.textContent=m; alive=true;  }
function setOff(m){ dot.className='tb-dot off'; stxt.textContent=m; alive=false; }

/* ── CTRL LATCH ── */
function setCtrlLatched(on){
  ctrlLatched=on;
  if(on){
    ctrlBtn.classList.add('latched');
    ctrlHint.classList.add('show');
    tw.style.bottom='112px';
  } else {
    ctrlBtn.classList.remove('latched');
    ctrlHint.classList.remove('show');
    tw.style.bottom='';
    setTimeout(doResize,60);
  }
}
function toggleCtrl(){
  setCtrlLatched(!ctrlLatched);
  term&&term.focus();
}

/* ── ADAPTIVE FONT SIZE ── */
function calcFontSize(){
  const w=window.innerWidth;
  // phone portrait ~360-430px → 12px
  // tablet 768+    → 14px
  // desktop 1200+  → 15px
  if(w<400)  return 12;
  if(w<600)  return 13;
  if(w<900)  return 14;
  return 15;
}

/* ── INIT XTERM ── */
function initTerm(){
  if(term){ try{term.dispose()}catch(e){} term=null; }

  term=new Terminal({
    theme:{
      background:'#000000', foreground:'#f8f8f2',
      cursor:'#e95420',     cursorAccent:'#000000',  /* Ubuntu orange cursor */
      selectionBackground:'#44475a99',
      black:'#000000',   red:'#ff5555',
      green:'#50fa7b',   yellow:'#f1fa8c',
      blue:'#6272a4',    magenta:'#ff79c6',
      cyan:'#8be9fd',    white:'#bfbfbf',
      brightBlack:'#4d4d4d', brightRed:'#ff6e6e',
      brightGreen:'#69ff94', brightYellow:'#ffffa5',
      brightBlue:'#d6acff',  brightMagenta:'#ff92df',
      brightCyan:'#a4ffff',  brightWhite:'#ffffff',
    },
    fontFamily:"'Hack','DejaVu Sans Mono','Courier New',monospace",
    fontSize: calcFontSize(),
    lineHeight: 1.15,
    letterSpacing: 0,
    cursorBlink: true,
    cursorStyle: 'block',
    scrollback: 5000,          /* меньше буфер → быстрее */
    fastScrollModifier: 'alt',
    fastScrollSensitivity: 10,
    allowTransparency: false,
    convertEol: false,
    disableStdin: false,
    allowProposedApi: true,
    /* GPU accelerated renderer */
    rendererType: 'canvas',    /* canvas быстрее WebGL на мобилах */
    windowsMode: false,
    drawBoldTextInBrightColors: true,
    minimumContrastRatio: 1,
    overviewRulerWidth: 0,     /* отключаем ruler → меньше работы */
  });

  fit=new FitAddon.FitAddon();
  term.loadAddon(fit);

  /* Canvas renderer addon — ускоряет рендеринг */
  try {
    canvasAddon=new CanvasAddon.CanvasAddon();
    term.loadAddon(canvasAddon);
  } catch(e) {}

  try { term.loadAddon(new WebLinksAddon.WebLinksAddon()); } catch(e) {}

  term.open(tw);
  doResize();
  term.focus();

  /* ── KEY HANDLER ── */
  term.onData(data=>{
    if(ctrlLatched){
      let out=data;
      if(data.length===1){
        const c=data.charCodeAt(0);
        if(c>=65&&c<=90)       out=String.fromCharCode(c-64);
        else if(c>=97&&c<=122) out=String.fromCharCode(c-96);
      }
      setCtrlLatched(false);
      sr(out);
      return;
    }
    if(ws&&ws.readyState===WebSocket.OPEN)
      ws.send(JSON.stringify({type:'input',data}));
  });

  term.onResize(({cols,rows})=>{
    if(ws&&ws.readyState===WebSocket.OPEN)
      ws.send(JSON.stringify({type:'resize',cols,rows}));
  });
}

/* ── WEBSOCKET ── */
function connect(){
  const proto=location.protocol==='https:'?'wss:':'ws:';
  ws=new WebSocket(proto+'//'+location.host+'/ws');

  ws.onopen=()=>{
    setOk('root@ubuntu');
    term.focus();
    setTimeout(()=>{ doResize(); term.focus(); },300);
  };

  /* Batch writes — flush every animation frame for smooth output */
  let buf='', rafId=0;
  function flush(){
    if(buf){ term.write(buf); buf=''; }
    rafId=0;
  }
  ws.onmessage=e=>{
    buf+=e.data;
    if(!rafId) rafId=requestAnimationFrame(flush);
  };

  ws.onclose=()=>{
    setOff('disconnected');
    if(alive){
      term.write('\r\n\x1b[31m[!] соединение потеряно\x1b[0m\r\n');
      document.getElementById('ov').classList.add('show');
    }
    alive=false;
  };
  ws.onerror=()=>setOff('error');
}

function reconnect(){
  try{ws&&ws.close()}catch(e){}
  setCtrlLatched(false);
  setOff('reconnecting…');
  setTimeout(()=>{ initTerm(); connect(); },600);
}
function closeOv(){ document.getElementById('ov').classList.remove('show'); }

/* ── SEND HELPERS ── */
function sr(data){
  if(ws&&ws.readyState===WebSocket.OPEN)
    ws.send(JSON.stringify({type:'input',data}));
  term&&term.focus();
}
function sl(cmd){ sr(cmd+'\n'); }
function sk(key){
  const m={c:'\x03',d:'\x04',z:'\x1a',l:'\x0c',a:'\x01',e:'\x05',u:'\x15',k:'\x0b'};
  sr(m[key]||key);
}

/* ── RESIZE — throttled ── */
let resizeTimer=0;
function doResize(){
  clearTimeout(resizeTimer);
  resizeTimer=setTimeout(()=>{
    try{
      fit.fit();
      if(ws&&ws.readyState===WebSocket.OPEN)
        ws.send(JSON.stringify({type:'resize',cols:term.cols,rows:term.rows}));
    }catch(e){}
  },80);
}

window.addEventListener('resize',()=>{
  /* Also update font size on orientation change */
  if(term) term.options.fontSize=calcFontSize();
  doResize();
});

/* Mobile keyboard handling */
if(window.visualViewport){
  let vpTimer=0;
  window.visualViewport.addEventListener('resize',()=>{
    clearTimeout(vpTimer);
    vpTimer=setTimeout(()=>{
      const kb=window.innerHeight-window.visualViewport.height;
      const xk=document.querySelector('.xkeys');
      const ab=document.querySelector('.abar');
      const ch=document.getElementById('ctrl-hint');
      const safeBot=parseInt(
        getComputedStyle(document.documentElement)
          .getPropertyValue('--sab') || '0'
      )||0;

      if(kb>100){
        ab.style.bottom  = kb+'px';
        xk.style.bottom  = (kb+46)+'px';
        ch.style.bottom  = (kb+90)+'px';
        tw.style.bottom  = ctrlLatched?(kb+112)+'px':(kb+90)+'px';
      } else {
        ab.style.bottom=xk.style.bottom=ch.style.bottom='';
        tw.style.bottom=ctrlLatched?'112px':'';
      }
      doResize();
    },50);
  });
}

/* Keepalive */
setInterval(()=>{
  if(ws&&ws.readyState===WebSocket.OPEN)
    ws.send(JSON.stringify({type:'ping'}));
},20000);

/* ── BOOT ── */
initTerm();
connect();
</script>
</body>
</html>
"""

HELP_SCRIPT = r"""#!/bin/bash
echo ""
echo -e "\033[1;33m╔══════════════════════════════════════════════════════════╗\033[0m"
echo -e "\033[1;33m║         🖥️  Ubuntu WebShell — Справка                   ║\033[0m"
echo -e "\033[1;33m╚══════════════════════════════════════════════════════════╝\033[0m"
echo ""
echo -e "\033[1;32m▶ АВТОЗАПУСК ПРОЦЕССОВ\033[0m"
echo -e "\033[0;37m  Процессы в screen — живут даже после закрытия браузера.\033[0m"
echo -e "\033[0;37m  При перезапуске сервера стартуют автоматически.\033[0m"
echo ""
echo -e "\033[1;33m  Добавить процесс:\033[0m"
echo -e "    \033[0;36mautorun add \"python3 /root/workspace/bot.py\"\033[0m"
echo -e "    \033[0;36mautorun add \"node /root/workspace/app.js\"\033[0m"
echo -e "    \033[0;36mautorun add \"bash /root/workspace/script.sh\"\033[0m"
echo ""
echo -e "\033[1;33m  Список (🟢 работает / 🔴 остановлен):\033[0m"
echo -e "    \033[0;36mautorun list\033[0m"
echo ""
echo -e "\033[1;33m  Остановить / удалить / логи:\033[0m"
echo -e "    \033[0;36mautorun stop 1\033[0m"
echo -e "    \033[0;36mautorun remove 1\033[0m"
echo -e "    \033[0;36mautorun log 1\033[0m"
echo ""
echo -e "\033[1;32m▶ РАБОТА С SCREEN\033[0m"
echo -e "    \033[0;36mscreen -ls\033[0m               — все сессии"
echo -e "    \033[0;36mscreen -r ar_1\033[0m           — подключиться к процессу"
echo -e "    \033[0;36mCtrl+A → D\033[0m              — отключиться (не убивая)"
echo ""
echo -e "\033[1;32m▶ ФАЙЛЫ И СОХРАНЕНИЕ\033[0m"
echo -e "    \033[0;36m/root/workspace/\033[0m   — твоя папка (сохраняется)"
echo -e "    \033[0;36m/root/uploads/\033[0m     — загруженные файлы"
echo -e "    \033[0;36msave-state\033[0m         — сохранить вручную прямо сейчас"
echo -e "\033[0;37m  Автосохранение происходит каждые 10 минут.\033[0m"
echo ""
echo -e "\033[1;32m▶ УСТАНОВКА ПАКЕТОВ\033[0m"
echo -e "    \033[0;36mpip install aiogram requests flask\033[0m"
echo -e "    \033[0;36mapt install -y ffmpeg nmap\033[0m"
echo -e "\033[0;37m  Все пакеты запоминаются и восстанавливаются при перезапуске.\033[0m"
echo ""
echo -e "\033[1;32m▶ ПРИМЕР: ТЕЛЕГРАМ БОТ\033[0m"
echo -e "    \033[0;36mmkdir -p /root/workspace && nano /root/workspace/bot.py\033[0m"
echo -e "    \033[0;36mpip install aiogram\033[0m"
echo -e "    \033[0;36mautorun add \"python3 /root/workspace/bot.py\"\033[0m"
echo -e "    \033[0;37m# Бот запустится сразу и будет стартовать после каждого перезапуска\033[0m"
echo ""
echo -e "\033[1;32m▶ ПРИМЕР: NODE.JS СЕРВЕР\033[0m"
echo -e "    \033[0;36mcd /root/workspace && nano app.js\033[0m"
echo -e "    \033[0;36mautorun add \"node /root/workspace/app.js\"\033[0m"
echo ""
echo -e "\033[1;32m▶ СИСТЕМНЫЕ КОМАНДЫ\033[0m"
echo -e "    \033[0;36mdf -h\033[0m         — диск    \033[0;36mfree -h\033[0m  — RAM"
echo -e "    \033[0;36mps aux\033[0m        — процессы \033[0;36mhtop\033[0m    — монитор"
echo -e "    \033[0;36mip a\033[0m          — сеть     \033[0;36mkill PID\033[0m — убить"
echo -e "    \033[0;36muname -a\033[0m      — система"
echo ""
echo -e "\033[1;32m▶ ГОРЯЧИЕ КЛАВИШИ\033[0m"
echo -e "    \033[0;36mCTRL\033[0m (кнопка) — зажать, затем нажать букву на клавиатуре"
echo -e "    \033[0;36m^C\033[0m — стоп  \033[0;36m^D\033[0m — выход  \033[0;36m^Z\033[0m — пауза"
echo -e "    \033[0;36mTAB\033[0m — автодополнение  \033[0;36m▲▼\033[0m — история команд"
echo ""
echo -e "\033[1;33m══════════════════════════════════════════════════════════\033[0m"
echo -e "  Введи \033[0;36mhelp\033[0m в любой момент чтобы снова увидеть справку."
echo -e "\033[1;33m══════════════════════════════════════════════════════════\033[0m"
echo ""
"""

BASHRC_APPEND = """
# ── Ubuntu WebShell ──
export WORKSPACE=/root/workspace
alias ll='ls -la --color=auto'
alias la='ls -la --color=auto'
alias ..='cd ..'
alias cls='clear'

if [ -z "$TERMUX_WELCOMED" ]; then
  export TERMUX_WELCOMED=1
  echo ""
  echo -e "\\033[1;33m  Ubuntu WebShell готов!\\033[0m  Введи \\033[1;36mhelp\\033[0m для справки."
  echo ""
fi
"""

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
                if not chunk: break
                f.write(chunk)
        return web.json_response({'ok': True, 'path': fpath})
    except Exception as e:
        return web.json_response({'ok': False, 'error': str(e)})

async def handle_ws(request):
    ws = web.WebSocketResponse(max_msg_size=16*1024*1024, heartbeat=30)
    await ws.prepare(request)

    try:
        with open('/usr/local/bin/help', 'w') as f: f.write(HELP_SCRIPT)
        os.chmod('/usr/local/bin/help', 0o755)
    except: pass

    try:
        bashrc = '/root/.bashrc'
        existing = open(bashrc).read() if os.path.exists(bashrc) else ''
        if 'TERMUX_WELCOMED' not in existing:
            with open(bashrc, 'a') as f: f.write(BASHRC_APPEND)
    except: pass

    while True:
        pid, fd = pty.fork()
        if pid == 0:
            env = {
                'TERM':            'xterm-256color',
                'COLORTERM':       'truecolor',
                'SHELL':           '/bin/bash',
                'HOME':            '/root',
                'USER':            'root',
                'LOGNAME':         'root',
                'HOSTNAME':        'ubuntu',
                'PATH':            '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin',
                'LANG':            'en_US.UTF-8',
                'LC_ALL':          'en_US.UTF-8',
                'DEBIAN_FRONTEND': 'noninteractive',
                'PS1': r'\[\033[01;32m\]root@ubuntu\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ ',
            }
            try: os.chdir('/root')
            except: pass
            try:
                with open('/etc/hostname','w') as f: f.write('ubuntu\n')
            except: pass
            os.execvpe('/bin/bash', ['/bin/bash', '--login'], env)
            os._exit(1)

        loop = asyncio.get_event_loop()
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
        done = asyncio.Event()

        async def pty_reader():
            while True:
                try:
                    data = await loop.run_in_executor(None, lambda: os.read(fd, 8192))
                    if not data or ws.closed: break
                    await ws.send_str(data.decode('utf-8', errors='replace'))
                except OSError: break
            done.set()

        async def ws_reader():
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        pkt = json.loads(msg.data)
                        t = pkt.get('type','')
                        if t == 'input':
                            os.write(fd, pkt['data'].encode('utf-8'))
                        elif t == 'resize':
                            cols = max(10, int(pkt.get('cols', 80)))
                            rows = max(2,  int(pkt.get('rows', 24)))
                            fcntl.ioctl(fd, termios.TIOCSWINSZ,
                                        struct.pack('HHHH', rows, cols, 0, 0))
                        elif t == 'ping':
                            pass
                    except: pass
                elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                    break
            done.set()

        t1 = asyncio.ensure_future(pty_reader())
        t2 = asyncio.ensure_future(ws_reader())
        await done.wait()
        t1.cancel(); t2.cancel()
        try: os.kill(pid, signal.SIGKILL)
        except: pass
        try: os.waitpid(pid, 0)
        except: pass
        try: os.close(fd)
        except: pass

        if ws.closed: break
        await ws.send_str('\r\n\x1b[33m[shell restarted]\x1b[0m\r\n')
        await asyncio.sleep(0.3)
    return ws

def main():
    app = web.Application(client_max_size=512*1024*1024)
    app.router.add_get('/',        handle_index)
    app.router.add_get('/ws',      handle_ws)
    app.router.add_post('/upload', handle_upload)
    port = int(os.environ.get('PORT', 8080))
    print(f'[*] Ubuntu WebShell on :{port}')
    web.run_app(app, host='0.0.0.0', port=port, access_log=None)

if __name__ == '__main__':
    main()
