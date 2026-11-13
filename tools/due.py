"""Cheap check before the heavy setup: is a video needed now? Prints go=true/false for GitHub Actions."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ytauto import history  # noqa: E402

hours = float(sys.argv[1]) if len(sys.argv) > 1 else 10
go = history.slot_due(hours)
print(f"next slot {history.next_slot()}, due within {hours} h: {go}")
with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
    f.write(f"go={'true' if go else 'false'}\n")
