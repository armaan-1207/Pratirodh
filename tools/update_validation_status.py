"""Write the canonical generated status projection atomically."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pratirodh.upstream_status import load_status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    args = parser.parse_args()
    payload = load_status(args.root.resolve())
    output = args.root / 'run_output/upstream-validation/status.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    temporary.replace(output)
    print(json.dumps({key: payload[key] for key in ('status', 'acquired', 'qualified', 'completed', 'audited')}, indent=2))


if __name__ == '__main__':
    main()
