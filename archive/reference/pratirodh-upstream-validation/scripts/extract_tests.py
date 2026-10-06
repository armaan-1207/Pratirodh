import subprocess
from pathlib import Path

for recipe in sorted(Path('benchmark/recipes').glob('*')):
    name = recipe.name
    audit = recipe / 'audit.json'
    if not audit.exists(): continue
    import json
    data = json.loads(audit.read_text('utf-8'))
    if not data.get('files'):
        # Missing harness. Let's see if tests are in fix_revision
        recipe_json = json.loads((recipe / 'recipe.json').read_text('utf-8'))
        fix_rev = recipe_json.get('fix_revision')
        if not fix_rev: continue
        try:
            diff = subprocess.check_output(['git', 'log', '-p', '-1', fix_rev], cwd=str(recipe / 'target'), text=True)
            test_files = [line.split(' b/')[1] for line in diff.split('\n') if line.startswith('+++ b/') and ('test' in line.lower() or 'spec' in line.lower())]
            if test_files:
                print(f'{name}: Tests found in fix commit: {", ".join(test_files)}')
            else:
                print(f'{name}: No tests found in fix commit.')
        except Exception as e:
            print(f'{name}: Error checking git: {e}')
