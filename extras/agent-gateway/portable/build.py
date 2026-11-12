#!/usr/bin/env python3
"""Verify and rebuild the immutable feedback delivery without Docker or Git."""
import hashlib, json, os, pathlib, subprocess, tarfile, tempfile
root = pathlib.Path(__file__).resolve().parent
expected = dict(line.split(None, 1)[::-1] for line in (root / "SHA256SUMS").read_text().splitlines())
def check(path, digest):
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise SystemExit(f"checksum mismatch: {path}")
for name in ("source-snapshot.tar.gz", "source-manifest.json"):
    check(root / name, expected[name])
if subprocess.check_output(["go", "env", "GOVERSION"], text=True).strip() != "go1.27.3":
    raise SystemExit("Install Go 1.27.3 and put its bin directory first in PATH")
out = root / "out"
out.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="gateway-build-") as tmp:
    with tarfile.open(root / "source-snapshot.tar.gz") as archive:
        archive.extractall(tmp, filter="data")
    src = pathlib.Path(tmp) / "agent-gateway"
    manifest = json.loads((root / "source-manifest.json").read_text())
    actual = {str(p.relative_to(src)) for p in src.rglob("*") if p.is_file()}
    if actual != set(manifest["source_files"]) | {"source-manifest.json"}:
        raise SystemExit("archive file set differs from manifest")
    check(src / "source-manifest.json", expected["source-manifest.json"])
    for name, digest in manifest["source_files"].items():
        check(src / name, digest)
    for arch in ("amd64", "arm64"):
        env = dict(os.environ, GOOS="linux", GOARCH=arch, CGO_ENABLED="0",
                   GOTOOLCHAIN="local", GOENV="off", GOFLAGS="", GOPROXY="off",
                   GOAMD64="v1", GOARM64="v8.0", GOEXPERIMENT="")
        for command in ("agent-gateway", "agentctl", "gateway-healthcheck"):
            name = f"{command}-linux-{arch}"
            subprocess.run(["go", "build", "-trimpath", "-buildvcs=false", "-o",
                            str(out / name), f"./cmd/{command}"], cwd=src, env=env, check=True)
            check(out / name, expected[name])
            print(f"verified {name}")
print("All six binaries match the original feedback delivery")
