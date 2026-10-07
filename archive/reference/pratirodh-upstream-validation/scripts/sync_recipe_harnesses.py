"""Sync harness files into recipe.json and provide target reconstruction."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RECIPES = ROOT / "benchmark" / "recipes"

def sync_all():
    count = 0
    for recipe_dir in sorted(RECIPES.iterdir()):
        if not recipe_dir.is_dir():
            continue
        recipe_json_path = recipe_dir / "recipe.json"
        if not recipe_json_path.exists():
            continue
        target_dir = recipe_dir / "target"
        if not target_dir.exists():
            continue

        recipe = json.loads(recipe_json_path.read_text(encoding="utf-8"))
        harness_files = recipe.get("harness_files", {})

        # 1. Untracked files
        proc_untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=target_dir, capture_output=True, text=True
        )
        untracked = [p.strip().replace("\\", "/") for p in proc_untracked.stdout.splitlines() if p.strip()]

        # 2. Modified tracked files
        proc_modified = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=target_dir, capture_output=True, text=True
        )
        modified = [p.strip().replace("\\", "/") for p in proc_modified.stdout.splitlines() if p.strip()]

        for rel_path in untracked + modified:
            full_path = target_dir / rel_path
            if full_path.is_file():
                try:
                    content = full_path.read_text(encoding="utf-8")
                    harness_files[rel_path] = content
                except UnicodeDecodeError:
                    print(f"Warning: binary file skipped in harness_files: {rel_path}")

        recipe["harness_files"] = harness_files
        recipe_json_path.write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")
        count += 1
        print(f"Synced {recipe_dir.name}: {len(harness_files)} harness files")

if __name__ == "__main__":
    sync_all()
