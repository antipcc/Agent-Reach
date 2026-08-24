#!/usr/bin/env python3
"""校验海德堡知识库数据文件的引用完整性与收录纪律。

只依赖标准库，可脱离 Agent Reach 独立运行（这套数据将来可能整体迁出到自己的仓库）：

    python docs/heidelberg-kb/validate.py

退出码 0 表示全部通过，1 表示存在错误。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterator

KB_DIR = Path(__file__).parent

# 收录纪律：故障码表禁止出现未核实条目——机长按图索骥查不到，是这类产品最快的失信方式。
CONFIDENCE_BANNED_IN_FAULT_CODES = {"unverified"}

# machines 字段允许的通配值，表示与机型无关的通用机械/工艺问题。
MACHINE_WILDCARD = "*"


def load(name: str) -> dict[str, Any]:
    path = KB_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def iter_entries(data: dict[str, Any], *keys: str) -> Iterator[tuple[str, dict[str, Any]]]:
    """遍历数据文件中若干个条目列表，产出 (来源列表名, 条目)。"""
    for key in keys:
        for entry in data.get(key, []):
            yield key, entry


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

        self.sources = load("sources.json")
        self.machines = load("machines.json")
        self.fault_codes = load("fault-codes.json")
        self.cases = load("cases.json")
        self.maintenance = load("maintenance.json")

        self.source_ids = {s["id"] for s in self.sources["sources"]}
        self.machine_ids = {m["id"] for m in self.machines["machines"]}
        self.control_system_ids = {c["id"] for c in self.machines["control_systems"]}
        self.category_ids = {c["id"] for c in self.machines["categories"]}
        self.confidence_ids = {c["id"] for c in self.machines["confidence_levels"]}
        self.interval_ids = {i["id"] for i in self.maintenance["intervals"]}
        self.fixable_ids = {f["id"] for f in self.cases["field_fixable_levels"]}

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")

    def check_sources(self, where: str, entry: dict[str, Any], required: bool = True) -> None:
        refs = entry.get("sources", [])
        if required and not refs:
            self.err(where, "缺少 sources —— 每条数据都必须能追溯到公开来源")
            return
        for ref in refs:
            if ref not in self.source_ids:
                self.err(where, f"引用了不存在的来源 id: {ref!r}")

    def check_enum(self, where: str, entry: dict[str, Any], field: str,
                   allowed: set[str], required: bool = True) -> None:
        value = entry.get(field)
        if value is None:
            if required:
                self.err(where, f"缺少必填字段 {field}")
            return
        values = value if isinstance(value, list) else [value]
        for v in values:
            if v not in allowed:
                self.err(where, f"{field} 取值 {v!r} 不在允许范围内")

    def check_machines(self, where: str, entry: dict[str, Any]) -> None:
        values = entry.get("machines")
        if not values:
            self.err(where, "缺少必填字段 machines")
            return
        for v in values:
            if v != MACHINE_WILDCARD and v not in self.machine_ids:
                self.err(where, f"machines 取值 {v!r} 未在 machines.json 中定义")

    def check_generation_consistency(self, where: str, entry: dict[str, Any]) -> None:
        """核心校验：条目声明的控制系统必须与其声明的机型实际配备的世代相符。

        这条规则专门防止“把 CP2000 时代的报警挂到 XL 106 上”这类跨代错配——
        它是同类产品里最常见、也最伤信誉的内容错误。
        """
        systems = entry.get("control_systems")
        machines = entry.get("machines", [])
        if not systems or MACHINE_WILDCARD in machines:
            return

        by_id = {m["id"]: m for m in self.machines["machines"]}
        for machine_id in machines:
            machine = by_id.get(machine_id)
            if machine is None:
                continue  # 已由 check_machines 报错
            supported = set(machine.get("control_systems", []))
            for system in systems:
                if system not in supported:
                    self.err(
                        where,
                        f"世代错配：{machine['name']} 不使用 {system}"
                        f"（其支持的控制系统为 {sorted(supported)}）",
                    )

    def validate_fault_codes(self) -> None:
        seen: set[str] = set()
        for rule in self.fault_codes.get("decoding_rules", []):
            where = f"fault-codes/decoding_rules/{rule.get('id', '?')}"
            self.check_sources(where, rule)
            self.check_enum(where, rule, "confidence", self.confidence_ids)
            self.check_enum(where, rule, "applies_to", self.control_system_ids)

        for entry in self.fault_codes["entries"]:
            eid = entry.get("id", "?")
            where = f"fault-codes/{eid}"

            if eid in seen:
                self.err(where, "id 重复")
            seen.add(eid)

            for field in ("code", "title_zh", "meaning_zh", "checks"):
                if not entry.get(field):
                    self.err(where, f"缺少必填字段 {field}")

            self.check_sources(where, entry)
            self.check_enum(where, entry, "category", self.category_ids)
            self.check_enum(where, entry, "severity", {"stop", "warning", "info"})
            self.check_enum(where, entry, "confidence", self.confidence_ids)
            self.check_enum(where, entry, "control_systems", self.control_system_ids)
            self.check_machines(where, entry)
            self.check_generation_consistency(where, entry)

            if entry.get("confidence") in CONFIDENCE_BANNED_IN_FAULT_CODES:
                self.err(where, "故障码表禁止收录 unverified 条目（收录纪律）")

        declared = self.fault_codes.get("entry_count")
        actual = len(self.fault_codes["entries"])
        if declared != actual:
            self.err("fault-codes", f"entry_count 声明 {declared} 与实际 {actual} 不符")

    def validate_cases(self) -> None:
        seen: set[str] = set()
        for entry in self.cases["entries"]:
            eid = entry.get("id", "?")
            where = f"cases/{eid}"

            if eid in seen:
                self.err(where, "id 重复")
            seen.add(eid)

            for field in ("title_zh", "symptom_zh", "causes"):
                if not entry.get(field):
                    self.err(where, f"缺少必填字段 {field}")

            self.check_sources(where, entry)
            self.check_enum(where, entry, "category", self.category_ids)
            self.check_enum(where, entry, "confidence", self.confidence_ids)
            self.check_enum(where, entry, "field_fixable", self.fixable_ids)
            self.check_enum(where, entry, "control_systems", self.control_system_ids, required=False)
            self.check_machines(where, entry)
            self.check_generation_consistency(where, entry)

            eta = entry.get("eta_minutes")
            if not (isinstance(eta, list) and len(eta) == 2 and eta[0] <= eta[1]):
                self.err(where, "eta_minutes 必须是 [下限, 上限] 且下限不大于上限")

            # 原因必须按概率由高到低排列，强制“先查高概率项”的排查纪律。
            order = {"high": 0, "medium": 1, "low": 2}
            ranks = []
            for cause in entry["causes"]:
                likelihood = cause.get("likelihood")
                if likelihood not in order:
                    self.err(where, f"causes.likelihood 取值 {likelihood!r} 非法")
                    continue
                if not cause.get("fix_zh"):
                    self.err(where, f"原因 {cause.get('cause_zh', '?')!r} 缺少 fix_zh")
                ranks.append(order[likelihood])
            if ranks != sorted(ranks):
                self.err(where, "causes 未按 likelihood 由高到低排列")

        declared = self.cases.get("entry_count")
        actual = len(self.cases["entries"])
        if declared != actual:
            self.err("cases", f"entry_count 声明 {declared} 与实际 {actual} 不符")

    def validate_maintenance(self) -> None:
        seen: set[str] = set()
        for entry in self.maintenance["entries"]:
            eid = entry.get("id", "?")
            where = f"maintenance/{eid}"

            if eid in seen:
                self.err(where, "id 重复")
            seen.add(eid)

            if not entry.get("title_zh"):
                self.err(where, "缺少必填字段 title_zh")

            self.check_sources(where, entry)
            self.check_enum(where, entry, "interval", self.interval_ids)
            self.check_enum(where, entry, "category", self.category_ids)
            self.check_enum(where, entry, "confidence", self.confidence_ids)
            self.check_enum(where, entry, "control_systems", self.control_system_ids, required=False)
            self.check_machines(where, entry)
            self.check_generation_consistency(where, entry)

        for part in self.maintenance["wear_parts"]:
            where = f"maintenance/wear_parts/{part.get('id', '?')}"
            self.check_sources(where, part)
            self.check_enum(where, part, "category", self.category_ids)

        self.check_sources("maintenance/lubrication_color_code",
                           self.maintenance["lubrication_color_code"])

        declared = self.maintenance.get("entry_count")
        actual = len(self.maintenance["entries"])
        if declared != actual:
            self.err("maintenance", f"entry_count 声明 {declared} 与实际 {actual} 不符")

    def validate_sources(self) -> None:
        seen: set[str] = set()
        for source in self.sources["sources"]:
            sid = source.get("id", "?")
            where = f"sources/{sid}"
            if sid in seen:
                self.err(where, "id 重复")
            seen.add(sid)
            for field in ("title", "url", "type", "accessed"):
                if not source.get(field):
                    self.err(where, f"缺少必填字段 {field}")
            url = source.get("url", "")
            if not url.startswith(("http://", "https://")):
                self.err(where, f"url 格式不正确: {url!r}")

        # 未被任何条目引用的来源不是错误，但值得提示——可能是漏挂了引用。
        used: set[str] = set()
        for data, keys in (
            (self.fault_codes, ("entries", "decoding_rules")),
            (self.cases, ("entries",)),
            (self.maintenance, ("entries", "wear_parts")),
        ):
            for _, entry in iter_entries(data, *keys):
                used.update(entry.get("sources", []))
        used.update(self.maintenance["lubrication_color_code"].get("sources", []))
        for machine in self.machines["machines"] + self.machines["control_systems"]:
            used.update(machine.get("sources", []))

        for unused in sorted(self.source_ids - used):
            self.warn("sources", f"来源 {unused!r} 未被任何条目引用")

    def run(self) -> int:
        self.validate_sources()
        self.validate_fault_codes()
        self.validate_cases()
        self.validate_maintenance()

        counts = {
            "故障码": len(self.fault_codes["entries"]),
            "解码规则": len(self.fault_codes["decoding_rules"]),
            "案例": len(self.cases["entries"]),
            "保养项": len(self.maintenance["entries"]),
            "易损件": len(self.maintenance["wear_parts"]),
            "来源": len(self.sources["sources"]),
            "机型": len(self.machines["machines"]),
        }
        print("数据统计: " + " | ".join(f"{k} {v}" for k, v in counts.items()))

        by_confidence: dict[str, int] = {}
        for data, keys in ((self.fault_codes, ("entries",)), (self.cases, ("entries",))):
            for _, entry in iter_entries(data, *keys):
                c = entry.get("confidence", "?")
                by_confidence[c] = by_confidence.get(c, 0) + 1
        print("置信度分布: " + " | ".join(f"{k} {v}" for k, v in sorted(by_confidence.items())))

        for warning in self.warnings:
            print(f"[warn]  {warning}")
        for error in self.errors:
            print(f"[error] {error}")

        if self.errors:
            print(f"\n校验失败：{len(self.errors)} 个错误、{len(self.warnings)} 个提示")
            return 1
        print(f"\n校验通过：0 个错误、{len(self.warnings)} 个提示")
        return 0


if __name__ == "__main__":
    sys.exit(Validator().run())
