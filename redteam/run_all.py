"""One CPU job; preserve all original tracked scoring files and large output."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
from run_trial import NAMES


def main():
    backup = ROOT / "redteam/.work/original"
    backup.mkdir(parents=True, exist_ok=True)
    changed = ["outputs/method_results.json", "scoring/scores_train.json", "scoring/scores_test.json"]
    for name in changed:
        target = backup / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() and (ROOT / name).exists():
            shutil.copy2(ROOT / name, target)
    failures = []
    try:
        selected = sys.argv[1:] or NAMES
        if any(name not in NAMES for name in selected):
            raise ValueError(selected)
        for name in selected:
            # Separate method/scoring interpreters; no persistent monkeypatches.
            result = subprocess.run(["bash", f"redteam/{name}/run.sh"])
            if result.returncode:
                failures.append({"name": name, "returncode": result.returncode})
        result = subprocess.run([sys.executable, "redteam/summarize.py"])
        if result.returncode:
            failures.append({"name": "summarize", "returncode": result.returncode})
        (ROOT / "redteam/job_status.json").write_text(json.dumps({
            "last_job_trials": selected, "unexpected_failures": failures}, indent=2))
    finally:
        for name in changed:
            if (backup / name).exists():
                shutil.copy2(backup / name, ROOT / name)
        base = (ROOT / "redteam/base_commit.txt").read_text().strip()
        original_runner = subprocess.check_output(["git", "show", f"{base}:scripts/run.sh"])
        # Bash may still have the submitted runner open. Replacing its inode
        # avoids making Bash read unrelated bytes from the restored script.
        restored_runner = ROOT / "redteam/.work/restored_run.sh"
        restored_runner.write_bytes(original_runner)
        restored_runner.chmod((ROOT / "scripts/run.sh").stat().st_mode)
        os.replace(restored_runner, ROOT / "scripts/run.sh")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
