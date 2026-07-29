"""Run every pty_uxn_*.py test in this directory as a subprocess and
report pass/fail. Requires bin/writhdeck.rom to already be built
(`make rom`).
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
tests = sorted(HERE.glob("pty_uxn_*.py"))

failed = []
for t in tests:
    print(f"\n----- {t.name} -----")
    result = subprocess.run([sys.executable, str(t)], cwd=HERE)
    if result.returncode != 0:
        failed.append(t.name)

print("\n" + "=" * 40)
if failed:
    print(f"FAILED: {', '.join(failed)}")
    sys.exit(1)
print(f"ALL {len(tests)} TEST FILES PASSED")
