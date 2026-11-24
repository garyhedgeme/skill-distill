#!/usr/bin/env python3
"""Grade a cheap model's layout pass. The reference must pass the same checks."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BOX = set("┌┐└┘├┤┬┴─│┼")
CRUMBS = {
    "10",
    "8",
    "GitHub",
    "GitHub+1",
    "Orca Docs",
    "The agent development environment+1",
}
MARK = re.compile(r"<<<\s*FILE\s+(\S+)\s*>>>\s*(.*?)<<<\s*END\s*>>>", re.S | re.I)


def outside_fences(text: str) -> str:
    parts = text.split("```")
    return "".join(parts[i] for i in range(0, len(parts), 2))


def parse_stdout(raw: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for name, body in MARK.findall(raw):
        found[Path(name).name] = body.strip("\n") + "\n"
    return found


def check(name: str, text: str, original: str) -> list[str]:
    bad: list[str] = []
    def letters(body: str) -> int:
        body = re.sub(r"https?://\S+", "", body)
        return sum(ch.isalpha() for ch in body)

    orig_letters = letters(original)
    got_letters = letters(text)
    if orig_letters and got_letters < int(orig_letters * 0.9):
        bad.append(f"мало букв ({got_letters}/{orig_letters})")
    bare = outside_fences(text)
    if any(ch in bare for ch in BOX):
        bad.append("рамка вне блока кода")
    if "| ----- |" in text:
        bad.append("осталась строка | ----- |")
    first = text.splitlines()[0] if text.splitlines() else ""
    if len(first) > 80 or any(ch in first for ch in BOX) or first.startswith("#"):
        bad.append(f"первая строка не название: {first[:70]!r}")
    for crumb in CRUMBS:
        if any(line.strip() == crumb for line in text.splitlines()):
            bad.append(f"мусор {crumb!r}")
    if "images.openai.com" in text:
        bad.append("ссылка на картинку openai")
    if "п=рименил" in text:
        bad.append("осталась опечатка п=рименил")
    if name == "board.md":
        for needle in (
            "Что ещё лежит в Board",
            "Список составлен по дереву репозитория vercel/board",
            "reproduce-bug",
            "configure-factory-board",
            "Наш swarm повторяет templates/swarm",
        ):
            if needle not in text:
                bad.append(f"пропало: {needle}")
        if "| Скилл Board |" not in text and "Скилл Board" not in text.split("|")[0]:
            if "Скилл Board" not in text:
                bad.append("нет шапки Скилл Board")
    if name == "steps.md":
        for needle in (
            "vb tasks create",
            "ready-for-agent",
            "you bring",
            "needs_input",
            "patrol-daily",
            "Рождение",
        ):
            if needle not in text:
                bad.append(f"пропало: {needle}")
        rows = [ln for ln in text.splitlines() if ln.startswith("|")]
        if len(rows) < 15:
            bad.append(f"в таблице шагов строк {len(rows)}, нужно ≥15")
    if name == "herdr.md":
        for needle in (
            "В предложенной конфигурации",
            "Background Server",
            "Возможность",
            "Browser / Design Mode",
            "Research OS",
            "Human Management",
            "execution_backends",
            "Task dispatch",
            "Thern",
            "применил",
        ):
            if needle not in text:
                bad.append(f"пропало: {needle}")
        if text.count("```") < 6:
            bad.append("нет трёх блоков кода")
        if not text.lstrip().startswith("Herdr") and "Herdr" not in first:
            bad.append("в названии нет Herdr")
    return bad


def grade_dir(model_dir: Path, originals: dict[str, str]) -> tuple[bool, list[str]]:
    stdout = (model_dir / "stdout.txt").read_text(errors="replace") if (model_dir / "stdout.txt").exists() else ""
    parsed = parse_stdout(stdout)
    lines: list[str] = []
    ok = True
    for name, original in originals.items():
        text = parsed.get(name)
        if text is None:
            ok = False
            lines.append(f"{name}: нет маркера")
            continue
        (model_dir / name).write_text(text)
        bad = check(name, text, original)
        if bad:
            ok = False
            lines.append(f"{name}: " + "; ".join(bad))
        else:
            lines.append(f"{name}: ok")
    return ok, lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("model_dir", type=Path)
    ap.add_argument("--originals", type=Path, required=True)
    args = ap.parse_args()
    originals = {
        "board.md": (args.originals / "board.md").read_text(),
        "steps.md": (args.originals / "steps.md").read_text(),
        "herdr.md": (args.originals / "herdr.md").read_text(),
    }
    # The reference layout, if present, must pass too.
    ref = args.originals / "reference"
    if ref.is_dir() and (ref / "herdr.md").exists():
        for name, original in originals.items():
            bad = check(name, (ref / name).read_text(), original)
            if bad:
                print(f"REF {name}: " + "; ".join(bad))
                return 2
        print("REF ok")
    ok, lines = grade_dir(args.model_dir, originals)
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
