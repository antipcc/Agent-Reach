#!/usr/bin/env python3
"""生成「口述录入台」——把口头讲述的排故经历直接转成结构化案例。

与 build_demo.py 面向客户不同，本工具面向知识库拥有者自己：目标是把多年
经验以最低摩擦倒进库里。一次录音讲完一条，靠语音口令推进，不用碰键盘。

    python docs/heidelberg-kb/build_capture.py [-o 输出路径]

只依赖标准库。默认输出到 docs/heidelberg-kb/capture.html。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

KB_DIR = Path(__file__).parent


def load(name: str) -> dict[str, Any]:
    with open(KB_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


def build_payload() -> dict[str, Any]:
    machines = load("machines.json")
    submissions = load("submissions.json")
    cases = load("cases.json")
    return {
        "machines": machines["machines"],
        "controlSystems": {c["id"]: c for c in machines["control_systems"]},
        "categories": {c["id"]: c["name_zh"] for c in machines["categories"]},
        "checklist": submissions["review_checklist"],
        "fixableLevels": {f["id"]: f for f in cases["field_fixable_levels"]},
        "updated": submissions["updated"],
    }


TEMPLATE = r"""<title>口述录入台</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600&family=Noto+Sans+SC:wght@400;500;700&display=swap">
<style>
:root{
  --bg:#E9EAE7; --surface:#FFFFFF; --sunk:#F1F2EF; --line:#CFD2CC;
  --ink:#15181A; --ink-2:#555A5C; --ink-3:#878C8C;
  --rec:#B4291F; --rec-bg:#FAE6E3;
  --done:#0E5E48; --done-bg:#DFEDE7;
  --accent:#0B5F74; --accent-soft:#DCEAEF;
  --warn:#7C5300; --warn-bg:#F8EFD9;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#131618; --surface:#1C2022; --sunk:#171A1C; --line:#2E3336;
  --ink:#E9E8E4; --ink-2:#A4AAAC; --ink-3:#767B7D;
  --rec:#EE9F97; --rec-bg:#371A17;
  --done:#83C9AE; --done-bg:#122C24;
  --accent:#61B5CD; --accent-soft:#15303A;
  --warn:#E0BB78; --warn-bg:#2E2412;
}}
:root[data-theme="dark"]{
  --bg:#131618; --surface:#1C2022; --sunk:#171A1C; --line:#2E3336;
  --ink:#E9E8E4; --ink-2:#A4AAAC; --ink-3:#767B7D;
  --rec:#EE9F97; --rec-bg:#371A17;
  --done:#83C9AE; --done-bg:#122C24;
  --accent:#61B5CD; --accent-soft:#15303A;
  --warn:#E0BB78; --warn-bg:#2E2412;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif;
  font-size:16px;line-height:1.7;-webkit-font-smoothing:antialiased}
.lat{font-family:"IBM Plex Sans","Noto Sans SC",sans-serif}
.mono{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}
button{font:inherit;color:inherit;background:none;border:none;cursor:pointer}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.wrap{max-width:660px;margin:0 auto;padding:0 18px 40px}

header{position:sticky;top:0;z-index:10;background:var(--bg);border-bottom:1px solid var(--line)}
.hd{max-width:660px;margin:0 auto;padding:11px 18px;display:flex;align-items:center;
  justify-content:space-between;gap:12px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:9px}
.brand b{font-size:16px}
.brand .sub{font-size:10.5px;letter-spacing:.16em;color:var(--ink-3);font-weight:600}
.hstat{display:flex;gap:14px;align-items:center;font-size:12.5px;color:var(--ink-2)}
.hstat b{color:var(--ink);font-size:15px}
.bar{height:3px;background:var(--line);border-radius:2px;overflow:hidden;max-width:660px;margin:0 auto}
.bar i{display:block;height:100%;background:var(--accent);transition:width .25s}
@media (prefers-reduced-motion:reduce){.bar i{transition:none}}

.stepno{font-size:11px;letter-spacing:.18em;color:var(--ink-3);font-weight:700;
  margin:26px 0 8px;text-transform:uppercase}
h1.q{font-size:clamp(23px,5.5vw,30px);font-weight:700;line-height:1.35;margin:0 0 6px;text-wrap:balance}
.hint{font-size:14px;color:var(--ink-2);margin:0 0 18px;max-width:34em}

.pad{background:var(--surface);border:1px solid var(--line);border-radius:9px;
  padding:16px 18px;min-height:132px;font-size:18px;line-height:1.75;white-space:pre-wrap}
.pad.rec{border-color:var(--rec);box-shadow:0 0 0 3px var(--rec-bg)}
.pad .ph{color:var(--ink-3);font-size:16px}
.pad .im{color:var(--ink-3)}
textarea.pad{width:100%;font-family:inherit;resize:vertical;display:block}

.ctl{display:flex;gap:11px;align-items:center;margin-top:14px;flex-wrap:wrap}
.big{width:66px;height:66px;flex:none;border-radius:50%;background:var(--rec);color:#fff;
  font-size:13px;font-weight:700;line-height:1.2;display:flex;align-items:center;
  justify-content:center;border:none}
.big.off{background:var(--surface);color:var(--ink-2);border:1px solid var(--line)}
.big.on{animation:pulse 1.5s ease-out infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(180,41,31,.5)}70%{box-shadow:0 0 0 15px rgba(180,41,31,0)}100%{box-shadow:0 0 0 0 rgba(180,41,31,0)}}
@media (prefers-reduced-motion:reduce){.big.on{animation:none}}
.nav{display:flex;gap:9px;flex:1;flex-wrap:wrap}
.btn{padding:11px 20px;border-radius:7px;border:1px solid var(--line);font-size:15px;font-weight:500}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn.pri{background:var(--accent);border-color:var(--accent);color:#fff}
.btn.pri:hover{opacity:.9;color:#fff}
.btn.pri:disabled{background:var(--sunk);border-color:var(--line);color:var(--ink-3);cursor:not-allowed}
.btn.sm{padding:7px 13px;font-size:13.5px}

.cmds{margin-top:12px;font-size:12.5px;color:var(--ink-3);line-height:1.9}
.cmds kbd{font-family:"IBM Plex Mono",monospace;background:var(--sunk);border:1px solid var(--line);
  border-radius:4px;padding:1px 7px;font-size:12px;color:var(--ink-2);margin:0 2px}
.err{color:var(--rec);font-size:13.5px;margin-top:10px;line-height:1.6}

.opts{display:flex;flex-wrap:wrap;gap:8px;margin-top:4px}
.opt{padding:12px 18px;border:1px solid var(--line);border-radius:8px;background:var(--surface);
  font-size:16px;font-weight:500}
.opt:hover{border-color:var(--accent)}
.opt[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
.sel{width:100%;font:inherit;font-size:17px;padding:13px 14px;border:1px solid var(--line);
  border-radius:8px;background:var(--surface);color:var(--ink)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:11px}
.two label{display:block;font-size:13px;color:var(--ink-2);margin-bottom:4px}
.two input{width:100%;font:inherit;font-size:17px;padding:11px 13px;border:1px solid var(--line);
  border-radius:8px;background:var(--surface);color:var(--ink)}
.note{background:var(--sunk);border-radius:7px;padding:11px 14px;font-size:13.5px;
  color:var(--ink-2);margin-top:12px;line-height:1.65}

.rev{background:var(--surface);border:1px solid var(--line);border-radius:9px;overflow:hidden;margin-top:6px}
.rrow{display:flex;gap:12px;padding:12px 15px;border-top:1px solid var(--line);font-size:15px}
.rrow:first-child{border-top:none}
.rk{flex:none;width:82px;font-size:12.5px;color:var(--ink-3);padding-top:3px}
.rv{flex:1;min-width:0;white-space:pre-wrap;word-break:break-word}
.rv.empty{color:var(--ink-3)}
.rrow button{font-size:12.5px;color:var(--accent);flex:none;align-self:flex-start;padding-top:3px}

.qm{display:flex;align-items:center;gap:12px;margin:16px 0 6px}
.qm .ring{width:52px;height:52px;flex:none;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-size:15px;font-weight:700;border:3px solid var(--line)}
.qm .ring.good{border-color:var(--done);color:var(--done)}
.qm .ring.mid{border-color:var(--warn);color:var(--warn)}
.qm .ring.low{border-color:var(--rec);color:var(--rec)}
.qm .qt{font-size:14px;color:var(--ink-2);line-height:1.6}
.miss{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.miss span{font-size:12px;border:1px dashed var(--line);border-radius:4px;padding:3px 9px;color:var(--ink-2)}
.miss span.bad{border-color:var(--rec);border-style:solid;color:var(--rec)}

.batch{margin-top:26px;padding-top:18px;border-top:1px solid var(--line)}
.brow{display:flex;gap:11px;align-items:center;padding:10px 0;border-bottom:1px solid var(--line);font-size:14.5px}
.brow .n{font-size:12px;color:var(--ink-3);width:20px;flex:none}
.brow .t{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.brow .d{font-size:12px;color:var(--ink-3);flex:none}
.brow .x{color:var(--ink-3);font-size:16px;flex:none;padding:0 4px}
.brow .x:hover{color:var(--rec)}
.done-card{background:var(--done-bg);border:1px solid var(--done);border-radius:9px;
  padding:16px 18px;text-align:center;margin-top:6px}
.done-card .t{font-size:17px;font-weight:700;color:var(--done)}
.done-card .d{font-size:13.5px;color:var(--ink-2);margin-top:3px}
.foot{font-size:12.5px;color:var(--ink-3);margin-top:26px;padding-top:14px;
  border-top:1px solid var(--line);line-height:1.75}
[hidden]{display:none !important}
</style>

<header>
  <div class="hd">
    <div class="brand"><b>口述录入台</b><span class="sub lat">CASE CAPTURE</span></div>
    <div class="hstat">
      <span>本批 <b id="h-batch">0</b> 条</span>
      <span class="mono" id="h-timer">0:00</span>
    </div>
  </div>
  <div class="bar"><i id="h-bar" style="width:0%"></i></div>
</header>

<div class="wrap"><main id="view"></main></div>

<script>
const D = __DATA__;
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const VOICE = !!SR;
let rec = null, tick = null;

const STEPS = [
  { key:"machine",  type:"machine",  title:"哪台机器？",            hint:"选一次就记住，同一台机器的后续案例不用再选。" },
  { key:"title",    type:"voice",    title:"一句话说这是什么故障",  hint:"例：换季后首件套准漂移，中午自愈。" },
  { key:"category", type:"category", title:"归到哪个部位？",        hint:"" },
  { key:"symptom",  type:"voice",    title:"当时机器什么表现？",    hint:"客户或机长看到的现象。" },
  { key:"tried",    type:"voice",    title:"试过哪些没解决的？",    hint:"这是最值钱的部分——它替下一个人省掉同样的弯路，也是别人抄不走的东西。可以连着说几条。", optional:true },
  { key:"root",     type:"voice",    title:"最后查出来是什么原因？", hint:"为什么坏，而不是换了什么件。" },
  { key:"fix",      type:"voice",    title:"怎么解决的？",          hint:"尽量具体到部件、参数、工具。" },
  { key:"found",    type:"voice",    title:"你是怎么找到这个原因的？", hint:"真实的排查过程，包括走过的弯路。" },
  { key:"meta",     type:"meta",     title:"难度和耗时",            hint:"" }
];

const blank = () => ({ machine:"", csys:"", title:"", category:"", symptom:"", tried:"",
  root:"", fix:"", found:"", fixable:"onsite", etaLo:"", etaHi:"", unsafe:false });

const state = { i:0, d:blank(), batch:[], listening:false, hands:true,
  interim:"", err:"", started:null, elapsed:0, msg:"" };

const STORE = "hdb-capture-v1";
try {
  const s = JSON.parse(localStorage.getItem(STORE) || "{}");
  if (s.batch) state.batch = s.batch;
  if (s.machine) { state.d.machine = s.machine; state.d.csys = s.csys || ""; }
} catch (e) { /* 隐私模式下静默降级 */ }

function persist() {
  try { localStorage.setItem(STORE, JSON.stringify({
    batch: state.batch, machine: state.d.machine, csys: state.d.csys })); }
  catch (e) { /* 本地保存只是防丢失，失败不影响录入 */ }
}

const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g,
  c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
const machineById = id => D.machines.find(m => m.id === id);
const step = () => STEPS[state.i];

/* ── 语音口令：让整条案例可以不碰键盘讲完 ── */
const CMDS = [
  { re:/(下一步|下一题|下一个|说完了|完成了)/, act:"next" },
  { re:/(上一步|上一题|回上一个)/,           act:"back" },
  { re:/(重说|重来|说错了|清空)/,             act:"clear" },
  { re:/(跳过|不用了)/,                       act:"skip" }
];

function applyCommands(text) {
  for (const c of CMDS) {
    const m = text.match(c.re);
    if (m) return { text: text.replace(c.re, "").trim(), act: c.act };
  }
  return { text: text, act: null };
}

function startTimer() {
  if (tick) return;
  if (!state.started) state.started = Date.now() - state.elapsed * 1000;
  tick = setInterval(() => {
    state.elapsed = Math.floor((Date.now() - state.started) / 1000);
    const el = document.getElementById("h-timer");
    if (el) el.textContent = Math.floor(state.elapsed / 60) + ":" +
      String(state.elapsed % 60).padStart(2, "0");
  }, 1000);
}
function stopTimer() { if (tick) { clearInterval(tick); tick = null; } }

function stopVoice() {
  try { if (rec) { rec.onend = null; rec.abort(); } } catch (e) { /* 已停 */ }
  rec = null; state.listening = false; state.interim = "";
}

function startVoice() {
  if (!VOICE || state.listening) return;
  try {
    rec = new SR();
    rec.lang = "zh-CN";
    rec.continuous = true;      // 连续模式：长句和停顿都不会被切断
    rec.interimResults = true;
    rec.onstart = () => { state.listening = true; state.err = ""; startTimer(); render(); };
    rec.onresult = ev => {
      let interim = "", final = "";
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const r = ev.results[i];
        if (r.isFinal) final += r[0].transcript; else interim += r[0].transcript;
      }
      if (final) {
        const { text, act } = applyCommands(final);
        if (text) appendTo(step().key, text);
        state.interim = "";
        if (act === "next") { go(1); return; }
        if (act === "back") { go(-1); return; }
        if (act === "clear") { state.d[step().key] = ""; render(); return; }
        if (act === "skip") { go(1); return; }
        render();
      } else {
        state.interim = interim;
        const pad = document.getElementById("pad");
        if (pad) pad.innerHTML = padHTML();
      }
    };
    rec.onerror = ev => {
      state.listening = false;
      const map = { "not-allowed":"麦克风权限被拒绝。点地址栏权限图标允许后重试，或在新标签页单独打开本页。",
        "service-not-allowed":"当前环境不允许语音识别，请在新标签页单独打开本页。",
        "audio-capture":"没有检测到麦克风。", "no-speech":"", "network":"语音识别需要联网。",
        "aborted":"" };
      state.err = map[ev.error] === undefined ? ("语音出错：" + ev.error) : map[ev.error];
      render();
    };
    rec.onend = () => {
      // 连续模式下浏览器仍可能自行断开；免手模式下自动续上
      if (state.listening && state.hands && STEPS[state.i].type === "voice") {
        try { rec.start(); return; } catch (e) { /* 落到下面收尾 */ }
      }
      state.listening = false; render();
    };
    rec.start();
  } catch (e) {
    state.listening = false;
    state.err = "无法启动语音识别：" + ((e && e.message) || e);
    render();
  }
}

function appendTo(key, text) {
  const cur = state.d[key] || "";
  state.d[key] = key === "tried" && cur ? cur + "\n" + text : (cur ? cur + text : text);
}

function go(delta) {
  const next = state.i + delta;
  if (next < 0) return;
  if (next >= STEPS.length) { state.i = STEPS.length; stopVoice(); render(); return; }
  state.i = next;
  const t = STEPS[next].type;
  if (t !== "voice") stopVoice();
  else if (state.hands && VOICE && !state.listening) { render(); startVoice(); return; }
  render();
}

/* ── 质量自检：对自己人是提示，不是关卡；但安全项仍然硬拦 ── */
function quality() {
  const d = state.d, has = v => !!String(v || "").trim(), long = (v,n) => String(v||"").trim().length >= n;
  const m = machineById(d.machine);
  return {
    traceable: has(d.machine),
    root_cause: long(d.root, 10),
    actionable: long(d.fix, 10),
    generation_ok: !!m && (m.control_systems.length === 1 || has(d.csys)),
    safety_ok: !d.unsafe,
    original: long(d.found, 12),
    negative_results: has(d.tried)
  };
}

function padHTML() {
  const v = state.d[step().key] || "";
  if (!v && !state.interim) return `<span class="ph">${state.listening
    ? "正在听…直接说就行" : (VOICE ? "点下面的按钮开始说，或直接打字" : "请打字输入")}</span>`;
  return esc(v) + (state.interim ? `<span class="im">${esc(state.interim)}</span>` : "");
}

function viewStep() {
  const s = step();
  const d = state.d;
  const m = machineById(d.machine);

  let bodyHTML = "";
  if (s.type === "machine") {
    bodyHTML = `<select class="sel" id="in-machine">
        <option value="">— 选择机型 —</option>
        ${D.machines.map(x => `<option value="${x.id}" ${d.machine === x.id ? "selected" : ""}
          >${esc(x.name)}</option>`).join("")}
      </select>
      ${m && m.control_systems.length === 1
        ? `<div class="note">控制系统：<b>${esc(D.controlSystems[m.control_systems[0]].name_zh)}</b>（自动识别）</div>`
        : ""}
      ${m && m.control_systems.length > 1 ? `<div style="margin-top:11px">
        <div class="note" style="margin:0 0 9px">${esc(m.name)} 横跨两代，不同代的报警与板卡完全不同，必须指明是哪一代。</div>
        <div class="opts">${m.control_systems.map(c => `<button class="opt" data-csys="${c}"
          aria-pressed="${d.csys === c}">${esc(D.controlSystems[c].name_zh)}</button>`).join("")}</div>
      </div>` : ""}`;
  } else if (s.type === "category") {
    bodyHTML = `<div class="opts">${Object.entries(D.categories).map(([k, v]) =>
      `<button class="opt" data-cat="${k}" aria-pressed="${d.category === k}">${esc(v)}</button>`).join("")}</div>`;
  } else if (s.type === "meta") {
    bodyHTML = `<div class="opts">${Object.entries(D.fixableLevels).map(([k, v]) =>
        `<button class="opt" data-fix="${k}" aria-pressed="${d.fixable === k}">${esc(v.name_zh)}</button>`).join("")}</div>
      <div class="two" style="margin-top:14px">
        <div><label for="in-lo">耗时下限（分钟）</label><input id="in-lo" type="number" value="${esc(d.etaLo)}"></div>
        <div><label for="in-hi">耗时上限（分钟）</label><input id="in-hi" type="number" value="${esc(d.etaHi)}"></div>
      </div>
      <label class="note" style="display:flex;gap:10px;align-items:flex-start;cursor:pointer">
        <input type="checkbox" id="in-unsafe" ${d.unsafe ? "checked" : ""} style="width:18px;height:18px;margin-top:2px">
        <span>做法中包含短接或屏蔽安全装置。如实勾选——这类做法不会入库。</span></label>`;
  } else {
    bodyHTML = `<div class="pad ${state.listening ? "rec" : ""}" id="pad">${padHTML()}</div>
      ${VOICE ? "" : `<div class="note">本浏览器不支持语音识别，请直接打字。</div>`}
      <textarea class="pad" id="in-text" rows="3" style="margin-top:9px;font-size:15px;min-height:0"
        placeholder="需要修改就在这里改">${esc(d[s.key] || "")}</textarea>`;
  }

  const isVoice = s.type === "voice";
  const canNext = s.type === "machine"
    ? (!!m && (m.control_systems.length === 1 || !!d.csys))
    : s.type === "category" ? !!d.category : true;

  return `<div class="stepno lat">第 ${state.i + 1} / ${STEPS.length} 步${
      s.optional ? " · 可跳过" : ""}</div>
    <h1 class="q">${esc(s.title)}</h1>
    ${s.hint ? `<p class="hint">${esc(s.hint)}</p>` : ""}
    ${bodyHTML}
    <div class="ctl">
      ${isVoice && VOICE ? `<button class="big ${state.listening ? "on" : "off"}" data-mic="1"
        aria-pressed="${state.listening}">${state.listening ? "停止" : "按住说"}</button>` : ""}
      <div class="nav">
        ${state.i > 0 ? `<button class="btn" data-go="-1">上一步</button>` : ""}
        <button class="btn pri" data-go="1" ${canNext ? "" : "disabled"}>${
          state.i === STEPS.length - 1 ? "看一遍" : "下一步"}</button>
        ${s.optional ? `<button class="btn" data-go="1">跳过</button>` : ""}
      </div>
    </div>
    ${state.err ? `<div class="err">${esc(state.err)}</div>` : ""}
    ${isVoice && VOICE ? `<div class="cmds">不用碰屏幕，直接说：
      <kbd>下一步</kbd><kbd>上一步</kbd><kbd>重说</kbd>${s.optional ? "<kbd>跳过</kbd>" : ""}
      <br>连续模式已${state.hands ? "开启" : "关闭"}，
      <button class="btn sm" data-hands="1" style="padding:2px 9px">${state.hands ? "关闭" : "开启"}</button>
      开启后进入下一步会自动继续录音。</div>` : ""}`;
}

function viewReview() {
  const d = state.d, q = quality(), m = machineById(d.machine);
  const list = D.checklist;
  const okCount = list.filter(c => q[c.id]).length;
  const missing = list.filter(c => !q[c.id]);
  const ring = okCount >= 6 ? "good" : okCount >= 4 ? "mid" : "low";

  const row = (k, label, val) => `<div class="rrow"><span class="rk">${esc(label)}</span>
    <span class="rv ${val ? "" : "empty"}">${val ? esc(val) : "（空）"}</span>
    <button data-edit="${esc(k)}">改</button></div>`;

  return `<div class="stepno lat">复核 · 确认后加入本批</div>
    <h1 class="q">${esc(d.title || "（未填标题）")}</h1>
    <div class="qm">
      <div class="ring ${ring}">${okCount}/${list.length}</div>
      <div class="qt">${d.unsafe
        ? "<b style='color:var(--rec)'>含短接或屏蔽安全装置的做法，本条不会入库。</b>"
        : okCount >= 6 ? "质量达标，可直接入库。"
        : "还差几项。缺项不影响先存下来，但入库前需要补。"}</div>
    </div>
    ${missing.length ? `<div class="miss">${missing.map(c =>
      `<span class="${c.blocking ? "bad" : ""}">缺 ${esc(c.name_zh)}</span>`).join("")}</div>` : ""}

    <div class="rev" style="margin-top:16px">
      ${row("machine", "机型", m ? m.name + (d.csys ? " · " + D.controlSystems[d.csys].name_zh : "") : "")}
      ${row("title", "标题", d.title)}
      ${row("category", "部位", D.categories[d.category] || "")}
      ${row("symptom", "现象", d.symptom)}
      ${row("tried", "试过没用", d.tried)}
      ${row("root", "根因", d.root)}
      ${row("fix", "做法", d.fix)}
      ${row("found", "怎么发现", d.found)}
      ${row("meta", "难度耗时", (D.fixableLevels[d.fixable] || {}).name_zh +
        (d.etaLo && d.etaHi ? " · " + d.etaLo + "–" + d.etaHi + " 分钟" : ""))}
    </div>

    <div class="ctl">
      <div class="nav">
        <button class="btn pri" data-save="1">加入本批，录下一条</button>
        <button class="btn" data-go="-1">回去改</button>
        <button class="btn" data-discard="1">丢弃这条</button>
      </div>
    </div>
    <div class="note">用时 ${Math.floor(state.elapsed / 60)} 分 ${state.elapsed % 60} 秒。
      加入本批后机型会保留，下一条直接从标题开始说。</div>`;
}

function viewBatch() {
  if (!state.batch.length) return "";
  return `<div class="batch">
    <div class="stepno lat">本批 ${state.batch.length} 条 · 存在本机浏览器</div>
    ${state.batch.map((b, i) => `<div class="brow">
      <span class="n mono">${i + 1}</span>
      <span class="t">${esc(b.title_zh || "（无标题）")}</span>
      <span class="d">${esc((machineById(b.incident.machine) || {}).name || "")}</span>
      <button class="x" data-del="${i}" aria-label="删除">×</button></div>`).join("")}
    <div class="ctl"><div class="nav">
      <button class="btn pri" data-export="1">导出这 ${state.batch.length} 条</button>
      <button class="btn" data-clearbatch="1">清空本批</button>
    </div></div>
    ${state.msg ? `<div class="note">${esc(state.msg)}</div>` : ""}
  </div>`;
}

function render() {
  const v = document.getElementById("view");
  const atReview = state.i >= STEPS.length;
  v.innerHTML = (atReview ? viewReview() : viewStep()) + viewBatch();
  document.getElementById("h-batch").textContent = state.batch.length;
  document.getElementById("h-bar").style.width =
    Math.round((Math.min(state.i, STEPS.length) / STEPS.length) * 100) + "%";
}

function toRecord() {
  const d = state.d, m = machineById(d.machine);
  return {
    id: "sub-" + Date.now().toString(36),
    provenance: "field",
    status: quality().safety_ok && Object.values(quality()).filter(Boolean).length >= 6
      ? "pending" : "draft",
    submitted_at: new Date().toISOString().slice(0, 10),
    submitter: { handle: "", role: "", years: null },
    incident: {
      machine: d.machine,
      control_system: m ? (m.control_systems.length === 1 ? m.control_systems[0] : d.csys) : null,
      occurred_at: "", downtime_minutes: null
    },
    title_zh: d.title.trim(),
    category: d.category,
    symptom_zh: d.symptom.trim(),
    tried_zh: d.tried.split("\n").map(s => s.trim()).filter(Boolean),
    root_cause_zh: d.root.trim(),
    fix_zh: d.fix.trim(),
    parts_used: [],
    field_fixable: d.fixable,
    eta_minutes: [Number(d.etaLo) || 0, Number(d.etaHi) || 0],
    how_found_zh: d.found.trim(),
    confidence_proposed: "field_single",
    unsafe_flag: d.unsafe,
    capture_seconds: state.elapsed
  };
}

async function exportBatch() {
  const payload = JSON.stringify(state.batch, null, 2);
  const filename = "口述案例-" + new Date().toISOString().slice(0, 10) + "-" + state.batch.length + "条.json";
  try {
    const dl = await window.claude.use("downloads");
    if (dl) {
      await dl.save({ filename: filename, data: payload });
      state.msg = "已导出 " + filename + "。放进审核队列跑一遍 validate.py 即可并入。";
      render(); return;
    }
  } catch (e) {
    if (e && e.code === "declined") { state.msg = "已取消导出。"; render(); return; }
    if (e && e.code === "rate_limited") { state.msg = "上一个保存提示还没处理完，稍等再试。"; render(); return; }
  }
  try {
    await navigator.clipboard.writeText(payload);
    state.msg = "本环境无法直接保存文件，已复制到剪贴板，粘贴到文本文件另存为 .json。";
  } catch (e2) {
    state.msg = "本环境既不能保存文件也不能访问剪贴板，请换个浏览器或在新标签页打开。";
  }
  render();
}

document.addEventListener("click", e => {
  const t = e.target.closest("[data-mic],[data-go],[data-cat],[data-csys],[data-fix],[data-save],[data-discard],[data-edit],[data-del],[data-export],[data-clearbatch],[data-hands]");
  if (!t) return;
  const d = t.dataset;
  if (d.mic) { state.listening ? (stopVoice(), render()) : startVoice(); return; }
  if (d.hands) { state.hands = !state.hands; if (!state.hands) stopVoice(); render(); return; }
  if (d.go) { go(Number(d.go)); return; }
  if (d.cat) { state.d.category = d.cat; render(); return; }
  if (d.csys) { state.d.csys = d.csys; persist(); render(); return; }
  if (d.fix) { state.d.fixable = d.fix; render(); return; }
  if (d.edit) {
    const idx = STEPS.findIndex(s => s.key === d.edit);
    state.i = idx < 0 ? 0 : idx; stopVoice(); render(); return;
  }
  if (d.save) {
    state.batch.push(toRecord());
    const keepM = state.d.machine, keepC = state.d.csys;
    state.d = blank(); state.d.machine = keepM; state.d.csys = keepC;
    state.i = 1;                       // 机型已记住，直接从标题开始
    state.elapsed = 0; state.started = null; stopTimer();
    document.getElementById("h-timer").textContent = "0:00";
    state.msg = ""; persist(); render();
    if (state.hands && VOICE) startVoice();
    return;
  }
  if (d.discard) {
    const keepM = state.d.machine, keepC = state.d.csys;
    state.d = blank(); state.d.machine = keepM; state.d.csys = keepC;
    state.i = 1; state.elapsed = 0; state.started = null; stopTimer();
    document.getElementById("h-timer").textContent = "0:00";
    render(); return;
  }
  if (d.del) { state.batch.splice(Number(d.del), 1); persist(); render(); return; }
  if (d.export) { exportBatch(); return; }
  if (d.clearbatch) { state.batch = []; state.msg = ""; persist(); render(); return; }
});

document.addEventListener("input", e => {
  if (e.target.id === "in-text") { state.d[step().key] = e.target.value; return; }
  if (e.target.id === "in-lo") { state.d.etaLo = e.target.value; return; }
  if (e.target.id === "in-hi") { state.d.etaHi = e.target.value; return; }
});
document.addEventListener("change", e => {
  if (e.target.id === "in-machine") { state.d.machine = e.target.value; state.d.csys = ""; persist(); render(); }
  if (e.target.id === "in-unsafe") { state.d.unsafe = e.target.checked; render(); }
});

render();
</script>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--out", type=Path, default=KB_DIR / "capture.html")
    args = parser.parse_args()
    payload = json.dumps(build_payload(), ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c")
    args.out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")
    print(f"已生成 {args.out}（{args.out.stat().st_size / 1024:.1f} KB）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
