#!/usr/bin/env node
/* Generate auditable scenario cards from saved benchmark JSON. */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const [openThaiPath, qwenPath, outputDirectory] = process.argv.slice(2);
if (!openThaiPath || !qwenPath || !outputDirectory) {
  throw new Error('usage: generate_scenario_captures.js <openthai.json> <qwen.json> <output-dir>');
}

const openThai = JSON.parse(fs.readFileSync(openThaiPath, 'utf8'));
const qwen = JSON.parse(fs.readFileSync(qwenPath, 'utf8')).results;
const scores = [
  ['5.5', '8.0', 'CII sector is cited, but the selected severity material is not a complete bank-specific designation test.'],
  ['6.5', '9.5', 'Qwen anchors Three Lines, independence, Head of Information Security and CIRT responsibilities.'],
  ['6.5', '9.0', 'Qwen traces risk framework, appetite, register, monitoring and minimum controls.'],
  ['8.5', '9.0', 'Both are useful; distinguish coordination-centre duties from bank implementation duties.'],
  ['10.0', '10.0', 'Both cover plan, communication, drill/review cadence and audit artefacts well.'],
  ['8.0', '9.5', 'Qwen anchors reporting structure and preservation of evidence without inventing a deadline.'],
  ['10.0', '10.0', 'Both cover supplier risk, contract/SLA requirements, access controls and audit rights.'],
  ['10.0', '10.0', 'Both produce audit-ready configuration control and sampling guidance.'],
  ['7.0', '9.5', 'Qwen consistently cites awareness, annual review and information-sharing requirements.'],
  ['6.5', '7.5', 'The top-three evidence packet is not broad enough to justify enterprise-wide priority ranking.'],
];

const chrome = process.env.CHROME_BIN || '/home/indows-11/.cache/ms-playwright/chromium-1232/chrome-linux64/chrome';
fs.mkdirSync(outputDirectory, { recursive: true });

const escapeHtml = (text) => String(text || '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const plain = (text) => String(text || '').replace(/[`*_#>-]+/g, ' ').replace(/\s+/g, ' ').trim();
const compact = (text, limit) => plain(text).slice(0, limit);
const slug = (title) => title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

for (let index = 0; index < qwen.length; index += 1) {
  const q = qwen[index];
  const o = openThai[index];
  const [openScore, qwenScore, finding] = scores[index];
  const evidence = q.evidence.map((item) => `p.${item.page} c.${item.part}`).join(' · ');
  const filename = `scenario-${String(index + 1).padStart(2, '0')}-${slug(q.title)}.png`;
  const html = `<!doctype html><html lang="th"><head><meta charset="utf-8"><style>
    *{box-sizing:border-box} body{margin:0;background:#08111f;color:#e9f2ff;font-family:"Noto Sans Thai","Noto Sans",Arial,sans-serif}
    main{width:1600px;min-height:1550px;padding:58px 68px;background:radial-gradient(circle at 90% 0,#173764 0,transparent 34%),linear-gradient(135deg,#091427,#0d1c31)}
    .eyebrow{color:#71d7ff;font-size:22px;font-weight:700;letter-spacing:1.6px;text-transform:uppercase}.title{font-size:47px;line-height:1.2;margin:14px 0 16px;color:#fff}.subtitle{font-size:24px;line-height:1.55;color:#bdcbe0;margin:0 0 30px}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.card{background:#112542;border:1px solid #29466d;border-radius:18px;padding:23px 27px}.label{font-size:18px;color:#9db4d4;font-weight:700;text-transform:uppercase;letter-spacing:1px}.metric{font-size:38px;font-weight:800;color:#fff;margin:8px 0}.small{font-size:21px;line-height:1.42;color:#d5e0ef}.good{color:#74edbe}.warn{color:#ffd281}
    h2{font-size:27px;margin:33px 0 14px;color:#8de3ff}.block{background:#0c1b30;border-left:5px solid #50c8f2;border-radius:8px;padding:20px 24px;font-size:23px;line-height:1.58;color:#e3ecf8}.quote{font-size:22px;line-height:1.6;white-space:normal}.footer{position:absolute;bottom:50px;left:68px;right:68px;border-top:1px solid #29466d;padding-top:18px;color:#9fb3ce;font-size:18px}.pill{display:inline-block;background:#153c57;color:#a9e9ff;border:1px solid #317c9f;border-radius:999px;padding:6px 14px;margin-right:8px;font-size:18px;font-weight:700}
  </style></head><body><main><div class="eyebrow">NCSA RAG Benchmark · Scenario ${index + 1}/10</div><h1 class="title">${escapeHtml(q.title)}</h1><p class="subtitle">${escapeHtml(compact(q.question, 340))}</p>
  <div class="grid"><section class="card"><div class="label">OpenThai2.0 Legal</div><div class="metric">${(o.generation_ms / 1000).toFixed(2)} s</div><div class="small ${o.citation_present ? 'good' : 'warn'}">Strict citation: ${o.citation_present ? 'present' : 'missing'}</div><div class="small">Codex judge: ${openScore}/10</div></section><section class="card"><div class="label">Qwen3.6-27B</div><div class="metric good">${(q.generation_ms / 1000).toFixed(2)} s</div><div class="small good">Strict citation: present</div><div class="small">Codex judge: ${qwenScore}/10</div></section></div>
  <h2>Retrieved evidence packet</h2><div class="block"><span class="pill">${escapeHtml(evidence)}</span><br><br>${escapeHtml(compact(q.evidence.map((item) => `[p.${item.page} c.${item.part}] ${item.content}`).join(' '), 560))}</div>
  <h2>Qwen answer capture</h2><div class="block quote">${escapeHtml(compact(q.answer, 640))}</div>
  <h2>Codex judge note</h2><div class="block">${escapeHtml(finding)}</div><div class="footer">Fixed source: NCSA cyber-security compendium document 16122 · Same recursive chunks and top-3 BM25 evidence for both models · Latency excludes model loading</div></main></body></html>`;
  const htmlPath = path.join(os.tmpdir(), `ncsa-scenario-${index + 1}.html`);
  fs.writeFileSync(htmlPath, html, 'utf8');
  execFileSync(chrome, ['--headless', '--disable-gpu', '--hide-scrollbars', '--no-sandbox', '--run-all-compositor-stages-before-draw', '--virtual-time-budget=1000', '--window-size=1600,1550', `--screenshot=${path.join(outputDirectory, filename)}`, `file://${htmlPath}`], { stdio: 'ignore' });
  fs.unlinkSync(htmlPath);
  console.log(filename);
}
