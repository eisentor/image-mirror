import tempfile
import unittest
from pathlib import Path

import liste

D = "sha256:" + "a" * 64


class Test(unittest.TestCase):
    def test_docker_hub_library(self):
        self.assertEqual(
            liste.eintrag(f"python:3.14.10-slim@{D}"),
            (f"docker.io/library/python:3.14.10-slim@{D}", "ghcr.io/eisentor/mirror/docker.io/library/python", "3.14.10-slim", D),
        )

    def test_fremde_registry(self):
        e = liste.eintrag(f"nvcr.io/nvidia/k8s/container-toolkit:v1.19.1@{D}")
        self.assertEqual(e[1], "ghcr.io/eisentor/mirror/nvcr.io/nvidia/k8s/container-toolkit")

    def test_eigene_und_ghcr_nie(self):
        for r in (
            f"git.example.work/owner/app:1.0.0@{D}",
            f"mirror:5000/ci/push/x:1@{D}",
            f"ghcr.io/eisentor/mirror/docker.io/library/python:3@{D}",
            f"ghcr.io/project-zot/zot-linux-amd64:v2.1.23@{D}",
            f"localhost:5000/x:1@{D}",
            f"example.com/x:1@{D}",
        ):
            self.assertIsNone(liste.eintrag(r), r)

    def test_ohne_digest_nie(self):
        self.assertIsNone(liste.eintrag("python:3.14"))
        self.assertIsNone(liste.eintrag("forgejo-dsm:15.0.10"))

    def test_arg_aufloesen(self):
        args = {"V": "3.4.0", "DIG": D}
        self.assertEqual(
            liste.aufloesen("docker.io/paperlessngx/paperless-ngx:${V}${DIG:+@${DIG}}", args),
            f"docker.io/paperlessngx/paperless-ngx:3.4.0@{D}",
        )
        self.assertEqual(liste.aufloesen("codeberg.org/forgejo/forgejo:${V}@${DIG}", args), f"codeberg.org/forgejo/forgejo:3.4.0@{D}")
        self.assertIn("${BASE}", liste.aufloesen("${BASE}", args))

    def test_checkout(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "a").mkdir()
            (root / "a/Dockerfile").write_text(f"ARG V=1.0\nFROM alpine:3.24.3@{D} AS x\nFROM ${{BASE}}\nFROM codeberg.org/f/f:${{V}}@{D}\n")
            (root / "b").mkdir()
            (root / "b/compose.yaml").write_text(f"  image: docker.io/x/ohne-dockerfile:1@{D}\n")
            (root / "a/compose.yaml").write_text(
                f"  image: ${{P:-git.example.work/a/p:1}}\n  image: docker.io/gotenberg/gotenberg:8.39.0@{D}\n"
            )
            (root / "c").mkdir()
            (root / "c/lib.sh").write_text(
                f"N=${{N:-docker.io/library/node:22-bookworm@{D}}}\nP=${{P:-mcr.microsoft.com/playwright:v1.64.1-noble@{D}}}\n"
            )
            quellen = [e[0] for e in liste.liste(root)]
            self.assertEqual(
                quellen,
                [
                    f"codeberg.org/f/f:1.0@{D}",
                    f"docker.io/gotenberg/gotenberg:8.39.0@{D}",
                    f"docker.io/library/alpine:3.24.3@{D}",
                    f"docker.io/library/node:22-bookworm@{D}",
                    f"mcr.microsoft.com/playwright:v1.64.1-noble@{D}",
                ],
            )


if __name__ == "__main__":
    unittest.main()
