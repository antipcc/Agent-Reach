#!/usr/bin/env python3
"""Static sanity checks for the Woo sources.

Not a compiler. It catches the classes of mistake that are cheap to make and
expensive to discover in Xcode: unbalanced delimiters, a layering violation
(WooKit reaching for UIKit/SwiftUI), a type declared twice, or a file that
forgot its imports. Run it before opening the project:

    python3 apps/woo-ios/scripts/check-swift-hygiene.py
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "WooKit" / "Sources"
KIT_TESTS = ROOT / "WooKit" / "Tests"
APP = ROOT / "Woo"

# WooKit must stay Foundation-only so it builds and tests off-device.
FORBIDDEN_IN_KIT = {"SwiftUI", "UIKit", "AppKit", "Vision", "CoreImage", "AVFoundation", "Photos"}

# Symbols that only exist once a particular framework is imported. Missing one
# of these is the single most common way a file that reads fine fails to build.
# SwiftUI transitively exposes UIKit and Combine on iOS, so it satisfies both.
REQUIRED_IMPORTS = [
    (r"\bUIImage\b|\bUIColor\b|\bUIView\b|\bUIGraphicsImageRenderer\b|\bUIViewRepresentable\b",
     {"UIKit", "SwiftUI"}),
    (r"\bObservableObject\b|@Published", {"Combine", "SwiftUI"}),
    (r"\bAVCapture\w+|\bAVCaptureSession\b", {"AVFoundation"}),
    (r"\bVN[A-Z]\w+", {"Vision"}),
    (r"\bPH(?:Photo|Asset|Picker)\w*", {"Photos", "PhotosUI"}),
    (r"\bCIImage\b|\bCIContext\b", {"CoreImage", "UIKit"}),
    (r"\bCGImagePropertyOrientation\b", {"ImageIO", "Vision"}),
    (r"\bCGContext\b|\bCGRect\b|\bCGFloat\b|\bCGSize\b",
     {"CoreGraphics", "UIKit", "SwiftUI", "Foundation"}),
]


def strip_noise(source: str) -> str:
    """Blank out comments and string literals so delimiters inside them don't count."""
    out = []
    i, n = 0, len(source)
    while i < n:
        two = source[i : i + 2]
        if two == "//":
            j = source.find("\n", i)
            i = n if j == -1 else j
            continue
        if two == "/*":
            depth, i = 1, i + 2
            while i < n and depth:
                if source[i : i + 2] == "/*":
                    depth, i = depth + 1, i + 2
                elif source[i : i + 2] == "*/":
                    depth, i = depth - 1, i + 2
                else:
                    i += 1
            continue
        if source[i : i + 3] == '"""':
            j = source.find('"""', i + 3)
            i = n if j == -1 else j + 3
            continue
        if source[i] == '"':
            i += 1
            while i < n and source[i] != '"':
                i += 2 if source[i] == "\\" else 1
            i += 1
            continue
        out.append(source[i])
        i += 1
    return "".join(out)


def check_delimiters(path: Path, code: str) -> list[str]:
    pairs = {")": "(", "]": "[", "}": "{"}
    stack, problems = [], []
    for index, char in enumerate(code):
        if char in "([{":
            stack.append((char, index))
        elif char in ")]}":
            if not stack or stack[-1][0] != pairs[char]:
                line = code.count("\n", 0, index) + 1
                problems.append(f"{path}:{line}: unexpected '{char}'")
                break
            stack.pop()
    if stack:
        char, index = stack[0]
        line = code.count("\n", 0, index) + 1
        problems.append(f"{path}:{line}: '{char}' is never closed")
    return problems


def check_imports(path: Path, code: str, in_kit: bool) -> list[str]:
    problems = []
    imports = set(re.findall(r"^\s*import\s+(\w+)", code, re.MULTILINE))
    if in_kit:
        for banned in sorted(imports & FORBIDDEN_IN_KIT):
            problems.append(f"{path}: WooKit must stay Foundation-only, but imports {banned}")
        if not imports:
            problems.append(f"{path}: no imports at all — Foundation is missing")

    body = re.sub(r"^\s*import\s+\w+\s*$", "", code, flags=re.MULTILINE)
    for pattern, satisfied_by in REQUIRED_IMPORTS:
        if re.search(pattern, body) and not (imports & satisfied_by):
            problems.append(
                f"{path}: uses /{pattern}/ but imports none of {', '.join(sorted(satisfied_by))}"
            )
    return problems


DECLARATION = re.compile(
    r"^\s*(?:public\s+|internal\s+|private\s+|fileprivate\s+)?"
    r"(?:final\s+)?(?:struct|class|enum|actor|protocol)\s+(\w+)"
)


def collect_declarations(path: Path, code: str, table: dict[str, list[Path]]) -> None:
    """Record top-level type names only.

    Nested types legitimately share names across parents — every
    UIViewRepresentable has its own Coordinator — so only declarations at
    file scope can collide.
    """
    depth = 0
    for line in code.splitlines():
        if depth == 0:
            match = DECLARATION.match(line)
            if match:
                table[match.group(1)].append(path)
        depth += line.count("{") - line.count("}")


def main() -> int:
    problems: list[str] = []
    declarations: dict[str, list[Path]] = defaultdict(list)
    files = sorted(
        list(KIT.rglob("*.swift")) + list(APP.rglob("*.swift")) + list(KIT_TESTS.rglob("*.swift"))
    )

    if not files:
        print("no Swift sources found", file=sys.stderr)
        return 1

    for path in files:
        raw = path.read_text(encoding="utf-8")
        code = strip_noise(raw)
        rel = path.relative_to(ROOT)
        problems += check_delimiters(rel, code)
        problems += check_imports(rel, code, in_kit=KIT in path.parents)
        collect_declarations(rel, code, declarations)

    for name, paths in sorted(declarations.items()):
        # Extensions and nested types are filtered out by the regex, so a
        # repeat here is a genuine redeclaration.
        unique = sorted({str(p) for p in paths})
        if len(paths) > len(unique) or len(unique) > 1:
            problems.append(f"{name} is declared in more than one place: {', '.join(unique)}")

    for problem in problems:
        print(problem)
    print(f"checked {len(files)} Swift files, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
