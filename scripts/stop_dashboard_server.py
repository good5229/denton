from __future__ import annotations

import os
import signal
import subprocess
import sys


def pids_on_port(port: str) -> list[int]:
    completed = subprocess.run(
        ["lsof", "-ti", f"TCP:{port}", "-sTCP:LISTEN"],
        text=True,
        capture_output=True,
        check=False,
    )
    return [int(line) for line in completed.stdout.splitlines() if line.strip().isdigit()]


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else "8000"
    pids = pids_on_port(port)
    if not pids:
        print(f"no dashboard server listening on port {port}")
        return 0
    for pid in pids:
        os.kill(pid, signal.SIGTERM)
        print(f"stopped dashboard server pid={pid} port={port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
