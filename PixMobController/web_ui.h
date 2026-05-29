#pragma once
#include <pgmspace.h>

const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PixMob Controller</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #1a1a2e; color: #eee; padding: 16px; min-height: 100vh;
  }
  h1 { text-align: center; font-size: 1.5em; margin-bottom: 4px; color: #e94560; }
  .subtitle { text-align: center; font-size: 0.85em; color: #888; margin-bottom: 20px; }
  .status {
    text-align: center; padding: 10px; background: #16213e; border-radius: 8px;
    margin-bottom: 20px; font-size: 0.9em; border: 1px solid #0f3460;
  }
  .status.ok { border-color: #2ecc71; }
  .status.sending { border-color: #f39c12; }
  h2 {
    font-size: 1.1em; color: #e94560; margin: 20px 0 10px; padding-bottom: 6px;
    border-bottom: 1px solid #0f3460;
  }
  .btn-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 8px;
  }
  .btn {
    padding: 14px 8px; border: none; border-radius: 8px; font-size: 0.85em;
    font-weight: 600; cursor: pointer; transition: transform 0.1s, opacity 0.2s;
    color: #fff; text-align: center;
  }
  .btn:active { transform: scale(0.95); }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
  .btn.system { background: #555; }
  .btn.gold { background: #d4a017; }
  .btn.red { background: #c0392b; }
  .btn.blue { background: #2980b9; }
  .btn.white { background: #7f8c8d; }
  .btn.other { background: #8e44ad; }
  .btn.sending { animation: pulse 0.8s ease-in-out infinite; }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
  .wake-note {
    text-align: center; font-size: 0.8em; color: #f39c12; margin-top: 16px;
    padding: 8px; background: #2c2c3e; border-radius: 6px;
  }
  .footer {
    text-align: center; font-size: 0.75em; color: #555; margin-top: 30px;
  }
</style>
</head>
<body>
<h1>PixMob Controller</h1>
<p class="subtitle">ESP32 + CC1101 &middot; 868 MHz</p>
<div class="status ok" id="status">Ready</div>

<h2>Wake Up</h2>
<div class="btn-grid">
  <button class="btn system" onclick="sendCmd('nothing',600)">Wake Up (~30s)</button>
  <button class="btn system" onclick="sendCmd('nothing',200)">Wake Up (~10s)</button>
</div>

<h2>Gold</h2>
<div class="btn-grid">
  <button class="btn gold" onclick="sendCmd('gold_fade_in',EFFECT_REPEATS)">Fade In</button>
  <button class="btn gold" onclick="sendCmd('gold_fast_fade',EFFECT_REPEATS)">Fast Fade</button>
  <button class="btn gold" onclick="sendCmd('wine_fade_in',EFFECT_REPEATS)">Fade In 2</button>
  <button class="btn gold" onclick="sendCmd('gold_blink',EFFECT_REPEATS)">Blink (Random)</button>
  <button class="btn gold" onclick="sendCmd('gold_fade',EFFECT_REPEATS)">Fade (Random)</button>
</div>

<h2>Red</h2>
<div class="btn-grid">
  <button class="btn red" onclick="sendCmd('white_fastfade2',EFFECT_REPEATS)">Fast Fade 2</button>
  <button class="btn red" onclick="sendCmd('red_fade',EFFECT_REPEATS)">Fade (Random)</button>
  <button class="btn red" onclick="sendCmd('red_fastblink',EFFECT_REPEATS)">Fast Blink (Random)</button>
  <button class="btn red" onclick="sendCmd('red_fastfade',EFFECT_REPEATS)">Fast Fade (Random)</button>
</div>

<h2>Blue</h2>
<div class="btn-grid">
  <button class="btn blue" onclick="sendCmd('blue_fade',EFFECT_REPEATS)">Fade (Random)</button>
</div>

<h2>White</h2>
<div class="btn-grid">
  <button class="btn white" onclick="sendCmd('white_blink',EFFECT_REPEATS)">Blink (Random)</button>
  <button class="btn white" onclick="sendCmd('white_fade',EFFECT_REPEATS)">Fade (Random)</button>
  <button class="btn white" onclick="sendCmd('white_fastfade',EFFECT_REPEATS)">Fast Fade (Random)</button>
  <button class="btn white" onclick="sendCmd('gold_fastfade',EFFECT_REPEATS)">Fast Fade 2 (Random)</button>
</div>

<h2>Other</h2>
<div class="btn-grid">
  <button class="btn other" onclick="sendCmd('turq_blink',EFFECT_REPEATS)">Turquoise Blink (Random)</button>
</div>

<p class="wake-note">Hold the bracelet close to the antenna. Each non-wake command now sends a short wake preamble first. Buttons marked Random are designed to light only a subset of bracelets.</p>
<p class="footer">PixMob IR/RF Reverse Engineering Project &middot; github.com/danielweidman</p>

<script>
let busy = false;
let queued = false;
const EFFECT_REPEATS = 12;

function setButtonsDisabled(disabled) {
  document.querySelectorAll('.btn').forEach(b => b.disabled = disabled);
}

function setStatus(text, sending) {
  const st = document.getElementById('status');
  st.className = sending ? 'status sending' : 'status ok';
  st.textContent = text;
}

async function refreshStatus() {
  try {
    const r = await fetch('/status', { cache: 'no-store' });
    if (!r.ok) return;
    const data = await r.json();
    const radioBusy = data.transmitting || data.pending;
    if (!radioBusy) {
      queued = false;
    }
    busy = queued || radioBusy;
    setButtonsDisabled(busy);
    setStatus(data.status || 'Ready', busy);
  } catch (_) {
    // Keep the current state if polling fails briefly.
  }
}

function sendCmd(cmd, repeats) {
  if (busy) return;
  queued = true;
  busy = true;
  setStatus('Queueing ' + cmd + '... (' + repeats + 'x)', true);
  setButtonsDisabled(true);
  fetch('/cmd?name=' + cmd + '&repeats=' + repeats)
    .then(async r => {
      const msg = await r.text();
      if (!r.ok) {
        throw new Error(msg || 'Busy transmitting');
      }
      return msg;
    })
    .then(msg => {
      setStatus(msg, true);
      refreshStatus();
    })
    .catch((err) => {
      queued = false;
      busy = false;
      setButtonsDisabled(false);
      setStatus(err.message || 'Error sending command', false);
    });
}

setInterval(refreshStatus, 250);
refreshStatus();
</script>
</body>
</html>
)rawliteral";
