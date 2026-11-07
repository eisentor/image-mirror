# image-mirror

Öffentliche, unveränderte Kopien fremder Images, die eine private CI braucht, unter

    ghcr.io/eisentor/mirror/<registry>/<pfad>:<tag>@<digest>

Zweck: Läufe ohne internen Cache ziehen nicht von Docker Hub (Limit 100 Pulls / 6 h)
und nicht von Registries, die in ihrer Umgebung gesperrt sind.

## Regeln
- Nur dieser Workflow (`.github/workflows/spiegeln.yml`) schreibt nach ghcr, mit dem
  `GITHUB_TOKEN` dieses Repos.
- Nur fremde Images, nur nach Digest (`liste.py`), Allowlist: `docker.io`, `lscr.io`,
  `codeberg.org`, `data.forgejo.org`, `nvcr.io`, `quay.io`, `mcr.microsoft.com`. Alles andere, auch eigene
  Registries und `ghcr.io` (direkt erreichbar), wird nie kopiert.
- Ziel = Quelle unter festem Präfix; keine frei wählbaren Namen. Bestehende Digests
  werden nicht neu kopiert; Images ab 4 GB (amd64, komprimiert) werden übersprungen.

## Quelle der Liste
Secret `QUELLE_LESEN`: fein eingeschränkter Token, nur Contents: read auf genau ein
privates Repo. Der Workflow ermittelt dieses Repo selbst und liest dessen
Standard-Branch: alle `Dockerfile*`, `compose*.yaml` neben einem Dockerfile und
wörtliche Pins (Docker Hub, mcr.microsoft.com) in `*.sh`.

Läufe: bei Push auf main, täglich 03:17 UTC, per «Run workflow».

## Einmalig nach dem ersten Lauf
Neue Pakete sind privat: unter github.com/eisentor?tab=packages je Paket
`mirror/…` → Package settings → «Change visibility» → Public.

## Prüfung
    python3 -m unittest -v test_liste.py
