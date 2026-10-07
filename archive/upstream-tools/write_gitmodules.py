import glob
import json
from pathlib import Path

with open('benchmark/upstream-cohort.json', 'r', encoding='utf-8') as f:
    cohort = json.load(f)
url_map = {c['id']: c['repository_url'] for c in cohort['cases']}

lines = []
for path in sorted(glob.glob('benchmark/recipes/*/target')):
    posix_path = Path(path).as_posix()
    case_id = Path(path).parent.name
    url = url_map.get(case_id, '')
    lines.append(f'[submodule "{posix_path}"]')
    lines.append(f'\tpath = {posix_path}')
    lines.append(f'\turl = {url}')
    lines.append(f'\tshallow = true')
    lines.append('')

content = '\n'.join(lines)
with open('.gitmodules', 'w', newline='\n', encoding='utf-8') as f:
    f.write(content)
print(f'Written .gitmodules with {len(glob.glob("benchmark/recipes/*/target"))} submodules')
