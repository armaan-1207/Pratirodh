"""Build tracked overlay/ directories for all 24 target repositories.

This ensures all target harness files and build configuration edits are tracked
directly in the parent repository under benchmark/recipes/<case>/overlay/
so that a fresh clone can reconstruct all 24 targets identically.
"""
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RECIPES = ROOT / "benchmark" / "recipes"

def build_overlays():
    total_cases = 0
    total_files = 0

    for recipe_dir in sorted(RECIPES.iterdir()):
        if not recipe_dir.is_dir():
            continue
        recipe_json_path = recipe_dir / "recipe.json"
        if not recipe_json_path.exists():
            continue
        target_dir = recipe_dir / "target"
        if not target_dir.exists():
            continue

        overlay_dir = recipe_dir / "overlay"
        overlay_dir.mkdir(parents=True, exist_ok=True)

        recipe = json.loads(recipe_json_path.read_text(encoding="utf-8"))
        harness_files = recipe.get("harness_files", {})

        # 1. Untracked files in target
        proc_untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=target_dir, capture_output=True, text=True
        )
        untracked = [p.strip().replace("\\", "/") for p in proc_untracked.stdout.splitlines() if p.strip()]

        # 2. Modified tracked files in target
        proc_modified = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=target_dir, capture_output=True, text=True
        )
        modified = [p.strip().replace("\\", "/") for p in proc_modified.stdout.splitlines() if p.strip()]

        # Merge with existing harness_files from recipe.json if any
        all_rel_paths = set(untracked + modified + list(harness_files.keys()))

        copied = 0
        for rel_path in sorted(all_rel_paths):
            src = target_dir / rel_path
            dst = overlay_dir / rel_path
            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                # Copy exact file content
                content = src.read_bytes()
                dst.write_bytes(content)
                copied += 1
                try:
                    harness_files[rel_path] = content.decode("utf-8")
                except UnicodeDecodeError:
                    pass
            elif rel_path in harness_files:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(harness_files[rel_path], encoding="utf-8")
                copied += 1

        recipe["harness_files"] = harness_files
        recipe_json_path.write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")
        print(f"{recipe_dir.name}: {copied} overlay files saved to overlay/")
        total_cases += 1
        total_files += copied

    print(f"\nDone: {total_cases} cases, {total_files} overlay files saved.")

if __name__ == "__main__":
    build_overlays()
