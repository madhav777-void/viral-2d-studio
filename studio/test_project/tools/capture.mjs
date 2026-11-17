// Frame-exact capture through headless Chrome. No npm packages (Node 22+). Run from the project folder.
//   node tools/capture.mjs check                         boot, list shots + captions, report errors
//   node tools/capture.mjs cues                          write data/cues.json (the sound cues, for tools/mix.py)
//   node tools/capture.mjs sheet review/all.jpg [step=0.5] [cols=9]   contact sheet, a frame every `step` s, time-stamped
//   node tools/capture.mjs frames review/full "1.2,8.4"  full-size JPEGs of those times
//   node tools/capture.mjs board review/board.jpg [at=0.6]   STORYBOARD: one frame per shot (at 60% of it), labelled with
//                                                        the shot id: send it to the user for approval before the full render
//   node tools/capture.mjs video renders/out.mp4 [start end] [--draft]   the film (30 fps) with data/mix.wav if it exists
//   node tools/capture.mjs preview                       serve the project and print a URL to watch it in a browser
//   node tools/capture.mjs stylesheet ../style-sheet.png  render sheet.html (the style sheet, 1920x1080) to a PNG
//   WORKERS=n (video): parallel Chrome pages rendering chunks of the film (default: up to 4 with a GPU, 1 with SOFTWARE_GL; WORKERS=1 = one page)
// CHROME=/path/to/chrome overrides the browser.
import { spawn, spawnSync } from 'node:child_process';
import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const FPS = +(process.env.FPS || 30);
const CHROME = [process.env.CHROME, '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge', '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium',
  '/usr/bin/chromium-browser', '/snap/bin/chromium', 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe'].find((p) => p && fs.existsSync(p));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const args = process.argv.slice(2), flags = new Set(args.filter((a) => a.startsWith('--')));
const [mode, ...rest] = args.filter((a) => !a.startsWith('--'));
// "aspect": "16:9" in script.json renders a 1920x1080 film (default 9:16, 1080x1920)
let ASPECT = '9:16'; try { ASPECT = JSON.parse(fs.readFileSync(path.join(ROOT, 'script.json'), 'utf8')).aspect || '9:16'; } catch {}
const WIDE = ASPECT === '16:9', FW = WIDE ? 1920 : 1080, FH = WIDE ? 1080 : 1920;

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.otf': 'font/otf',
  '.ttf': 'font/ttf', '.woff2': 'font/woff2', '.wav': 'audio/wav', '.mp3': 'audio/mpeg', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.glb': 'model/gltf-binary', '.gltf': 'model/gltf+json', '.bin': 'application/octet-stream', '.webp': 'image/webp', '.m4a': 'audio/mp4' };
function serve(port = 0) {
  return new Promise((res) => {
    const srv = http.createServer((req, r) => {
      const u = decodeURIComponent(req.url.split('?')[0]), f = path.join(ROOT, u === '/' ? 'index.html' : u);
      if (!f.startsWith(ROOT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); r.end(); return; }
      r.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
      fs.createReadStream(f).pipe(r);
    });
    srv.listen(port, '127.0.0.1', () => res(srv));
  });
}

async function openPage(port, page = 'index.html', ready = 'window.OP ? (OP.bootError ? "ERR:" + OP.bootError : OP.ready) : false') {
  if (!CHROME) throw new Error('Chrome not found: install Google Chrome or set CHROME=/path/to/chrome');
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'fs-chrome-'));
  const chrome = spawn(CHROME, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${prof}`, '--no-first-run', '--no-default-browser-check',
    '--hide-scrollbars', `--window-size=${FW},${FH}`, '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', ...(process.env.SOFTWARE_GL ? ['--use-angle=swiftshader'] : []), ...(process.getuid?.() === 0 ? ['--no-sandbox'] : []), '--disable-background-timer-throttling', '--disable-renderer-backgrounding', 'about:blank'], { stdio: 'ignore' });
  let dbg;
  for (let i = 0; i < 200 && !dbg; i++) { try { dbg = fs.readFileSync(path.join(prof, 'DevToolsActivePort'), 'utf8').split('\n')[0].trim(); } catch { await sleep(100); } }
  if (!dbg) throw new Error('Chrome did not start');
  const r = await fetch(`http://127.0.0.1:${dbg}/json/new?${encodeURIComponent(`http://127.0.0.1:${port}/${page}?capture=1${process.env.QS || ''}`)}`, { method: 'PUT' });
  const target = await r.json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0; const pend = new Map(), logs = [];
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pend.has(m.id)) { const p = pend.get(m.id); pend.delete(m.id); m.error ? p.rej(new Error(m.error.message)) : p.res(m.result); }
    else if (m.method === 'Runtime.exceptionThrown') logs.push('EXCEPTION ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
    else if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') logs.push('ERROR ' + m.params.args.map((a) => a.value ?? a.description).join(' '));
  };
  const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pend.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async (expr) => { const x = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (x.exceptionDetails) throw new Error(x.exceptionDetails.exception?.description || x.exceptionDetails.text); return x.result.value; };
  await send('Runtime.enable');
  for (let i = 0; ; i++) {
    const st = await ev(ready).catch(() => false);
    if (st === true) break;
    if (typeof st === 'string') throw new Error('boot failed: ' + st + '\n' + logs.join('\n'));
    if (i > 1200) throw new Error('boot timeout\n' + logs.join('\n'));
    await sleep(100);
  }
  const close = () => { try { ws.close(); } catch {} chrome.kill('SIGKILL'); setTimeout(() => { try { fs.rmSync(prof, { recursive: true, force: true }); } catch {} }, 300); };
  return { ev, logs, close };
}
const jpg = (d) => Buffer.from(d.slice(d.indexOf(',') + 1), 'base64');
const FRAME = (t, q, label) => `(() => { const d = OP.frame(${t}, ${q}); ${label ? `const cv = document.getElementById('cv'), c = cv.getContext('2d'); c.setTransform(1,0,0,1,0,0); c.fillStyle = '#000'; c.fillRect(0, 0, 250, 86); c.fillStyle = '#fff'; c.font = '700 60px sans-serif'; c.textAlign = 'left'; c.textBaseline = 'alphabetic'; c.fillText('${(+t).toFixed(2)}', 14, 64); return cv.toDataURL('image/jpeg', ${q});` : 'return d;'} })()`;

const srv = await serve(mode === 'preview' ? 8765 : 0), port = srv.address().port;
if (mode === 'preview') { console.log(`open http://127.0.0.1:${port}/  (Ctrl+C to stop)`); }
else {
  const SHEET = mode === 'stylesheet';
  if (SHEET && !fs.existsSync(path.join(ROOT, 'sheet.html'))) { console.log('this style has no sheet.html: its style-sheet.png is a fixed image'); srv.close(); process.exit(0); }
  const P = SHEET ? await openPage(port, 'sheet.html', 'window.SHEET_ERR ? "ERR:" + window.SHEET_ERR : !!window.SHEET_READY') : await openPage(port);
  try {
    const dur = SHEET ? 0 : await P.ev('OP.duration()');
    if (SHEET) {
      const out = path.resolve(ROOT, rest[0] || '../style-sheet.png');
      const png = await P.ev("document.getElementById('cv').toDataURL('image/png')");
      fs.writeFileSync(out, Buffer.from(png.slice(png.indexOf(',') + 1), 'base64'));
      if (P.logs.length) console.log(P.logs.join('\n'));
      console.log(out);
    } else if (mode === 'check') {
      console.log(`duration ${dur.toFixed(2)} s`);
      for (const s of await P.ev('OP.shots()')) console.log(`${s.id.padEnd(5)} ${s.at.toFixed(2).padStart(6)} → ${s.end.toFixed(2).padStart(6)}  (${(s.end - s.at).toFixed(2)} s)  ${s.note}`);
      console.log('captions:'); for (const c of await P.ev('OP.captions()')) console.log(`  ${c.s.toFixed(2).padStart(6)}–${c.e.toFixed(2).padEnd(6)} ${c.text}`);
      let bad = 0; for (let t = 0; t < dur; t += 0.25) { try { await P.ev(`OP.draw(${t})`); } catch (e) { bad++; console.log(`ERROR at ${t.toFixed(2)}: ${e.message.split('\n')[0]}`); } }
      if (P.logs.length) console.log(P.logs.join('\n'));
      console.log(bad || P.logs.length ? 'CHECK FAILED' : 'CHECK OK');
    } else if (mode === 'cues') {
      const cues = await P.ev('OP.cues()');
      fs.mkdirSync(path.join(ROOT, 'data'), { recursive: true });
      fs.writeFileSync(path.join(ROOT, 'data/cues.json'), JSON.stringify({ duration: dur, cues }, null, 1));
      console.log(`data/cues.json: ${cues.length} cues, ${dur.toFixed(2)} s`);
    } else if (mode === 'frames') {
      const dir = path.resolve(ROOT, rest[0] || 'review/frames'); fs.mkdirSync(dir, { recursive: true });
      for (const t of (rest[1] || '0').split(',').map(Number)) { fs.writeFileSync(path.join(dir, `t${t.toFixed(2)}.jpg`), jpg(await P.ev(FRAME(t, 0.92)))); }
      console.log(dir);
    } else if (mode === 'sheet') {
      const out = path.resolve(ROOT, rest[0] || 'review/all.jpg'), step = +(rest[1] || 0.5), cols = +(rest[2] || 9);
      const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'fs-sheet-')); let n = 0;
      for (let t = step / 2; t < dur; t += step) fs.writeFileSync(path.join(tmp, `f${String(n++).padStart(4, '0')}.jpg`), jpg(await P.ev(FRAME(t, 0.8, true))));
      const rows = Math.ceil(n / cols); fs.mkdirSync(path.dirname(out), { recursive: true });
      const r = spawnSync('ffmpeg', ['-v', 'error', '-y', '-framerate', '1', '-i', path.join(tmp, 'f%04d.jpg'), '-vf', `scale=${WIDE ? '384:216' : '216:384'},tile=${cols}x${rows}:padding=4:color=black`, '-frames:v', '1', '-q:v', '3', out]);
      fs.rmSync(tmp, { recursive: true, force: true });
      if (r.status) throw new Error('ffmpeg: ' + r.stderr); console.log(`${out} (${n} frames, every ${step} s)`);
    } else if (mode === 'board') {
      const out = path.resolve(ROOT, rest[0] || 'review/board.jpg'), at = +(rest[1] || 0.6), shots = await P.ev('OP.shots()');
      const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'fs-board-'));
      for (const [n, s] of shots.entries()) {
        const t = s.at + (s.end - s.at) * at;
        const d = await P.ev(`(() => { OP.draw(${t}); const cv = document.getElementById('cv'), c = cv.getContext('2d'); c.setTransform(1,0,0,1,0,0); c.globalAlpha = 1;
          c.fillStyle = 'rgba(0,0,0,0.78)'; c.fillRect(0, 0, cv.width, 110); c.fillStyle = '#FFD43B'; c.font = '900 64px Inter, sans-serif'; c.textAlign = 'left'; c.textBaseline = 'middle';
          c.fillText(${JSON.stringify(s.id)} + '  ' + ${JSON.stringify(t.toFixed(1) + ' s')}, 30, 58); return cv.toDataURL('image/jpeg', 0.85); })()`);
        fs.writeFileSync(path.join(tmp, `f${String(n).padStart(4, '0')}.jpg`), jpg(d));
      }
      const cols = WIDE ? 3 : Math.min(5, shots.length), rows = Math.ceil(shots.length / cols); fs.mkdirSync(path.dirname(out), { recursive: true });
      const r = spawnSync('ffmpeg', ['-v', 'error', '-y', '-framerate', '1', '-i', path.join(tmp, 'f%04d.jpg'), '-vf', `scale=${WIDE ? '640:360' : '324:576'},tile=${cols}x${rows}:padding=6:color=black`, '-frames:v', '1', '-q:v', '3', out]);
      fs.rmSync(tmp, { recursive: true, force: true });
      if (r.status) throw new Error('ffmpeg: ' + r.stderr);
      for (const s of shots) console.log(`${s.id.padEnd(5)} ${s.note}`);
      console.log(`${out} (${shots.length} shots)`);
    } else if (mode === 'video') {
      // frames are a pure function of time, so the film is cut into WORKERS chunks rendered by parallel Chrome pages,
      // each into its own video segment, then joined without re-encoding and muxed with the audio mix.
      const out = path.resolve(ROOT, rest[0] || 'renders/video.mp4'); fs.mkdirSync(path.dirname(out), { recursive: true });
      const mix = path.join(ROOT, 'data/mix.wav'), hasMix = fs.existsSync(mix), a0 = rest[1] ? +rest[1] : 0, a1 = rest[2] ? Math.min(+rest[2], dur) : dur, n = Math.round((a1 - a0) * FPS);
      const draft = flags.has('--draft'), venc = ['-c:v', 'libx264', '-preset', draft ? 'ultrafast' : 'veryfast', '-crf', draft ? '28' : '18', '-pix_fmt', 'yuv420p', '-g', String(FPS * 2)];
      const auto = process.env.SOFTWARE_GL ? 1 : Math.max(1, Math.min(4, Math.floor(os.cpus().length / 2)));   // software GL already uses every core
      const NW = Math.max(1, Math.min(+(process.env.WORKERS || auto), Math.ceil(n / FPS)));
      const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'fs-seg-')), t0 = Date.now(), done = new Array(NW).fill(0);
      const progress = () => process.stdout.write(`\r${done.reduce((a, b) => a + b, 0)}/${n} frames · ${NW} worker${NW > 1 ? 's' : ''} · ${((Date.now() - t0) / 1000).toFixed(0)} s   `);
      const pages = [P]; try { for (let w = 1; w < NW; w++) pages.push(await openPage(port)); } catch (e) { console.log('\n(only ' + pages.length + ' worker(s) could start: ' + e.message.split('\n')[0] + ')'); }
      const W = pages.length, per = Math.ceil(n / W);
      await Promise.all(pages.map(async (pg, w) => {
        const i0 = w * per, i1 = Math.min(n, i0 + per); if (i0 >= i1) return;
        const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-', ...venc, '-an', path.join(tmp, `seg${w}.mp4`)], { stdio: ['pipe', 'inherit', 'inherit'] });
        for (let i = i0; i < i1; i++) {
          const b = jpg(await pg.ev(FRAME(a0 + i / FPS, draft ? 0.8 : 0.93)));
          if (!ff.stdin.write(b)) await new Promise((r) => ff.stdin.once('drain', r));
          done[w]++; if (done[w] % 25 === 0) progress();
        }
        ff.stdin.end(); await new Promise((r) => ff.on('close', r));
      }));
      pages.slice(1).forEach((pg) => pg.close());
      const segs = [...Array(W).keys()].map((w) => path.join(tmp, `seg${w}.mp4`)).filter((f) => fs.existsSync(f));
      fs.writeFileSync(path.join(tmp, 'list.txt'), segs.map((f) => `file '${f.replace(/'/g, "'\\''")}'`).join('\n'));
      await new Promise((res, rej) => spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', path.join(tmp, 'list.txt'),
        ...(hasMix ? ['-ss', String(a0), '-t', String(a1 - a0), '-i', mix] : ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo']), '-map', '0:v', '-map', '1:a',
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out], { stdio: 'inherit' }).on('close', (c) => (c ? rej(new Error('ffmpeg join failed')) : res())));
      fs.rmSync(tmp, { recursive: true, force: true });
      console.log(`\r${out} (${n} frames, ${W} worker${W > 1 ? 's' : ''}, ${hasMix ? 'with data/mix.wav' : 'SILENT: no data/mix.wav'}, ${((Date.now() - t0) / 1000).toFixed(0)} s)`);
    } else console.log('modes: check · cues · sheet · frames · video · preview · stylesheet');
  } finally { P.close(); srv.close(); }
}
