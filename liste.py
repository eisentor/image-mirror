#!/usr/bin/env python3
"""Spiegel-Liste: fremde, per Digest gepinnte Images aus dem privaten Quell-Repo.

Liest die Quellen eines Checkouts (Argument: Pfad) und gibt je Image eine Zeile aus:

    <quelle>\t<ziel-repo>\t<tag>\t<digest>

Regeln (bewusst eng, damit nie ein eigenes Image hier landet):
- nur Referenzen mit @sha256-Digest (Kopie nach Digest, unverändert);
- nur Registries aus ERLAUBT (Allowlist): jede andere, auch die eigene, ist
  ausgeschlossen, ebenso ghcr.io (ohne Limit direkt erreichbar);
- Ziel = ghcr.io/eisentor/mirror/<registry>/<pfad> (gleiches Schema wie der
  interne Cache), kein frei wählbarer Name.

Quellen ohne feste Pfade: alle Dockerfile* (FROM, ARG-Standardwerte aufgelöst),
compose*.yaml im selben Ordner wie ein Dockerfile, *.sh (wörtliche Docker-Hub-Pins).

Prüfung: python3 -m unittest test_liste.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ZIEL = "ghcr.io/eisentor/mirror"
ERLAUBT = ("docker.io", "lscr.io", "codeberg.org", "data.forgejo.org", "nvcr.io", "quay.io")
DOCKER_HUB = ("docker.io", "index.docker.io", "registry-1.docker.io")


FROM = re.compile(r"^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)", re.I | re.M)
IMAGE = re.compile(r"^\s*image:\s*(\S+)", re.M)
ARG = re.compile(r"^\s*ARG\s+([A-Za-z_]\w*)=(\S+)", re.M)
LITERAL = re.compile(r"docker\.io/library/[a-z0-9._-]+:[\w.-]+@sha256:[0-9a-f]{64}")
REF = re.compile(r"^(?P<name>[a-z0-9][a-z0-9._/:-]*?):(?P<tag>[\w][\w.-]*)@(?P<digest>sha256:[0-9a-f]{64})$")


def aufloesen(text: str, args: dict[str, str]) -> str:
    """${A:+@${B}}, ${A:-x}, ${A}, $A mit ARG-Standardwerten ersetzen."""
    text = re.sub(r"\$\{(\w+):\+@\$\{(\w+)\}\}", lambda m: "@" + args[m[2]] if args.get(m[1]) else "", text)
    text = re.sub(r"\$\{(\w+)(?::?-([^}]*))?\}", lambda m: args.get(m[1], m[2] or "${" + m[1] + "}"), text)
    return re.sub(r"\$(\w+)", lambda m: args.get(m[1], m[0]), text)


def registry(name: str) -> tuple[str, str]:
    """(registry, pfad); Docker Hub normalisiert auf docker.io/library/…"""
    first, sep, rest = name.partition("/")
    if sep and ("." in first or ":" in first or first == "localhost"):
        reg, path = first, rest
    else:
        reg, path = "docker.io", name
    if reg in DOCKER_HUB:
        reg = "docker.io"
        if "/" not in path:
            path = "library/" + path
    return reg, path


def eintrag(ref: str) -> tuple[str, str, str, str] | None:
    m = REF.match(ref)
    if not m:
        return None
    reg, path = registry(m["name"])
    if reg not in ERLAUBT:
        return None
    return f"{reg}/{path}:{m['tag']}@{m['digest']}", f"{ZIEL}/{reg}/{path}", m["tag"], m["digest"]


def dateien(root: Path, muster: str) -> list[Path]:
    return sorted(f for f in root.rglob(muster) if f.is_file() and ".git" not in f.relative_to(root).parts)


def referenzen(root: Path) -> list[str]:
    refs: list[str] = []
    ordner = set()
    for f in dateien(root, "Dockerfile*"):
        ordner.add(f.parent)
        text = f.read_text(encoding="utf-8")
        args = dict(ARG.findall(text))
        refs += [aufloesen(r, args) for r in FROM.findall(text)]
    for d in sorted(ordner):
        for f in sorted(d.glob("compose*.y*ml")):
            refs += IMAGE.findall(f.read_text(encoding="utf-8"))
    for f in dateien(root, "*.sh"):
        refs += LITERAL.findall(f.read_text(encoding="utf-8"))
    return refs


def liste(root: Path) -> list[tuple[str, str, str, str]]:
    out = {}
    for r in referenzen(root):
        e = eintrag(r)
        if e:
            out[e[0]] = e
        elif "@sha256:" in r:
            print(f"übersprungen (nicht in der Allowlist): {r}", file=sys.stderr)
    return sorted(out.values())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Aufruf: liste.py <checkout des Quell-Repos>")
    for e in liste(Path(sys.argv[1])):
        print("\t".join(e))
