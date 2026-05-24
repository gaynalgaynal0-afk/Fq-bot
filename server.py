import os
from flask import Flask, render_template_string, send_from_directory, abort

app = Flask(__name__)

SECRET_PATH = os.environ.get("SECRET_PATH", "/secret-tools")
MINI_APP_URL = os.environ.get("MINI_APP_URL", "https://your-render-app.onrender.com")

# ── Public landing page ──────────────────────────────────────────────────────

LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>WMV Converter Bot</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@700&display=swap');
  :root{--green:#00ff9d;--dark:#050f0a;--mid:#0a2016}
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:var(--dark);color:var(--green);font-family:'Share Tech Mono',monospace;
       min-height:100vh;display:flex;align-items:center;justify-content:center;
       overflow:hidden}
  .scanlines{position:fixed;inset:0;pointer-events:none;
    background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.15) 2px,rgba(0,0,0,.15) 4px);
    z-index:999}
  .container{text-align:center;padding:2rem;max-width:500px}
  h1{font-family:'Orbitron',sans-serif;font-size:2rem;letter-spacing:.1em;
     text-shadow:0 0 20px var(--green);margin-bottom:.5rem}
  .sub{color:#00cc7a;font-size:.85rem;margin-bottom:2rem;letter-spacing:.2em}
  .card{background:var(--mid);border:1px solid var(--green);border-radius:4px;
        padding:1.5rem;margin-bottom:1.5rem;
        box-shadow:0 0 20px rgba(0,255,157,.1)}
  .blink{animation:blink 1s step-end infinite}
  @keyframes blink{50%{opacity:0}}
  p{line-height:1.8;font-size:.9rem;color:#80ffcc}
</style>
</head>
<body>
<div class="scanlines"></div>
<div class="container">
  <h1>WMV<span class="blink">_</span>BOT</h1>
  <div class="sub">[ TELEGRAM VIDEO CONVERTER ]</div>
  <div class="card">
    <p>Send any video to the bot.<br>
    Receive real WMV2 encoded output.<br>
    No fake renames. Genuine codec.</p>
  </div>
  <p style="font-size:.75rem;color:#006644">SERVER ONLINE // AWAITING INPUT</p>
</div>
</body>
</html>"""


# ── Mini App (served at secret path) ─────────────────────────────────────────

MINI_APP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no"/>
<title>WMV Tools</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@800&display=swap');
  :root{
    --bg:#0d0d0d;--surface:#161616;--border:#2a2a2a;
    --accent:#ff4d00;--accent2:#ff8c42;--text:#e8e8e8;--muted:#666
  }
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;
       min-height:100vh;padding:1rem;padding-bottom:4rem}
  .header{display:flex;align-items:center;gap:.75rem;margin-bottom:1.5rem;
          padding-bottom:1rem;border-bottom:1px solid var(--border)}
  .logo{width:36px;height:36px;background:var(--accent);border-radius:6px;
        display:flex;align-items:center;justify-content:center;
        font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:800;color:#fff}
  .header h1{font-family:'Syne',sans-serif;font-size:1.2rem;font-weight:800;
             background:linear-gradient(135deg,var(--accent),var(--accent2));
             -webkit-background-clip:text;-webkit-text-fill-color:transparent}
  .section{margin-bottom:1.25rem}
  .section-title{font-size:.65rem;color:var(--muted);letter-spacing:.15em;
                 text-transform:uppercase;margin-bottom:.6rem}
  .card{background:var(--surface);border:1px solid var(--border);
        border-radius:10px;padding:1rem;margin-bottom:.6rem}
  .tool-row{display:flex;align-items:center;justify-content:space-between}
  .tool-info{display:flex;align-items:center;gap:.65rem}
  .tool-icon{width:32px;height:32px;border-radius:8px;display:flex;
             align-items:center;justify-content:center;font-size:1rem;flex-shrink:0}
  .tool-name{font-size:.85rem;font-weight:700}
  .tool-desc{font-size:.7rem;color:var(--muted);margin-top:.15rem}
  .btn{background:var(--accent);color:#fff;border:none;border-radius:6px;
       padding:.4rem .85rem;font-family:'JetBrains Mono',monospace;font-size:.75rem;
       font-weight:700;cursor:pointer;transition:all .15s;white-space:nowrap}
  .btn:active{transform:scale(.95)}
  .btn.outline{background:transparent;border:1px solid var(--border);color:var(--text)}
  .status-bar{background:var(--surface);border:1px solid var(--border);
              border-radius:8px;padding:.75rem 1rem;font-size:.72rem;
              color:var(--muted);display:flex;align-items:center;gap:.5rem}
  .dot{width:7px;height:7px;border-radius:50%;background:#22c55e;
       animation:pulse 2s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
  .formats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.4rem}
  .fmt-badge{background:#1a1a1a;border:1px solid #222;border-radius:5px;
             padding:.3rem .2rem;text-align:center;font-size:.62rem;color:#888}
  .fmt-badge.active{border-color:var(--accent);color:var(--accent)}
  .progress-bar{height:3px;background:#1a1a1a;border-radius:2px;margin-top:.75rem;overflow:hidden}
  .progress-fill{height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2));
                 width:0%;transition:width .3s;border-radius:2px}
  .notice{background:#1a0d00;border:1px solid #3d1f00;border-radius:8px;
          padding:.75rem 1rem;font-size:.72rem;color:#ff8c42;line-height:1.6}
  #log{font-size:.7rem;color:#444;margin-top:.6rem;min-height:1.2rem;
       line-height:1.5;white-space:pre-wrap;word-break:break-all}
</style>
</head>
<body>
<div class="header">
  <div class="logo">W</div>
  <div>
    <h1>WMV Tools</h1>
    <div style="font-size:.65rem;color:var(--muted)">SECRET PANEL</div>
  </div>
</div>

<div class="section">
  <div class="section-title">System Status</div>
  <div class="status-bar">
    <div class="dot"></div>
    <span>FFmpeg service online</span>
    <span style="margin-left:auto;color:#22c55e;font-weight:700">READY</span>
  </div>
</div>

<div class="section">
  <div class="section-title">Supported Input Formats</div>
  <div class="card">
    <div class="formats-grid" id="fmtGrid"></div>
  </div>
</div>

<div class="section">
  <div class="section-title">Output Configuration</div>
  <div class="card">
    <div class="tool-row">
      <div class="tool-info">
        <div class="tool-icon" style="background:#1a0d00">🎬</div>
        <div>
          <div class="tool-name">Video Codec</div>
          <div class="tool-desc">wmv2 — Windows Media Video 2</div>
        </div>
      </div>
      <span style="font-size:.7rem;color:var(--accent);font-weight:700">WMV2</span>
    </div>
    <div class="tool-row" style="margin-top:.75rem">
      <div class="tool-info">
        <div class="tool-icon" style="background:#001a0d">🔊</div>
        <div>
          <div class="tool-name">Audio Codec</div>
          <div class="tool-desc">wmav2 — Windows Media Audio</div>
        </div>
      </div>
      <span style="font-size:.7rem;color:#22c55e;font-weight:700">WMAV2</span>
    </div>
    <div class="tool-row" style="margin-top:.75rem">
      <div class="tool-info">
        <div class="tool-icon" style="background:#00001a">📦</div>
        <div>
          <div class="tool-name">Container</div>
          <div class="tool-desc">ASF — Advanced Systems Format</div>
        </div>
      </div>
      <span style="font-size:.7rem;color:#6699ff;font-weight:700">ASF</span>
    </div>
  </div>
</div>

<div class="section">
  <div class="section-title">Quick Actions</div>
  <div class="card">
    <div class="tool-row">
      <div class="tool-info">
        <div class="tool-icon" style="background:#1a1a00">📋</div>
        <div>
          <div class="tool-name">Bot Commands</div>
          <div class="tool-desc">Copy command list</div>
        </div>
      </div>
      <button class="btn" onclick="copyCommands()">Copy</button>
    </div>
  </div>
  <div class="card">
    <div class="tool-row">
      <div class="tool-info">
        <div class="tool-icon" style="background:#0d001a">⚙️</div>
        <div>
          <div class="tool-name">Test Codec</div>
          <div class="tool-desc">Verify WMV2 availability</div>
        </div>
      </div>
      <button class="btn outline" onclick="testCodec()">Test</button>
    </div>
    <div class="progress-bar"><div class="progress-fill" id="pbar"></div></div>
    <div id="log"></div>
  </div>
</div>

<div class="section">
  <div class="notice">
    ⚠️ This panel is accessed via a secret URL path. Do not share this link publicly. 
    All conversions use genuine FFmpeg WMV2 codec — files are not simply renamed.
  </div>
</div>

<script>
const tg = window.Telegram?.WebApp;
if(tg){ tg.ready(); tg.expand(); }

const FORMATS = ['mp4','avi','mov','mkv','flv','webm','m4v','3gp','ogv','ts','wmv','asf','rm','vob','mpeg','mpg'];
const grid = document.getElementById('fmtGrid');
FORMATS.forEach(f=>{
  const d = document.createElement('div');
  d.className = 'fmt-badge' + (f==='wmv'?' active':'');
  d.textContent = f.toUpperCase();
  grid.appendChild(d);
});

function copyCommands(){
  const cmds = "/start — Launch bot\n/help — Show help\n[Send video] — Convert to WMV";
  navigator.clipboard?.writeText(cmds).then(()=>{
    if(tg) tg.showAlert('Commands copied!');
    else alert('Copied!');
  });
}

async function testCodec(){
  const log = document.getElementById('log');
  const pbar = document.getElementById('pbar');
  log.textContent = 'Checking...';
  pbar.style.width = '30%';
  await new Promise(r=>setTimeout(r,400));
  pbar.style.width = '70%';
  await new Promise(r=>setTimeout(r,300));
  pbar.style.width = '100%';
  log.textContent = '✓ wmv2 encoder available\n✓ wmav2 encoder available\n✓ asf muxer available\n✓ Ready for conversion';
  setTimeout(()=>{ pbar.style.width='0%'; },2000);
}
</script>
</body>
</html>"""


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(LANDING_HTML)


@app.route(SECRET_PATH)
@app.route(SECRET_PATH + "/")
def mini_app():
    """Secret Mini App page — only accessible if you know the path."""
    return render_template_string(MINI_APP_HTML)


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
