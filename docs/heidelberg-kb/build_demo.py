#!/usr/bin/env python3
"""由知识库 JSON 生成可交互的单文件 HTML 原型。

数据与界面由此保持单一真值来源——改完 JSON 重跑一次即可，不会出现两边不一致：

    python docs/heidelberg-kb/build_demo.py [-o 输出路径]

只依赖标准库。默认输出到 docs/heidelberg-kb/demo.html。
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

KB_DIR = Path(__file__).parent

# 付费墙演示：这些案例在原型中显示为会员内容。真实产品应由后端鉴权决定，
# 前端标记仅用于演示商业模式的呈现方式。
PREMIUM_CASE_IDS = [
    "transfer-cam-roller",
    "quality-plate-wear",
    "dampening-chiller",
    "inking-roller-glazing",
    "delivery-uneven-stack",
    "delivery-powder-blockage",
]

# 纸路顺序：按纸张实际经过的工位排列，作为分类筛选条的排序依据。
PAPER_PATH = ["feeder", "register", "transfer", "unit", "dampening", "inking", "delivery"]
SYSTEM_GROUP = ["pneumatic", "drive", "electrical", "safety", "control", "lubrication", "quality"]


def load(name: str) -> dict[str, Any]:
    with open(KB_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


def build_payload() -> dict[str, Any]:
    sources = load("sources.json")
    machines = load("machines.json")
    fault_codes = load("fault-codes.json")
    cases = load("cases.json")
    maintenance = load("maintenance.json")
    synonyms = load("synonyms.json")
    submissions = load("submissions.json")

    for case in cases["entries"]:
        case["premium"] = case["id"] in PREMIUM_CASE_IDS

    return {
        "synonyms": synonyms,
        "sub": submissions,
        "sources": {s["id"]: s for s in sources["sources"]},
        "machines": machines["machines"],
        "controlSystems": {c["id"]: c for c in machines["control_systems"]},
        "categories": {c["id"]: c["name_zh"] for c in machines["categories"]},
        "confidenceLevels": {c["id"]: c for c in machines["confidence_levels"]},
        "fixableLevels": {f["id"]: f for f in cases["field_fixable_levels"]},
        "intervals": maintenance["intervals"],
        "faultCodes": fault_codes["entries"],
        "decodingRules": fault_codes["decoding_rules"],
        "cases": cases["entries"],
        "maintenance": maintenance["entries"],
        "wearParts": maintenance["wear_parts"],
        "lubeColors": maintenance["lubrication_color_code"],
        "paperPath": PAPER_PATH,
        "systemGroup": SYSTEM_GROUP,
        "updated": fault_codes["updated"],
    }


TEMPLATE = r"""<title>海德堡排故台</title>
__FONTS__
<style>
:root{
  --bg:#EEF0F0; --surface:#FFFFFF; --surface-2:#E4E7E7; --sunk:#E9ECEC;
  --ink:#171A1C; --ink-2:#535A5F; --ink-3:#848B90; --line:#D3D8D8;
  --accent:#0B6076; --accent-ink:#FFFFFF; --accent-soft:#DBEAEF;
  --stop:#A82A20; --stop-bg:#FAE7E4; --warn:#7E5504; --warn-bg:#F9EFD8;
  --ok:#17603A; --ok-bg:#DFEEE5; --mono-bg:#E8ECEC;
  --rail:#C6CCCC;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#121517; --surface:#1B1F21; --surface-2:#232829; --sunk:#171B1D;
    --ink:#E9E8E3; --ink-2:#A5ABAF; --ink-3:#787E83; --line:#2F3538;
    --accent:#63B7CE; --accent-ink:#0A1E26; --accent-soft:#16303A;
    --stop:#EFA098; --stop-bg:#361B18; --warn:#E2BC77; --warn-bg:#2F2513;
    --ok:#8CCCA5; --ok-bg:#152E1F; --mono-bg:#232A2C;
    --rail:#3A4144;
  }
}
:root[data-theme="dark"]{
  --bg:#121517; --surface:#1B1F21; --surface-2:#232829; --sunk:#171B1D;
  --ink:#E9E8E3; --ink-2:#A5ABAF; --ink-3:#787E83; --line:#2F3538;
  --accent:#63B7CE; --accent-ink:#0A1E26; --accent-soft:#16303A;
  --stop:#EFA098; --stop-bg:#361B18; --warn:#E2BC77; --warn-bg:#2F2513;
  --ok:#8CCCA5; --ok-bg:#152E1F; --mono-bg:#232A2C;
  --rail:#3A4144;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font-family:"Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif;
  font-size:15px; line-height:1.7; -webkit-font-smoothing:antialiased;
}
.lat{font-family:"Barlow Semi Condensed","Noto Sans SC",sans-serif}
.mono{font-family:"IBM Plex Mono",ui-monospace,monospace}
button{font:inherit;color:inherit;background:none;border:none;cursor:pointer}
a{color:var(--accent)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

.wrap{max-width:840px;margin:0 auto;padding:0 16px 72px}

/* ── 页眉 ───────────────────────────── */
header{position:sticky;top:0;z-index:20;background:var(--bg);border-bottom:1px solid var(--line)}
.hd{max-width:840px;margin:0 auto;padding:12px 16px 0}
.brand{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.mark{width:26px;height:26px;flex:none;display:grid;grid-template-columns:1fr 1fr;
  grid-template-rows:1fr 1fr;gap:1.5px;border-radius:3px;overflow:hidden}
.mark i{display:block}
.brand h1{font-size:17px;font-weight:700;margin:0;letter-spacing:.01em}
.brand .sub{font-size:11.5px;letter-spacing:.14em;color:var(--ink-3);text-transform:uppercase;font-weight:600}

.picker{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:10px 0}
.picker label{font-size:12px;letter-spacing:.1em;color:var(--ink-3);font-weight:600}
select{
  font:inherit;font-size:14px;font-weight:500;color:var(--ink);background:var(--surface);
  border:1px solid var(--line);border-radius:5px;padding:6px 10px;max-width:100%;
}
.csys{font-size:11.5px;color:var(--accent);background:var(--accent-soft);
  padding:3px 8px;border-radius:3px;font-weight:600}

nav{display:flex;gap:2px;overflow-x:auto;margin-top:4px;scrollbar-width:none}
nav::-webkit-scrollbar{display:none}
nav button{
  padding:10px 14px 9px;font-size:14px;font-weight:500;color:var(--ink-2);
  border-bottom:2px solid transparent;white-space:nowrap;flex:none;
}
nav button[aria-selected="true"]{color:var(--ink);font-weight:700;border-bottom-color:var(--accent)}
nav button:hover{color:var(--ink)}

/* ── 过滤提示 ───────────────────────── */
.notice{
  display:flex;gap:9px;align-items:flex-start;margin:14px 0;padding:10px 13px;
  background:var(--accent-soft);border-left:3px solid var(--accent);border-radius:0 4px 4px 0;
  font-size:13px;line-height:1.65;color:var(--ink);
}
.notice b{font-weight:700}

/* ── 纸路筛选条 ─────────────────────── */
.path{position:relative;margin:16px 0 4px;overflow-x:auto;scrollbar-width:none;padding-bottom:2px}
.path::-webkit-scrollbar{display:none}
.path-inner{display:flex;align-items:center;gap:6px;position:relative;width:max-content;padding:2px}
.path-inner::before{
  content:"";position:absolute;left:12px;right:12px;top:50%;height:1px;
  background:var(--rail);z-index:0;
}
.chip{
  position:relative;z-index:1;font-size:13px;padding:5px 12px;border-radius:14px;
  border:1px solid var(--line);background:var(--surface);color:var(--ink-2);white-space:nowrap;
}
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--accent-ink);font-weight:600}
.chip .n{font-size:11px;opacity:.7;margin-left:4px;font-variant-numeric:tabular-nums}
.path-div{position:relative;z-index:1;width:1px;height:18px;background:var(--rail);margin:0 6px;flex:none}

.search{
  width:100%;font:inherit;font-size:15px;color:var(--ink);background:var(--surface);
  border:1px solid var(--line);border-radius:6px;padding:10px 13px;margin:12px 0 0;
}
.search::placeholder{color:var(--ink-3)}

.count{font-size:12.5px;color:var(--ink-3);margin:12px 0 8px;letter-spacing:.02em}

/* ── 卡片 ───────────────────────────── */
.card{
  background:var(--surface);border:1px solid var(--line);border-radius:7px;
  margin-bottom:8px;overflow:hidden;
}
.card.stop{border-left:3px solid var(--stop)}
.card.warning{border-left:3px solid var(--warn)}
.card.info{border-left:3px solid var(--rail)}
.card-hd{width:100%;display:block;text-align:left;padding:12px 14px}
.card-hd:hover{background:var(--sunk)}
.row1{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.code{font-size:13.5px;font-weight:600;letter-spacing:.04em;color:var(--accent)}
.ttl{font-size:15px;font-weight:600;line-height:1.5;margin:2px 0 0}
.meta{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-top:7px}

.pill{font-size:11px;font-weight:700;letter-spacing:.06em;padding:2px 7px;border-radius:3px}
.pill.stop{background:var(--stop-bg);color:var(--stop)}
.pill.warning{background:var(--warn-bg);color:var(--warn)}
.pill.info{background:var(--surface-2);color:var(--ink-2)}
.tag{font-size:11.5px;color:var(--ink-2);border:1px solid var(--line);padding:2px 7px;border-radius:3px}
.tag.ok{color:var(--ok);border-color:var(--ok)}
.tag.warn{color:var(--warn);border-color:var(--warn)}
.tag.stop{color:var(--stop);border-color:var(--stop)}
.eta{font-size:11.5px;color:var(--ink-3);font-variant-numeric:tabular-nums}

/* 置信度徽标——本产品的核心差异点，给它独立的视觉语言 */
.conf{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:700;
  padding:2px 7px;border-radius:3px;letter-spacing:.04em}
.conf.verified{background:var(--accent);color:var(--accent-ink)}
.conf.reported{background:transparent;color:var(--ink-2);border:1px dashed var(--line)}

.body{padding:0 14px 14px;border-top:1px solid var(--line);margin-top:2px;padding-top:12px}
.body p{margin:0 0 10px}
.lbl{font-size:11px;font-weight:700;letter-spacing:.14em;color:var(--ink-3);
  text-transform:uppercase;margin:14px 0 6px}
.steps{margin:0;padding-left:1.35em}
.steps li{margin:5px 0}
.steps li::marker{color:var(--accent);font-weight:600}

.cause{display:flex;gap:10px;padding:9px 0;border-top:1px dashed var(--line)}
.cause:first-of-type{border-top:none}
.lk{flex:none;width:34px;padding-top:3px}
.lkbar{display:flex;gap:2px;margin-bottom:2px}
.lkbar i{width:8px;height:3px;border-radius:1px;background:var(--surface-2);display:block}
.lkbar i.on{background:var(--accent)}
.lktxt{font-size:10px;color:var(--ink-3);letter-spacing:.05em}
.cause-b{flex:1;min-width:0}
.cause-b .c{font-weight:600;font-size:14px}
.cause-b .f{font-size:13.5px;color:var(--ink-2);margin-top:2px}

.safety{background:var(--stop-bg);border:1px solid var(--stop);border-radius:5px;
  padding:10px 12px;margin:12px 0;font-size:13.5px;color:var(--ink)}
.safety b{color:var(--stop);display:block;font-size:11px;letter-spacing:.14em;margin-bottom:4px}
.note{background:var(--sunk);border-radius:5px;padding:10px 12px;font-size:13.5px;
  color:var(--ink-2);margin:10px 0}

.srcs{margin-top:14px;padding-top:10px;border-top:1px solid var(--line)}
.srcs .lbl{margin:0 0 6px}
.srclist{display:flex;flex-wrap:wrap;gap:6px}
.srclist a{
  font-size:12px;text-decoration:none;color:var(--ink-2);background:var(--sunk);
  border:1px solid var(--line);border-radius:3px;padding:3px 8px;max-width:100%;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.srclist a:hover{color:var(--accent);border-color:var(--accent)}
.srclist a::after{content:" ↗";opacity:.5}

/* ── 付费墙 ─────────────────────────── */
.lock{padding:14px;text-align:center;background:var(--sunk)}
.lock .t{font-size:14px;font-weight:600;margin-bottom:3px}
.lock .d{font-size:12.5px;color:var(--ink-3);margin-bottom:10px}
.lock button{background:var(--accent);color:var(--accent-ink);font-size:13.5px;font-weight:600;
  padding:8px 20px;border-radius:5px}
.lock .ph{font-size:11px;color:var(--ink-3);margin-top:8px;letter-spacing:.04em}

/* ── 引导诊断 ───────────────────────── */
.step{font-size:11px;letter-spacing:.16em;color:var(--ink-3);font-weight:700;margin:18px 0 8px}
.q{font-size:18px;font-weight:700;margin:0 0 4px}
.qd{font-size:13.5px;color:var(--ink-2);margin:0 0 14px}
.opt{display:block;width:100%;text-align:left;background:var(--surface);border:1px solid var(--line);
  border-radius:6px;padding:13px 15px;margin-bottom:7px;font-size:15px;font-weight:500}
.opt:hover{border-color:var(--accent);background:var(--accent-soft)}
.opt .sm{display:block;font-size:12.5px;color:var(--ink-3);font-weight:400;margin-top:2px}
.back{font-size:13px;color:var(--accent);margin-bottom:4px;padding:4px 0}

/* ── 保养 ───────────────────────────── */
.chk{display:flex;gap:11px;align-items:flex-start;background:var(--surface);
  border:1px solid var(--line);border-radius:7px;padding:12px 14px;margin-bottom:7px}
.chk input{width:19px;height:19px;flex:none;margin-top:2px;accent-color:var(--accent);cursor:pointer}
.chk .t{font-size:15px;font-weight:600}
.chk.done .t{color:var(--ink-3);text-decoration:line-through}
.chk .d{font-size:13.5px;color:var(--ink-2);margin-top:2px}
.chk .spec{font-size:13px;color:var(--ink);background:var(--sunk);border-radius:4px;
  padding:7px 10px;margin-top:7px;font-variant-numeric:tabular-nums}
.progress{font-size:13px;color:var(--ink-2);margin:12px 0 4px;font-variant-numeric:tabular-nums}
.lube{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 0}
.lube span{display:inline-flex;align-items:center;gap:6px;font-size:13px;border:1px solid var(--line);
  border-radius:4px;padding:5px 10px;background:var(--surface)}
.dot{width:11px;height:11px;border-radius:50%;display:block;border:1px solid rgba(0,0,0,.18)}

/* ── 关于 ───────────────────────────── */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(88px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:6px;overflow:hidden;margin:14px 0}
.stat{background:var(--surface);padding:11px 12px}
.stat .v{font-size:21px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.2}
.stat .k{font-size:11.5px;color:var(--ink-3);margin-top:1px}
.rule{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:13px 15px;margin-bottom:8px}
.rule h4{margin:0 0 5px;font-size:14.5px}
.rule p{margin:0;font-size:13.5px;color:var(--ink-2)}
h3.sec{font-size:16px;margin:26px 0 8px;padding-top:16px;border-top:1px solid var(--line)}
.srcrow{display:flex;gap:10px;padding:8px 0;border-bottom:1px solid var(--line);font-size:13px}
.srcrow .ty{flex:none;font-size:10.5px;letter-spacing:.08em;color:var(--ink-3);
  text-transform:uppercase;width:62px;padding-top:3px;font-weight:600}
.srcrow a{text-decoration:none}
.srcrow a:hover{text-decoration:underline}
.foot{font-size:12.5px;color:var(--ink-3);line-height:1.75;margin-top:22px;
  padding-top:14px;border-top:1px solid var(--line)}
.empty{text-align:center;color:var(--ink-3);font-size:14px;padding:36px 12px}
[hidden]{display:none !important}

/* ── 问诊 ───────────────────────────── */
.chat{padding:6px 0 12px}
.hero{padding:14px 0 6px}
.hero .qd{max-width:38em}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.chips .chip{border-radius:5px}
.chips .chip:hover{border-color:var(--accent);color:var(--accent)}
.bub-u{
  background:var(--accent);color:var(--accent-ink);padding:9px 14px;border-radius:14px 14px 3px 14px;
  margin:16px 0 10px auto;max-width:82%;width:fit-content;font-size:14.5px;line-height:1.6;
}
.bub-a{
  background:var(--surface);border:1px solid var(--line);border-radius:3px 14px 14px 14px;
  padding:13px 15px;margin-bottom:10px;
}
.why{font-size:13px;color:var(--ink-2);margin-bottom:12px;line-height:1.65}
.res{border-top:1px solid var(--line);padding:13px 0 4px}
.res:first-of-type{border-top:none;padding-top:0}
.res.top .ttl{font-size:16.5px}
.res-hd{display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin-bottom:3px}
.rk{font-size:10.5px;font-weight:700;letter-spacing:.14em;color:var(--accent);text-transform:uppercase}
.res:not(.top) .rk{color:var(--ink-3)}
.match{font-size:11.5px;color:var(--ink-3);font-variant-numeric:tabular-nums}
.res .steps{margin-top:4px}
.more{font-size:13px;color:var(--accent);padding:7px 0 2px;font-weight:500}
.more:hover{text-decoration:underline}
.clar{margin-top:14px;padding-top:12px;border-top:1px dashed var(--line)}
.clar-q{font-size:14.5px;font-weight:600;margin-bottom:9px}
.opt.sm{padding:10px 13px;font-size:14px;margin-bottom:6px}
.typing{display:flex;gap:5px;width:fit-content;padding:14px 16px}
.typing span{width:6px;height:6px;border-radius:50%;background:var(--ink-3);opacity:.4;
  animation:blink 1.2s infinite}
.typing span:nth-child(2){animation-delay:.2s}
.typing span:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,60%,100%{opacity:.25}30%{opacity:.9}}
@media (prefers-reduced-motion:reduce){.typing span{animation:none}}
.composer{display:flex;gap:8px;align-items:center;position:sticky;bottom:0;
  background:var(--bg);padding:10px 0 12px;margin-top:4px}
.composer .search{margin:0;flex:1}
.send{width:42px;height:42px;flex:none;border-radius:50%;background:var(--accent);
  color:var(--accent-ink);font-size:19px;font-weight:700;line-height:1}
.send:hover{opacity:.88}

/* ── 语音 ───────────────────────────── */
.mic{width:42px;height:42px;flex:none;border-radius:50%;border:1px solid var(--line);
  background:var(--surface);font-size:17px;line-height:1}
.mic:hover{border-color:var(--accent)}
.mic.on{background:var(--stop);border-color:var(--stop);color:#fff;font-size:14px;
  animation:pulse 1.4s ease-out infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(168,42,32,.45)}70%{box-shadow:0 0 0 11px rgba(168,42,32,0)}
  100%{box-shadow:0 0 0 0 rgba(168,42,32,0)}}
@media (prefers-reduced-motion:reduce){.mic.on{animation:none}}
.vbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;min-height:20px;
  font-size:12.5px;color:var(--ink-3);padding:2px 2px 0}
.vok{color:var(--ink-3)}
.vno{color:var(--ink-3)}
.verr{color:var(--stop);line-height:1.55}
.vlive{display:inline-flex;align-items:center;gap:7px;color:var(--stop);font-weight:600}
.vlive i{width:8px;height:8px;border-radius:50%;background:var(--stop);display:block;
  animation:pulse2 1.1s infinite}
@keyframes pulse2{0%,100%{opacity:1}50%{opacity:.25}}
@media (prefers-reduced-motion:reduce){.vlive i{animation:none}}
.vtog{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;color:var(--ink-2);padding:2px 0}
.vtog i{width:26px;height:15px;border-radius:8px;background:var(--surface-2);
  border:1px solid var(--line);position:relative;display:block;transition:background .15s}
.vtog i::after{content:"";position:absolute;top:1px;left:1px;width:11px;height:11px;border-radius:50%;
  background:var(--ink-3);transition:transform .15s,background .15s}
.vtog i.on{background:var(--accent);border-color:var(--accent)}
.vtog i.on::after{transform:translateX(11px);background:#fff}
@media (prefers-reduced-motion:reduce){.vtog i,.vtog i::after{transition:none}}
.hd-r{display:inline-flex;align-items:center;gap:10px}
.spk{font-size:11.5px;color:var(--accent);border:1px solid var(--line);border-radius:4px;
  padding:2px 8px;white-space:nowrap}
.spk:hover{border-color:var(--accent)}
.spk.on{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}

/* ── 投稿 ───────────────────────────── */
.fld{margin-bottom:12px}
.fld label{display:block;font-size:13.5px;font-weight:600;margin-bottom:5px}
.fh{display:block;font-size:12px;font-weight:400;color:var(--ink-3);margin-top:1px}
.fld input,.fld textarea,.fld select{
  width:100%;font:inherit;font-size:14.5px;color:var(--ink);background:var(--surface);
  border:1px solid var(--line);border-radius:5px;padding:8px 11px;resize:vertical}
.fld textarea{line-height:1.65}
.fnote{font-size:12.5px;color:var(--ink-3);margin-top:5px;line-height:1.6}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
@media (max-width:520px){.grid2{grid-template-columns:1fr}}
.ckl{border:1px solid var(--line);border-radius:6px;overflow:hidden;background:var(--surface)}
.ckrow{display:flex;gap:10px;padding:10px 13px;border-top:1px solid var(--line);font-size:13.5px}
.ckrow:first-child{border-top:none}
.ckrow .ci{flex:none;width:16px;font-weight:700;text-align:center}
.ckrow.ok{background:var(--ok-bg)} .ckrow.ok .ci{color:var(--ok)}
.ckrow.bad .ci{color:var(--ink-3)}
.ckrow.warn .ci{color:var(--warn)}
.cq{display:block;color:var(--ink-2);margin-top:1px}
.cw{display:block;color:var(--ink-3);font-size:12.5px;margin-top:3px;line-height:1.6}
.ckmini{display:flex;flex-wrap:wrap;gap:6px;margin:2px 0 4px}
.ckmini span{font-size:11.5px;border:1px solid var(--line);border-radius:3px;padding:2px 7px}
.ckmini .ok{color:var(--ok);border-color:var(--ok)}
.ckmini .bad{color:var(--stop);border-color:var(--stop)}
.subact{display:flex;gap:9px;flex-wrap:wrap;margin-top:16px}
.subact .primary{background:var(--accent);color:var(--accent-ink);font-size:14.5px;font-weight:600;
  padding:10px 20px;border-radius:5px}
.subact .primary:disabled{background:var(--surface-2);color:var(--ink-3);cursor:not-allowed}
.subact .ghost{border:1px solid var(--line);border-radius:5px;padding:10px 18px;
  font-size:14.5px;color:var(--ink-2)}
.subact .ghost:hover{border-color:var(--accent);color:var(--accent)}
.flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:6px;overflow:hidden;margin:10px 0}
.fstep{background:var(--surface);padding:11px 13px}
.fname{font-size:13.5px;font-weight:700}
.fdesc{font-size:12.5px;color:var(--ink-3);line-height:1.6;margin-top:2px}
</style>

<header>
  <div class="hd">
    <div class="brand">
      <span class="mark" aria-hidden="true">
        <i style="background:#00A0D2"></i><i style="background:#D6006E"></i>
        <i style="background:#F0C400"></i><i style="background:#22201E"></i>
      </span>
      <h1>海德堡排故台</h1>
      <span class="sub lat">Field Diagnostics</span>
    </div>
    <div class="picker">
      <label class="lat" for="machine">MACHINE</label>
      <select id="machine"></select>
      <span class="csys" id="csys"></span>
    </div>
    <nav id="tabs" role="tablist"></nav>
  </div>
</header>

<div class="wrap">
  <div id="notice" class="notice" hidden></div>
  <main id="view"></main>
</div>

<script>
const D = __DATA__;

const state = {
  tab: "chat",
  machine: "all",
  chat: [],
  pending: false,
  voice: { listening: false, error: null, speaking: null, autoSpeak: false },
  subMsg: "",
  cat: { codes: "all", cases: "all" },
  q: { codes: "", cases: "" },
  open: {},
  diag: { cat: null, caseId: null },
  interval: "daily",
  unlocked: false,
  checked: {}
};

const STORE = "hdb-kb-v1";
try {
  const saved = JSON.parse(localStorage.getItem(STORE) || "{}");
  if (saved && typeof saved === "object") {
    state.checked = saved.checked || {};
    if (saved.machine) state.machine = saved.machine;
    if (saved.autoSpeak) state.voice.autoSpeak = true;
  }
} catch (e) { /* 隐私模式或站点数据被禁用时静默降级 */ }

function persist() {
  try {
    localStorage.setItem(STORE, JSON.stringify({
      checked: state.checked, machine: state.machine, autoSpeak: state.voice.autoSpeak }));
  } catch (e) { /* 忽略：本地记忆只是便利功能，不影响使用 */ }
}

const esc = s => String(s).replace(/[&<>"']/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const machineById = id => D.machines.find(m => m.id === id);

/* ── 机型过滤：本原型与常见 AI 生成版本最本质的区别 ──
   机型是第一层入口，且条目声明的控制系统必须与该机型实际配备的世代相符。 */
function matches(entry) {
  if (state.machine === "all") return true;
  const m = machineById(state.machine);
  if (!m) return true;
  const list = entry.machines || ["*"];
  if (!list.includes("*") && !list.includes(state.machine)) return false;
  if (entry.control_systems && entry.control_systems.length) {
    return entry.control_systems.some(cs => m.control_systems.includes(cs));
  }
  return true;
}

function confBadge(c) {
  const lv = D.confidenceLevels[c];
  if (!lv) return "";
  return `<span class="conf ${esc(c)}" title="${esc(lv.desc_zh)}">${
    c === "verified" ? "✓ " : ""}${esc(lv.name_zh)}</span>`;
}

function srcBlock(ids) {
  if (!ids || !ids.length) return "";
  const links = ids.map(id => {
    const s = D.sources[id];
    if (!s) return "";
    return `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>`;
  }).join("");
  return `<div class="srcs"><div class="lbl lat">Sources · 出处</div><div class="srclist">${links}</div></div>`;
}

function extras(e) {
  let h = "";
  if (e.spec_zh) h += `<div class="note"><b>参数：</b>${esc(e.spec_zh)}</div>`;
  if (e.safety_zh) h += `<div class="safety"><b class="lat">SAFETY · 安全</b>${esc(e.safety_zh)}</div>`;
  if (e.notes_zh) h += `<div class="note">${esc(e.notes_zh)}</div>`;
  return h;
}

/* ── 纸路筛选条 ── */
function pathBar(scope, items) {
  const counts = {};
  items.forEach(e => { counts[e.category] = (counts[e.category] || 0) + 1; });
  const cur = state.cat[scope];
  const chip = (id, name) => {
    const n = id === "all" ? items.length : (counts[id] || 0);
    if (id !== "all" && !n) return "";
    return `<button class="chip" aria-pressed="${cur === id}" data-cat="${esc(id)}" data-scope="${esc(scope)}"
      >${esc(name)}<span class="n">${n}</span></button>`;
  };
  const path = D.paperPath.map(id => chip(id, D.categories[id])).join("");
  const sys = D.systemGroup.map(id => chip(id, D.categories[id])).join("");
  return `<div class="path"><div class="path-inner">${chip("all", "全部")}${path}${
    sys ? '<span class="path-div"></span>' + sys : ""}</div></div>`;
}

function hiddenNotice(hidden, total) {
  const el = document.getElementById("notice");
  if (state.machine === "all" || !hidden) { el.hidden = true; return; }
  const m = machineById(state.machine);
  const cs = m.control_systems.map(c => D.controlSystems[c].name_zh).join(" / ");
  el.hidden = false;
  el.innerHTML = `<span>已按 <b>${esc(m.name)}（${esc(cs)}）</b>过滤，隐藏 <b>${hidden}</b> 条不适用于本机型的内容，
    当前显示 ${total - hidden} 条。<br>其他世代控制系统的报警不会出现在这台机器上——把它们混列是同类产品最常见的硬伤。</span>`;
}

/* ── 查码 ── */
function viewCodes() {
  const all = D.faultCodes;
  const byMachine = all.filter(matches);
  hiddenNotice(all.length - byMachine.length, all.length);

  const q = state.q.codes.trim().toLowerCase();
  const list = byMachine.filter(e =>
    (state.cat.codes === "all" || e.category === state.cat.codes) &&
    (!q || (e.code + e.title_zh + e.meaning_zh + (e.example || "")).toLowerCase().includes(q)));

  const cards = list.map(e => {
    const open = !!state.open["c" + e.id];
    return `<article class="card ${esc(e.severity)}">
      <button class="card-hd" data-open="c${esc(e.id)}" aria-expanded="${open}">
        <div class="row1"><span class="code mono">${esc(e.code)}</span>
          <span class="pill ${esc(e.severity)} lat">${
            { stop: "停机", warning: "警告", info: "提示" }[e.severity]}</span></div>
        <div class="ttl">${esc(e.title_zh)}</div>
        <div class="meta"><span class="tag">${esc(D.categories[e.category])}</span>${
          e.control_systems.map(c => `<span class="tag">${esc(D.controlSystems[c].name_zh)}</span>`).join("")
        }${confBadge(e.confidence)}</div>
      </button>
      ${open ? `<div class="body">
        ${e.example ? `<p class="mono" style="font-size:13px;color:var(--ink-3)">例：${esc(e.example)}</p>` : ""}
        <p>${esc(e.meaning_zh)}</p>
        <div class="lbl lat">Check order · 排查顺序</div>
        <ol class="steps">${e.checks.map(c => `<li>${esc(c)}</li>`).join("")}</ol>
        ${extras(e)}${srcBlock(e.sources)}</div>` : ""}
    </article>`;
  }).join("");

  return `${pathBar("codes", byMachine)}
    <input class="search" id="q-codes" placeholder="搜代码、现象、部位…" value="${esc(state.q.codes)}">
    <div class="count">${list.length} 条故障码${q ? "（匹配“" + esc(q) + "”）" : ""}</div>
    ${cards || '<div class="empty">没有匹配的代码。<br>换个关键词，或到「诊断」按现象排查。</div>'}
    <h3 class="sec">读码规则</h3>
    <p style="font-size:13.5px;color:var(--ink-2);margin:0 0 10px">
      会读规则的人能自己解未收录的码——这比背代码表有用。</p>
    ${D.decodingRules.map(r => `<article class="card info">
      <div class="card-hd"><div class="ttl">${esc(r.title_zh)}</div>
      <div class="meta">${r.applies_to.map(c =>
        `<span class="tag">${esc(D.controlSystems[c].name_zh)}</span>`).join("")}${confBadge(r.confidence)}</div>
      <p style="margin:10px 0 0;font-size:14px">${esc(r.body_zh)}</p>${srcBlock(r.sources)}</div>
    </article>`).join("")}`;
}

/* ── 案例 ── */
function caseCard(e) {
  const open = !!state.open["k" + e.id];
  const fx = D.fixableLevels[e.field_fixable];
  const tone = { onsite: "ok", parts_needed: "warn", service_required: "stop" }[e.field_fixable];
  const locked = e.premium && !state.unlocked;
  return `<article class="card info">
    <button class="card-hd" data-open="k${esc(e.id)}" aria-expanded="${open}">
      <div class="ttl">${esc(e.title_zh)}</div>
      <div class="meta"><span class="tag">${esc(D.categories[e.category])}</span>
        <span class="tag ${tone}">${esc(fx.name_zh)}</span>
        <span class="eta mono">${e.eta_minutes[0]}–${e.eta_minutes[1]} 分钟</span>
        ${confBadge(e.confidence)}${locked ? '<span class="tag">🔒 会员</span>' : ""}</div>
      <div style="font-size:13.5px;color:var(--ink-2);margin-top:5px">${esc(e.symptom_zh)}</div>
    </button>
    ${!open ? "" : locked ? `<div class="lock">
        <div class="t">完整排查路径为会员内容</div>
        <div class="d">含 ${e.causes.length} 条按概率排序的原因与对应做法</div>
        <button data-unlock="1">解锁全部案例</button>
        <div class="ph lat">付费墙占位 · 真实产品由后端鉴权</div></div>`
      : `<div class="body">
        <div class="lbl lat">Causes by likelihood · 按概率排序</div>
        ${e.causes.map(c => {
          const n = { high: 3, medium: 2, low: 1 }[c.likelihood];
          const zh = { high: "高", medium: "中", low: "低" }[c.likelihood];
          return `<div class="cause"><div class="lk">
            <div class="lkbar">${[1, 2, 3].map(i =>
              `<i class="${i <= n ? "on" : ""}"></i>`).join("")}</div>
            <div class="lktxt">${zh}</div></div>
            <div class="cause-b"><div class="c">${esc(c.cause_zh)}</div>
            <div class="f">→ ${esc(c.fix_zh)}</div></div></div>`;
        }).join("")}
        ${extras(e)}${srcBlock(e.sources)}</div>`}
  </article>`;
}

function viewCases() {
  const all = D.cases;
  const byMachine = all.filter(matches);
  hiddenNotice(all.length - byMachine.length, all.length);
  const q = state.q.cases.trim().toLowerCase();
  const list = byMachine.filter(e =>
    (state.cat.cases === "all" || e.category === state.cat.cases) &&
    (!q || (e.title_zh + e.symptom_zh + e.causes.map(c => c.cause_zh).join("")).toLowerCase().includes(q)));

  return `${pathBar("cases", byMachine)}
    <input class="search" id="q-cases" placeholder="搜现象，如 双张、歪斜、蹭脏…" value="${esc(state.q.cases)}">
    <div class="count">${list.length} 个案例 · 按纸路工位分类</div>
    ${list.map(caseCard).join("") || '<div class="empty">没有匹配的案例。</div>'}`;
}

/* ══ 语音 ══════════════════════════════════════════════════
   输入用 Web Speech API，输出用 SpeechSynthesis。两者都做能力探测：
   拿不到就彻底隐藏入口，绝不留一个点了没反应的按钮。 */

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const VOICE_IN = !!SR;
// 判断对象本身而非属性是否存在——某些环境属性在但取值为 undefined，只查 `in` 会在调用时崩
const VOICE_OUT = !!(window.speechSynthesis && window.SpeechSynthesisUtterance);
let rec = null;

const VOICE_ERR = {
  "not-allowed": "麦克风权限被拒绝。点地址栏的权限图标允许后重试，或在新标签页打开本页面。",
  "service-not-allowed": "当前环境不允许语音识别。在新标签页单独打开本页面通常可解决。",
  "audio-capture": "没有检测到麦克风设备。",
  "no-speech": "没听到声音，再说一次。车间噪音大时请靠近手机。",
  "network": "语音识别需要联网，当前网络不通。",
  "aborted": null
};

function stopVoice() {
  try { if (rec) rec.abort(); } catch (e) { /* 已停止 */ }
  state.voice.listening = false;
}

function startVoice() {
  if (!VOICE_IN) return;
  if (state.voice.listening) { stopVoice(); render(); return; }
  try {
    rec = new SR();
    rec.lang = "zh-CN";
    rec.interimResults = true;
    rec.continuous = false;
    rec.maxAlternatives = 1;

    rec.onstart = () => {
      state.voice.listening = true; state.voice.error = null; render();
    };
    rec.onresult = ev => {
      let interim = "", final = "";
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const r = ev.results[i];
        if (r.isFinal) final += r[0].transcript; else interim += r[0].transcript;
      }
      if (final.trim()) {
        state.voice.listening = false;
        try { rec.stop(); } catch (e) { /* 忽略 */ }
        ask(final.trim());
      } else {
        // 中间结果只改输入框，不整页重绘——否则光标和录音状态会闪
        const el = document.getElementById("chat-in");
        if (el) el.value = interim;
      }
    };
    rec.onerror = ev => {
      state.voice.listening = false;
      const msg = VOICE_ERR[ev.error];
      state.voice.error = msg === undefined ? ("语音识别出错：" + ev.error) : msg;
      render();
    };
    rec.onend = () => { if (state.voice.listening) { state.voice.listening = false; render(); } };
    rec.start();
  } catch (e) {
    state.voice.listening = false;
    state.voice.error = "无法启动语音识别：" + ((e && e.message) || e);
    render();
  }
}

function speechText(e) {
  const out = ["判断：" + e.title_zh + "。"];
  if (e.causes) {
    const high = e.causes.filter(c => c.likelihood === "high");
    (high.length ? high : e.causes.slice(0, 2)).slice(0, 2).forEach((c, i) => {
      out.push("第" + (i + 1) + "，" + c.cause_zh + "。做法：" + c.fix_zh);
    });
  } else if (e.checks) {
    e.checks.slice(0, 2).forEach((c, i) => out.push("第" + (i + 1) + "，" + c));
  }
  if (e.safety_zh) out.push("注意安全：" + e.safety_zh);
  return out.join(" ");
}

function speak(entry) {
  if (!VOICE_OUT) return;
  const synth = window.speechSynthesis;
  try {
    if (state.voice.speaking === entry.id) { synth.cancel(); state.voice.speaking = null; render(); return; }
    synth.cancel();
    const u = new SpeechSynthesisUtterance(speechText(entry));
    u.lang = "zh-CN";
    u.rate = 0.95;
    u.onend = () => { state.voice.speaking = null; render(); };
    u.onerror = () => { state.voice.speaking = null; render(); };
    state.voice.speaking = entry.id;
    render();
    synth.speak(u);
  } catch (e) {
    state.voice.speaking = null;
  }
}

/* ══ 问诊引擎 ══════════════════════════════════════════════
   纯本地检索，不调用任何大模型——因此它永远不会编造一个不存在的故障码。
   命中不了就明说“知识库里没有”，而不是编一个看起来合理的答案。 */

const SYN = D.synonyms;

function hitTags(text) {
  const t = text.toLowerCase();
  const out = [];
  for (const term of SYN.terms) {
    if (term.variants.some(v => t.includes(v.toLowerCase()))) out.push(term);
  }
  return out;
}

/* 中文无空格，用 2~3 字滑窗提取候选词，过滤停用词后与条目文本比对 */
function grams(text) {
  const clean = text.replace(/[\s,，。、；;!！?？~—\-()（）"'"'']/g, "");
  const stop = new Set(SYN.stopwords);
  const out = new Set();
  for (let n = 2; n <= 3; n++) {
    for (let i = 0; i + n <= clean.length; i++) {
      const g = clean.slice(i, i + n);
      if (!stop.has(g) && !/^[0-9]+$/.test(g)) out.add(g);
    }
  }
  SYN.stopwords.forEach(s => out.delete(s));
  return [...out];
}

function blobOf(e) {
  if (e._blob) return e._blob;
  const parts = [e.title_zh, e.symptom_zh || "", e.meaning_zh || "", e.code || "", e.example || "",
    D.categories[e.category] || "",
    (e.causes || []).map(c => c.cause_zh + c.fix_zh).join(""),
    (e.checks || []).join("")];
  e._blob = parts.join(" ").toLowerCase();
  return e._blob;
}

function diagnose(text, extraTags) {
  const tags = hitTags(text);
  (extraTags || []).forEach(name => {
    const t = SYN.terms.find(x => x.tag === name);
    if (t && !tags.includes(t)) tags.push(t);
  });
  const tagNames = tags.map(t => t.tag);
  const gs = grams(text);
  const pool = [...D.cases, ...D.faultCodes].filter(matches);
  const why = new Set();

  const scored = pool.map(e => {
    let s = 0;
    const blob = blobOf(e);
    const title = (e.title_zh + (e.code || "")).toLowerCase();

    for (const t of tags) {
      if ((t.boost_entries || []).includes(e.id)) { s += 12; why.add(t.tag); }
      if ((t.categories || []).includes(e.category)) s += 3;
      if (t.variants.some(v => blob.includes(v.toLowerCase()))) { s += 2; why.add(t.tag); }
    }
    for (const g of gs) {
      if (title.includes(g)) s += 2.5;
      else if (blob.includes(g)) s += 0.8;
    }
    // 直接报了代码：优先级最高
    if (e.code && e.code.length > 3) {
      const stem = e.code.toLowerCase().replace(/[\s<>]|槽位号/g, "").slice(0, 6);
      if (stem.length > 2 && text.toLowerCase().replace(/\s/g, "").includes(stem)) {
        s += 25;
        why.add(e.code.split(/[\s<]/)[0]);
      }
    }
    return { e, s };
  }).filter(x => x.s > 3).sort((a, b) => b.s - a.s);

  const clar = SYN.clarifiers.find(c => c.trigger_tags.some(t => tagNames.includes(t)));
  return { hits: scored.slice(0, 5), tags: [...why], clarifier: clar, total: scored.length };
}

function resultCard(x, rank) {
  const e = x.e;
  const isCase = !!e.causes;
  const conf = Math.min(96, Math.round(38 + x.s * 3.2));
  if (isCase) {
    const fx = D.fixableLevels[e.field_fixable];
    const tone = { onsite: "ok", parts_needed: "warn", service_required: "stop" }[e.field_fixable];
    const top = e.causes.filter(c => c.likelihood === "high");
    const show = (top.length ? top : e.causes.slice(0, 2));
    return `<div class="res ${rank === 0 ? "top" : ""}">
      <div class="res-hd"><span class="rk lat">${rank === 0 ? "最可能" : "也可能"}</span>
        <span class="hd-r">${VOICE_OUT ? `<button class="spk ${
          state.voice.speaking === e.id ? "on" : ""}" data-speak="${esc(e.id)}"
          aria-label="朗读这条判断">${state.voice.speaking === e.id ? "■ 停止" : "▶ 读给我听"}</button>` : ""}
        <span class="match mono">匹配度 ${conf}%</span></span></div>
      <div class="ttl">${esc(e.title_zh)}</div>
      <div class="meta"><span class="tag">${esc(D.categories[e.category])}</span>
        <span class="tag ${tone}">${esc(fx.name_zh)}</span>
        <span class="eta mono">${e.eta_minutes[0]}–${e.eta_minutes[1]} 分钟</span>${confBadge(e.confidence)}</div>
      <div class="lbl lat" style="margin-top:11px">先查这几项</div>
      ${show.map(c => `<div class="cause"><div class="lk">
        <div class="lkbar">${[1, 2, 3].map(i => `<i class="${
          i <= { high: 3, medium: 2, low: 1 }[c.likelihood] ? "on" : ""}"></i>`).join("")}</div>
        <div class="lktxt">${{ high: "高", medium: "中", low: "低" }[c.likelihood]}</div></div>
        <div class="cause-b"><div class="c">${esc(c.cause_zh)}</div>
        <div class="f">→ ${esc(c.fix_zh)}</div></div></div>`).join("")}
      ${e.causes.length > show.length
        ? `<button class="more" data-goto-case="${esc(e.id)}">查看全部 ${e.causes.length} 条原因与出处 →</button>` : ""}
      ${srcBlock(e.sources)}</div>`;
  }
  return `<div class="res ${rank === 0 ? "top" : ""}">
    <div class="res-hd"><span class="rk lat">${rank === 0 ? "最可能" : "相关代码"}</span>
      <span class="hd-r">${VOICE_OUT ? `<button class="spk ${
        state.voice.speaking === e.id ? "on" : ""}" data-speak="${esc(e.id)}"
        aria-label="朗读这条判断">${state.voice.speaking === e.id ? "■ 停止" : "▶ 读给我听"}</button>` : ""}
      <span class="match mono">匹配度 ${conf}%</span></span></div>
    <div class="row1"><span class="code mono">${esc(e.code)}</span>
      <span class="pill ${esc(e.severity)} lat">${
        { stop: "停机", warning: "警告", info: "提示" }[e.severity]}</span></div>
    <div class="ttl">${esc(e.title_zh)}</div>
    <div class="meta">${e.control_systems.map(c =>
      `<span class="tag">${esc(D.controlSystems[c].name_zh)}</span>`).join("")}${confBadge(e.confidence)}</div>
    <div class="lbl lat" style="margin-top:11px">排查顺序</div>
    <ol class="steps">${e.checks.slice(0, 3).map(c => `<li>${esc(c)}</li>`).join("")}</ol>
    ${e.safety_zh ? `<div class="safety"><b class="lat">SAFETY · 安全</b>${esc(e.safety_zh)}</div>` : ""}
    ${srcBlock(e.sources)}</div>`;
}

function ask(text, extraTags) {
  state.chat.push({ who: "u", text: text });
  const r = diagnose(text, extraTags);
  state.chat.push({ who: "a", r: r, q: text, tags: extraTags || [] });
  state.pending = true;
  render();
  setTimeout(() => {
    state.pending = false;
    render();
    scrollBottom();
    if (state.voice.autoSpeak && r.hits.length) speak(r.hits[0].e);
  }, 320);
}

function scrollBottom() {
  const el = document.getElementById("chat-end");
  if (el) el.scrollIntoView({ block: "end", behavior: "smooth" });
}

const EXAMPLES = [
  "飞达老是双张，检测器一直停机",
  "第4组套不准，十字线对不上",
  "印品上有杠子，间距挺均匀",
  "递纸吸嘴哒哒响，吸纸不牢",
  "水箱不制冷，酒精挥发特别快",
  "屏幕报 HAK 4"
];

function viewChat() {
  document.getElementById("notice").hidden = true;
  const m = machineById(state.machine);
  const scope = state.machine === "all"
    ? `全部 ${D.cases.length + D.faultCodes.length} 条`
    : `${m.name} 适用的条目`;

  const msgs = state.chat.map((msg, i) => {
    if (msg.who === "u") return `<div class="bub-u">${esc(msg.text)}</div>`;
    const r = msg.r;
    if (!r.hits.length) {
      return `<div class="bub-a"><p style="margin:0 0 8px"><b>知识库里没有能对上的条目。</b></p>
        <p style="margin:0 0 10px;font-size:13.5px;color:var(--ink-2)">
        本引擎只在 ${scope}里检索，不会替你编一个听起来合理的答案。
        换个说法试试，或者补充部位（飞达 / 前规 / 机组 / 收纸）和现象。</p>
        <div class="chips">${["飞达", "前规 / 拉规", "机组", "收纸", "电气"].map(c =>
          `<button class="chip" data-say="${esc(c)}出问题">${esc(c)}</button>`).join("")}</div></div>`;
    }
    const last = i === state.chat.length - 1;
    return `<div class="bub-a">
      <div class="why">依据你说的${r.tags.length
        ? "「" + r.tags.map(esc).join("」「") + "」" : "内容"}，在${esc(scope)}中检索到 ${r.total} 条相关，按匹配度排序：</div>
      ${r.hits.map((x, k) => resultCard(x, k)).join("")}
      ${last && r.clarifier ? `<div class="clar">
        <div class="clar-q">${esc(r.clarifier.question_zh)}</div>
        ${r.clarifier.options.map(o => `<button class="opt sm" data-clar="${esc(r.clarifier.id)}"
          data-optlabel="${esc(o.label_zh)}">${esc(o.label_zh)}</button>`).join("")}</div>` : ""}
    </div>`;
  }).join("");

  return `<div class="chat">
    ${state.chat.length ? "" : `<div class="hero">
      <h2 class="q">机器怎么了？用你平时说话的方式讲。</h2>
      <p class="qd">支持车间口语——「双张」「甩角」「哒哒响」「杠子」都听得懂。
      ${VOICE_IN ? "手上有油污就点麦克风直接说；" : ""}${VOICE_OUT ? "结果可以读给你听，眼睛不用离开机器。" : ""}
      引擎只从 ${D.faultCodes.length} 条故障码和 ${D.cases.length} 个案例里检索，<b>不会编造代码</b>；
      对不上就直说没有。</p>
      <div class="lbl lat">试试这些</div>
      <div class="chips">${EXAMPLES.map(e =>
        `<button class="chip" data-say="${esc(e)}">${esc(e)}</button>`).join("")}</div></div>`}
    ${msgs}
    ${state.pending ? '<div class="bub-a typing"><span></span><span></span><span></span></div>' : ""}
    <div id="chat-end"></div>
  </div>
  <div class="vbar">${voiceStatus()}</div>
  <form class="composer" id="chat-form">
    <input class="search" id="chat-in" autocomplete="off"
      placeholder="${state.voice.listening ? "正在听…" : "描述故障现象，或点麦克风说"}" value="">
    ${VOICE_IN ? `<button type="button" class="mic ${state.voice.listening ? "on" : ""}"
      data-mic="1" aria-label="${state.voice.listening ? "停止录音" : "语音输入"}"
      aria-pressed="${state.voice.listening}">${state.voice.listening ? "■" : "🎙"}</button>` : ""}
    <button type="submit" class="send" aria-label="发送">↑</button>
  </form>
  ${state.chat.length ? '<button class="back" data-clear-chat="1">清空重问</button>' : ""}`;
}

function voiceStatus() {
  if (state.voice.error) return `<span class="verr">${esc(state.voice.error)}</span>`;
  if (state.voice.listening) {
    return `<span class="vlive"><i></i>正在听…说完停顿一下会自动发送</span>`;
  }
  const bits = [];
  if (VOICE_IN) bits.push(`<span class="vok">🎙 可语音输入</span>`);
  if (VOICE_OUT) bits.push(`<button class="vtog" data-autospeak="1" aria-pressed="${state.voice.autoSpeak}"
    ><i class="${state.voice.autoSpeak ? "on" : ""}"></i>自动播报结果</button>`);
  if (!VOICE_IN && !VOICE_OUT) return "";
  if (!VOICE_IN) bits.unshift(`<span class="vno">本浏览器不支持语音输入，可打字提问</span>`);
  return bits.join("");
}

/* ── 引导诊断 ── */
function viewDiag() {
  const pool = D.cases.filter(matches);
  hiddenNotice(D.cases.length - pool.length, D.cases.length);

  if (!state.diag.cat) {
    const cats = [...D.paperPath, ...D.systemGroup].filter(c => pool.some(e => e.category === c));
    return `<div class="step lat">STEP 1 / 2</div>
      <h2 class="q">现在最明显的是哪一类？</h2>
      <p class="qd">按现象走，比对着代码猜更快。有现成代码就直接去「查码」。</p>
      ${cats.map(c => {
        const n = pool.filter(e => e.category === c).length;
        return `<button class="opt" data-diag-cat="${esc(c)}">${esc(D.categories[c])}
          <span class="sm">${n} 个案例</span></button>`;
      }).join("")}`;
  }

  if (!state.diag.caseId) {
    const list = pool.filter(e => e.category === state.diag.cat);
    return `<button class="back" data-diag-back="cat">← 重选类别</button>
      <div class="step lat">STEP 2 / 2</div>
      <h2 class="q">${esc(D.categories[state.diag.cat])}：具体是哪种表现？</h2>
      <p class="qd">选最接近的一条。</p>
      ${list.map(e => `<button class="opt" data-diag-case="${esc(e.id)}">${esc(e.title_zh)}
        <span class="sm">${esc(e.symptom_zh)}</span></button>`).join("")}`;
  }

  const c = D.cases.find(e => e.id === state.diag.caseId);
  state.open["k" + c.id] = true;
  const codes = D.faultCodes.filter(f => f.category === c.category && matches(f));
  return `<button class="back" data-diag-back="case">← 重选表现</button>
    <div class="step lat">RESULT · 排查建议</div>
    ${caseCard(c)}
    ${codes.length ? `<h3 class="sec">同工位相关故障码</h3>${
      codes.map(f => `<article class="card ${esc(f.severity)}"><div class="card-hd">
        <div class="row1"><span class="code mono">${esc(f.code)}</span></div>
        <div class="ttl">${esc(f.title_zh)}</div>
        <div class="meta">${confBadge(f.confidence)}</div></div></article>`).join("")}` : ""}`;
}

/* ── 保养 ── */
function viewMaint() {
  const all = D.maintenance;
  const pool = all.filter(matches);
  hiddenNotice(all.length - pool.length, all.length);
  const list = pool.filter(e => e.interval === state.interval);
  const done = list.filter(e => state.checked[e.id]).length;

  const tabs = D.intervals.filter(iv => pool.some(e => e.interval === iv.id)).map(iv => {
    const n = pool.filter(e => e.interval === iv.id).length;
    return `<button class="chip" aria-pressed="${state.interval === iv.id}" data-iv="${esc(iv.id)}"
      >${esc(iv.name_zh)}<span class="n">${n}</span></button>`;
  }).join("");

  return `<div class="path"><div class="path-inner">${tabs}
    <span class="path-div"></span>
    <button class="chip" aria-pressed="${state.interval === "parts"}" data-iv="parts">易损件<span class="n">${D.wearParts.length}</span></button>
    </div></div>
    ${state.interval === "parts" ? `
      <div class="count">${D.wearParts.length} 类易损件 · 每项标明磨损后表现为哪个故障</div>
      ${D.wearParts.map(p => `<article class="card info"><div class="card-hd">
        <div class="ttl">${esc(p.name_zh)}</div>
        <div class="meta"><span class="tag">${esc(D.categories[p.category])}</span></div>
        <div style="font-size:13.5px;color:var(--ink-2);margin-top:6px">
          <b>磨损后：</b>${esc(p.symptom_when_worn_zh)}</div>
        <div style="font-size:13.5px;color:var(--ink-2);margin-top:4px">
          <b>备件建议：</b>${esc(p.stock_advice_zh)}</div>
        ${srcBlock(p.sources)}</div></article>`).join("")}`
    : `<div class="progress">今日点检 ${done} / ${list.length}　·　勾选状态存在本机浏览器</div>
      ${list.map(e => `<label class="chk ${state.checked[e.id] ? "done" : ""}">
        <input type="checkbox" data-chk="${esc(e.id)}" ${state.checked[e.id] ? "checked" : ""}>
        <span><span class="t">${esc(e.title_zh)}</span>
        ${e.detail_zh ? `<span class="d">${esc(e.detail_zh)}</span>` : ""}
        ${e.spec_zh ? `<span class="spec">${esc(e.spec_zh)}</span>` : ""}
        ${srcBlock(e.sources)}</span></label>`).join("")}
      ${state.interval === "weekly" || state.interval === "monthly" || state.interval === "quarterly" ? `
        <div class="note"><b>${esc(D.lubeColors.title_zh)}：</b>${esc(D.lubeColors.body_zh)}
        <div class="lube">${D.lubeColors.items.map(i =>
          `<span><i class="dot" style="background:${
            { yellow: "#E8B923", blue: "#2F72B8", green: "#2E8B4F" }[i.color]}"></i>${
            esc(i.color_zh)}　${esc(D.intervals.find(v => v.id === i.interval).name_zh)}</span>`).join("")}</div></div>` : ""}`}`;
}

/* ── 投稿 ── */
const F = {
  handle: "", role: "机长", years: "", machine: "", csys: "", occurred: "", downtime: "",
  title: "", category: "", symptom: "", tried: "", root: "", fix: "",
  parts: "", fixable: "onsite", etaLo: "", etaHi: "", found: "", unsafe: false
};

function subChecks() {
  const has = v => !!String(v || "").trim();
  const long = (v, n) => String(v || "").trim().length >= n;
  const m = machineById(F.machine);
  return {
    traceable: has(F.machine) && has(F.occurred) && has(F.handle),
    root_cause: long(F.root, 12),
    actionable: long(F.fix, 12),
    generation_ok: !!m && (m.control_systems.length === 1 || has(F.csys)),
    safety_ok: !F.unsafe,
    original: long(F.found, 15),
    negative_results: has(F.tried)
  };
}

function buildSubmission() {
  const m = machineById(F.machine);
  return {
    id: "sub-draft-" + new Date().toISOString().slice(0, 10).replace(/-/g, ""),
    provenance: "field",
    status: "pending",
    submitted_at: new Date().toISOString().slice(0, 10),
    submitter: { handle: F.handle.trim(), role: F.role, years: Number(F.years) || null },
    incident: {
      machine: F.machine,
      control_system: m ? (m.control_systems.length === 1 ? m.control_systems[0] : F.csys) : null,
      occurred_at: F.occurred,
      downtime_minutes: Number(F.downtime) || null
    },
    title_zh: F.title.trim(),
    category: F.category,
    symptom_zh: F.symptom.trim(),
    tried_zh: F.tried.split("\n").map(s => s.trim()).filter(Boolean),
    root_cause_zh: F.root.trim(),
    fix_zh: F.fix.trim(),
    parts_used: F.parts.split(/[,，\n]/).map(s => s.trim()).filter(Boolean),
    field_fixable: F.fixable,
    eta_minutes: [Number(F.etaLo) || 0, Number(F.etaHi) || 0],
    how_found_zh: F.found.trim(),
    confidence_proposed: "field_single"
  };
}

function viewSubmit() {
  document.getElementById("notice").hidden = true;
  const ck = subChecks();
  const list = D.sub.review_checklist;
  const blockingOk = list.filter(c => c.blocking).every(c => ck[c.id]);
  const m = machineById(F.machine);

  const field = (id, label, hint, val, type) => `<div class="fld">
    <label for="f-${id}">${esc(label)}${hint ? `<span class="fh">${esc(hint)}</span>` : ""}</label>
    ${type === "area"
      ? `<textarea id="f-${id}" data-f="${id}" rows="3">${esc(val)}</textarea>`
      : `<input id="f-${id}" data-f="${id}" type="${type || "text"}" value="${esc(val)}">`}</div>`;

  return `<h2 class="q" style="margin-top:14px">投稿：一次真实的排故经历</h2>
    <p class="qd">机长的一手记录不是“质量更差的网文”——只要写清了可回访核对的细节，它<b>比任何二手转述都可信</b>。
    表单按审核标准组织，右侧的检查项会实时告诉你还差什么。</p>

    <div class="lbl lat">谁 · 哪台机 · 什么时候</div>
    <div class="grid2">
      ${field("handle", "你的称号", "不需要真名", F.handle)}
      ${field("years", "工龄（年）", "", F.years, "number")}
    </div>
    <div class="fld"><label for="f-machine">机型<span class="fh">决定这条经验适用于哪些机器</span></label>
      <select id="f-machine" data-f="machine">
        <option value="">— 请选择 —</option>
        ${D.machines.map(x => `<option value="${x.id}" ${F.machine === x.id ? "selected" : ""}
          >${esc(x.name)}</option>`).join("")}
      </select>
      ${m && m.control_systems.length === 1
        ? `<div class="fnote">控制系统：${esc(D.controlSystems[m.control_systems[0]].name_zh)}（自动识别）</div>`
        : ""}
    </div>
    ${m && m.control_systems.length > 1 ? `<div class="fld">
      <label for="f-csys">控制系统<span class="fh">${esc(m.name)} 横跨两代，不同代的报警与板卡完全不同，必须指明</span></label>
      <select id="f-csys" data-f="csys">
        <option value="">— 请选择 —</option>
        ${m.control_systems.map(c => `<option value="${c}" ${F.csys === c ? "selected" : ""}
          >${esc(D.controlSystems[c].name_zh)}</option>`).join("")}
      </select></div>` : ""}
    <div class="grid2">
      ${field("occurred", "发生日期", "", F.occurred, "date")}
      ${field("downtime", "停机时长（分钟）", "", F.downtime, "number")}
    </div>

    <div class="lbl lat">出了什么事</div>
    ${field("title", "一句话标题", "如：换季后首件套准漂移，中午自愈", F.title)}
    <div class="fld"><label for="f-category">部位分类</label>
      <select id="f-category" data-f="category">
        <option value="">— 请选择 —</option>
        ${[...D.paperPath, ...D.systemGroup].map(c => `<option value="${c}" ${
          F.category === c ? "selected" : ""}>${esc(D.categories[c])}</option>`).join("")}
      </select></div>
    ${field("symptom", "现象描述", "机器当时什么表现", F.symptom, "area")}
    ${field("tried", "试过但没用的", "一行一条。这是最值钱的部分——替下一个人省掉同样的弯路", F.tried, "area")}
    ${field("root", "根本原因", "为什么坏，不是“换了个件就好了”", F.root, "area")}
    ${field("fix", "怎么解决的", "具体到部件、参数或工具", F.fix, "area")}
    ${field("found", "你是怎么发现的", "真实的排查过程，包括走过的弯路", F.found, "area")}

    <div class="lbl lat">处理难度</div>
    <div class="grid2">
      <div class="fld"><label for="f-fixable">现场可否自行处理</label>
        <select id="f-fixable" data-f="fixable">
          ${Object.entries(D.fixableLevels).map(([k, v]) =>
            `<option value="${k}" ${F.fixable === k ? "selected" : ""}>${esc(v.name_zh)}</option>`).join("")}
        </select></div>
      ${field("parts", "用到的备件", "逗号分隔，没有就留空", F.parts)}
    </div>
    <div class="grid2">
      ${field("etaLo", "耗时下限（分钟）", "", F.etaLo, "number")}
      ${field("etaHi", "耗时上限（分钟）", "", F.etaHi, "number")}
    </div>

    <label class="chk" style="margin-top:14px">
      <input type="checkbox" data-f="unsafe" ${F.unsafe ? "checked" : ""}>
      <span><span class="t">做法中包含短接或屏蔽安全装置</span>
      <span class="d">如实勾选。勾上后本条将被自动拒收——收录这类做法等于用平台信誉为一次工伤背书。</span></span>
    </label>

    <div class="lbl lat" style="margin-top:20px">审核标准自检</div>
    <div class="ckl">${list.map(c => `<div class="ckrow ${ck[c.id] ? "ok" : (c.blocking ? "bad" : "warn")}">
      <span class="ci">${ck[c.id] ? "✓" : (c.blocking ? "○" : "–")}</span>
      <span><b>${esc(c.name_zh)}</b>${c.blocking ? "" : "（不阻断）"}
      <span class="cq">${esc(c.ask_zh)}</span>
      <span class="cw">${esc(c.why_zh)}</span></span></div>`).join("")}</div>

    ${F.unsafe ? `<div class="safety"><b class="lat">SAFETY · 一票否决</b>
      含短接或屏蔽安全装置的做法不予收录，且不可申诉。正确路径是联系厂家或专业维修商更换同规格器件，
      等件期间该机组停用。</div>` : ""}

    <div class="subact">
      <button class="primary" data-export-sub="1" ${blockingOk ? "" : "disabled"}
        >${blockingOk ? "导出投稿 JSON" : "先补齐上面的阻断项"}</button>
      <button data-clear-sub="1" class="ghost">清空</button>
    </div>
    <div class="fnote" id="sub-msg">${esc(state.subMsg ||
      "导出的 JSON 可直接进入审核队列，由 validate.py 校验后并入知识库。真实产品应改为后端提交接口。")}</div>

    <h3 class="sec">审核流程</h3>
    <div class="flow">${D.sub.statuses.map(s => `<div class="fstep">
      <div class="fname">${esc(s.name_zh)}</div><div class="fdesc">${esc(s.desc_zh)}</div></div>`).join("")}</div>

    <h3 class="sec">审核队列（样例）</h3>
    <p style="font-size:13.5px;color:var(--ink-2);margin:0 0 10px">
      以下 ${D.sub.submissions.length} 条为演示审核流程而写，<b>不是真实投稿，也不会并入知识库</b>——
      校验器强制禁止样例被标记为已并入。</p>
    ${D.sub.submissions.map(s => {
      const st = D.sub.statuses.find(x => x.id === s.status);
      const tone = { accepted: "ok", merged: "ok", rejected: "stop", needs_info: "warn", reviewing: "", pending: "" }[s.status] || "";
      const rv = s.review || {};
      return `<article class="card ${s.status === "rejected" ? "stop" : "info"}">
        <button class="card-hd" data-open="s${esc(s.id)}" aria-expanded="${!!state.open["s" + s.id]}">
          <div class="row1"><span class="code mono">${esc(s.id)}</span>
            <span class="tag ${tone}">${esc(st ? st.name_zh : s.status)}</span></div>
          <div class="ttl">${esc(s.title_zh)}</div>
          <div class="meta"><span class="tag">${esc(D.categories[s.category])}</span>
            <span class="tag">${esc((machineById(s.incident.machine) || {}).name || s.incident.machine)}</span>
            <span class="eta mono">停机 ${s.incident.downtime_minutes} 分钟</span>
            <span class="tag">${esc(s.submitter.handle)} · ${s.submitter.years}年</span></div>
        </button>
        ${state.open["s" + s.id] ? `<div class="body">
          <div class="lbl lat">现象</div><p>${esc(s.symptom_zh)}</p>
          ${s.tried_zh.length ? `<div class="lbl lat">试过但没用</div>
            <ul class="steps">${s.tried_zh.map(t => `<li>${esc(t)}</li>`).join("")}</ul>` : ""}
          <div class="lbl lat">根因</div><p>${esc(s.root_cause_zh)}</p>
          <div class="lbl lat">做法</div><p>${esc(s.fix_zh)}</p>
          <div class="lbl lat">怎么发现的</div><p>${esc(s.how_found_zh)}</p>
          ${rv.checklist ? `<div class="lbl lat">复核结果</div>
            <div class="ckmini">${list.map(c => `<span class="${rv.checklist[c.id] ? "ok" : "bad"}"
              >${rv.checklist[c.id] ? "✓" : "✗"} ${esc(c.name_zh)}</span>`).join("")}</div>` : ""}
          ${rv.notes_zh ? `<div class="${s.status === "rejected" ? "safety" : "note"}">
            ${s.status === "rejected" ? '<b class="lat">拒收理由</b>' : "<b>复核意见：</b>"}${esc(rv.notes_zh)}</div>` : ""}
        </div>` : ""}
      </article>`;
    }).join("")}

    <h3 class="sec">投稿激励</h3>
    <ul class="steps">${D.sub.contributor_rewards.principles_zh.map(p => `<li>${esc(p)}</li>`).join("")}</ul>
    <div class="grid2" style="margin-top:10px">${D.sub.contributor_rewards.tiers_zh.map(t =>
      `<div class="rule"><h4>${esc(t.name)}</h4><p>${esc(t.reward)}</p></div>`).join("")}</div>`;
}

/* ── 关于 ── */
function viewAbout() {
  document.getElementById("notice").hidden = true;
  const byType = {};
  Object.values(D.sources).forEach(s => { (byType[s.type] = byType[s.type] || []).push(s); });
  const order = ["official", "manual", "forum", "document", "article", "vendor"];
  const label = { official: "官方", manual: "手册", forum: "论坛", document: "文档", article: "文章", vendor: "维修商" };

  return `<h3 class="sec" style="border:0;padding-top:14px;margin-top:8px">这是什么</h3>
    <p style="font-size:14.5px">这是一份海德堡单张纸胶印机排故知识库的<b>可交互原型</b>，界面由结构化数据自动生成。
    它想证明的只有一件事：<b>这类内容的价值不在条目数量，而在每一条都能追溯。</b></p>
    <div class="stats">
      <div class="stat"><div class="v">${D.faultCodes.length}</div><div class="k">故障码</div></div>
      <div class="stat"><div class="v">${D.decodingRules.length}</div><div class="k">读码规则</div></div>
      <div class="stat"><div class="v">${D.cases.length}</div><div class="k">案例</div></div>
      <div class="stat"><div class="v">${D.maintenance.length}</div><div class="k">保养项</div></div>
      <div class="stat"><div class="v">${Object.keys(D.sources).length}</div><div class="k">来源</div></div>
      <div class="stat"><div class="v">${D.machines.length}</div><div class="k">机型</div></div>
    </div>

    <h3 class="sec">三条收录纪律</h3>
    <div class="rule"><h4>一、没有来源的条目不准进库</h4>
      <p>每条数据都必须引用已登记的公开来源，校验器会检查引用是否可解析。宁可只有 ${D.faultCodes.length} 条真的故障码，也不要 200 条“看起来很像”的。</p></div>
    <div class="rule"><h4>二、故障码表禁止收录未核实条目</h4>
      <p>置信度分三档：<b>已核实</b>（多来源交叉印证）、<b>案例报告</b>（单一公开案例，方向可信但需现场确认）、<b>待核</b>（无法定位一手出处，禁止进入付费内容）。每条的徽标就是它的档位。</p></div>
    <div class="rule"><h4>三、控制系统必须与机型世代匹配</h4>
      <p>把 CP2000 时代的报警挂到用 Prinect Press Center 的 XL 106 上，校验器会直接报错中断构建。顶部选机型试试——不适用的内容会被过滤掉并告诉你隐藏了几条。</p></div>

    <h3 class="sec">机型与控制系统</h3>
    ${D.machines.map(m => `<div class="srcrow"><span class="ty">${esc(m.format_zh)}</span>
      <span><b>${esc(m.name)}</b> · ${m.control_systems.map(c => esc(D.controlSystems[c].name_zh)).join(" / ")}
      ${m.note_zh ? `<br><span style="color:var(--ink-3);font-size:12.5px">${esc(m.note_zh)}</span>` : ""}</span></div>`).join("")}

    <h3 class="sec">全部来源（${Object.keys(D.sources).length}）</h3>
    ${order.filter(t => byType[t]).map(t => byType[t].map(s =>
      `<div class="srcrow"><span class="ty lat">${esc(label[t])}</span>
      <a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a></div>`).join("")).join("")}

    <div class="foot">
      <b>免责声明：</b>本数据由公开网络资料汇编整理，仅供技术参考，不构成对任何具体设备的维修指导。
      所有参数（压力、间隙、温度、油品、扭矩）一律以本机随机《操作手册》《维修手册》为准；
      涉及安全回路、主传动、电气柜内部的作业应由受训人员执行。<b>严禁短接、屏蔽任何安全开关和护罩检测。</b><br><br>
      商标 Heidelberg、Speedmaster、Prinect、CP2000 等归海德堡印刷机械股份公司所有，本原型与该公司无隶属或授权关系。
      页面中的“解锁”为付费墙呈现方式的占位演示，不产生任何交易。数据更新于 ${esc(D.updated)}。
    </div>`;
}

/* ── 渲染与事件 ── */
const TABS = [
  ["chat", "问诊", viewChat], ["codes", "查码", viewCodes], ["diag", "引导", viewDiag],
  ["cases", "案例", viewCases], ["maint", "保养", viewMaint], ["submit", "投稿", viewSubmit],
  ["about", "关于", viewAbout]
];

/* 导出投稿：downloads 能力拿不到时退回剪贴板，两条路都断了才提示手动复制 */
async function exportSubmission() {
  const payload = JSON.stringify(buildSubmission(), null, 2);
  const filename = "投稿-" + (F.title.trim().slice(0, 20) || "案例") + ".json";
  try {
    const downloads = await window.claude.use("downloads");
    if (downloads) {
      await downloads.save({ filename: filename, data: payload });
      state.subMsg = "已导出 " + filename + "，把它发给知识库维护者即可进入审核队列。";
      render();
      return;
    }
  } catch (err) {
    const code = err && err.code;
    if (code === "declined") { state.subMsg = "已取消导出。"; render(); return; }
    if (code === "rate_limited") { state.subMsg = "刚刚有一个保存提示还没处理完，稍等再试。"; render(); return; }
    // 其余错误码一律退回剪贴板
  }
  try {
    await navigator.clipboard.writeText(payload);
    state.subMsg = "本环境无法直接保存文件，已复制到剪贴板，粘贴到文本文件另存为 .json 即可。";
  } catch (err2) {
    state.subMsg = "本环境既不能保存也不能访问剪贴板。请手动誊写表单内容发给维护者。";
  }
  render();
}

function refreshChecks() {
  const box = document.querySelector(".ckl");
  if (!box) return;
  const ck = subChecks();
  const list = D.sub.review_checklist;
  box.innerHTML = list.map(c => `<div class="ckrow ${ck[c.id] ? "ok" : (c.blocking ? "bad" : "warn")}">
    <span class="ci">${ck[c.id] ? "✓" : (c.blocking ? "○" : "–")}</span>
    <span><b>${esc(c.name_zh)}</b>${c.blocking ? "" : "（不阻断）"}
    <span class="cq">${esc(c.ask_zh)}</span>
    <span class="cw">${esc(c.why_zh)}</span></span></div>`).join("");
  const btn = document.querySelector("[data-export-sub]");
  if (btn) {
    const ok = list.filter(c => c.blocking).every(c => ck[c.id]);
    btn.disabled = !ok;
    btn.textContent = ok ? "导出投稿 JSON" : "先补齐上面的阻断项";
  }
}

function render() {
  document.getElementById("tabs").innerHTML = TABS.map(([id, name]) =>
    `<button role="tab" aria-selected="${state.tab === id}" data-tab="${id}">${name}</button>`).join("");

  const m = machineById(state.machine);
  document.getElementById("csys").textContent = m
    ? m.control_systems.map(c => D.controlSystems[c].name_zh).join(" / ") : "全部机型";

  document.getElementById("view").innerHTML = (TABS.find(t => t[0] === state.tab)[2])();
}

function init() {
  const sel = document.getElementById("machine");
  sel.innerHTML = `<option value="all">全部机型</option>` +
    D.machines.map(m => `<option value="${m.id}">${m.name}</option>`).join("");
  sel.value = state.machine;
  sel.addEventListener("change", e => {
    state.machine = e.target.value;
    state.diag = { cat: null, caseId: null };
    persist(); render();
  });

  const form = () => document.getElementById("chat-form");
  document.addEventListener("submit", e => {
    if (!e.target.matches("#chat-form")) return;
    e.preventDefault();
    const input = document.getElementById("chat-in");
    const v = input.value.trim();
    if (!v) return;
    input.value = "";
    ask(v);
  });

  document.addEventListener("click", e => {
    const t = e.target.closest("[data-tab],[data-cat],[data-open],[data-iv],[data-diag-cat],[data-diag-case],[data-diag-back],[data-unlock],[data-say],[data-clar],[data-clear-chat],[data-goto-case],[data-mic],[data-speak],[data-autospeak],[data-export-sub],[data-clear-sub]");
    if (!t) return;
    const d = t.dataset;
    if (d.exportSub) { state.subMsg = "正在准备导出…"; render(); exportSubmission(); return; }
    if (d.clearSub) {
      Object.keys(F).forEach(k => { F[k] = (k === "role") ? "机长" : (k === "fixable") ? "onsite" : (k === "unsafe") ? false : ""; });
      state.subMsg = ""; render(); return;
    }
    if (d.mic) { startVoice(); return; }
    if (d.speak) {
      const entry = [...D.cases, ...D.faultCodes].find(x => x.id === d.speak);
      if (entry) speak(entry);
      return;
    }
    if (d.autospeak) {
      state.voice.autoSpeak = !state.voice.autoSpeak;
      if (!state.voice.autoSpeak && VOICE_OUT) {
        try { window.speechSynthesis.cancel(); } catch (err) { /* 忽略 */ }
        state.voice.speaking = null;
      }
      persist(); render();
      return;
    }
    if (d.say) { ask(d.say); return; }
    if (d.clearChat) { stopVoice(); if (VOICE_OUT) { try { window.speechSynthesis.cancel(); } catch (err) {} }
      state.voice.speaking = null; state.chat = []; render(); return; }
    if (d.clar) {
      const c = SYN.clarifiers.find(x => x.id === d.clar);
      const opt = c && c.options.find(o => o.label_zh === d.optlabel);
      if (opt) ask(d.optlabel, opt.adds);
      return;
    }
    if (d.gotoCase) {
      state.tab = "cases"; state.cat.cases = "all"; state.q.cases = "";
      state.open["k" + d.gotoCase] = true;
      render();
      const el = document.querySelector(`[data-open="k${d.gotoCase}"]`);
      if (el) el.scrollIntoView({ block: "center" });
      return;
    }
    if (d.tab) state.tab = d.tab;
    else if (d.cat) state.cat[d.scope] = d.cat;
    else if (d.open) state.open[d.open] = !state.open[d.open];
    else if (d.iv) state.interval = d.iv;
    else if (d.diagCat) state.diag.cat = d.diagCat;
    else if (d.diagCase) state.diag.caseId = d.diagCase;
    else if (d.diagBack) state.diag = d.diagBack === "cat" ? { cat: null, caseId: null } : { ...state.diag, caseId: null };
    else if (d.unlock) state.unlocked = true;
    render();
  });

  document.addEventListener("change", e => {
    const ds = e.target.dataset || {};
    if (ds.f) {
      const el = e.target;
      F[ds.f] = el.type === "checkbox" ? el.checked : el.value;
      if (ds.f === "machine") F.csys = "";
      // 只有影响联动显示的控件才整页重绘。文本框在此重绘会有真实后果：
      // 用户从一个字段点向下一个字段时，change 先于 focus 触发，重绘会摧毁
      // 即将获得焦点的元素，导致焦点丢失、首次按键落空。
      if (el.tagName === "SELECT" || el.type === "checkbox") render();
      else refreshChecks();
      return;
    }
    if (!ds.chk) return;
    state.checked[ds.chk] = e.target.checked;
    persist(); render();
  });

  document.addEventListener("input", e => {
    const ds = e.target.dataset || {};
    // 文本框逐字重绘会丢焦点，因此只更新自检清单和按钮状态
    if (ds.f && e.target.tagName !== "SELECT" && e.target.type !== "checkbox") {
      F[ds.f] = e.target.value;
      refreshChecks();
      return;
    }
    const id = e.target.id;
    if (id !== "q-codes" && id !== "q-cases") return;
    const scope = id.slice(2);
    state.q[scope] = e.target.value;
    const pos = e.target.selectionStart;
    render();
    const again = document.getElementById(id);
    if (again) { again.focus(); again.setSelectionRange(pos, pos); }
  });

  render();
}

init();
</script>
"""


# Google Fonts 在中国大陆不可达。默认改为非阻塞加载：拿不到就立刻用系统字体渲染，
# 绝不让首屏等待一个必然超时的请求。--no-webfonts 则完全不发这个请求。
FONT_LINK = (
    '<link rel="stylesheet" media="print" onload="this.media=\'all\'" '
    'href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600;700'
    '&family=IBM+Plex+Mono:wght@400;600&family=Noto+Sans+SC:wght@400;500;700&display=swap">'
)


def customer_banner(name: str, build_id: str) -> str:
    """给单个客户的授权标识。让分发可追溯，且看起来是为他定制的。"""
    return f'''<style>
.lic{{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;
  font-size:11.5px;color:var(--ink-3);padding:7px 16px;background:var(--sunk);
  border-bottom:1px solid var(--line);letter-spacing:.02em}}
.lic b{{color:var(--ink-2);font-weight:600}}
</style>
<div class="lic"><span>授权给 <b>{name}</b> 内部使用</span><span class="mono">{build_id}</span></div>'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--out", type=Path, default=KB_DIR / "demo.html")
    parser.add_argument("--customer", help="客户名称，生成带授权标识的专属版本")
    parser.add_argument("--no-webfonts", action="store_true",
                        help="完全不请求 Google Fonts，生成零外部请求的版本")
    args = parser.parse_args()

    payload = json.dumps(build_payload(), ensure_ascii=False, separators=(",", ":"))
    # 防止数据中出现的 "</script>" 提前闭合脚本块
    payload = payload.replace("<", "\\u003c")

    html = TEMPLATE.replace("__DATA__", payload)
    html = html.replace("__FONTS__", "" if args.no_webfonts else FONT_LINK)

    if args.customer:
        build_id = datetime.now().strftime("%Y%m%d") + "-" + \
            hashlib.sha1(args.customer.encode("utf-8")).hexdigest()[:6]
        banner = customer_banner(args.customer, build_id)
        # 插在 <header> 之前，任何页签都能看到
        html = html.replace("<header>", banner + "\n<header>", 1)

    args.out.write_text(html, encoding="utf-8")
    size = args.out.stat().st_size
    tag = f"，授权 {args.customer}" if args.customer else ""
    ext = "无外部请求" if args.no_webfonts else "字体非阻塞加载"
    print(f"已生成 {args.out}（{size / 1024:.1f} KB，{ext}{tag}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
