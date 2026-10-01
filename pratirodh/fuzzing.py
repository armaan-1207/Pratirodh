"""Seeded request variation with trusted assertions; not coverage-guided fuzzing."""
import copy
import random
from urllib.parse import quote

VERSION = 'seeded-properties-1'


def generate(contract, seed=0, count=64):
    rng = random.Random(seed)
    seeds = [c for c in contract['cases'] + contract.get('probes', []) if c['kind'] == 'attack']
    variants = []
    for base in seeds:
        variants.append(copy.deepcopy(base))
        for transport in ('query', 'form', 'json'):
            for key, value in base.get(transport, {}).items():
                if not isinstance(value, str):
                    continue
                for changed in [quote(value, safe=''), quote(quote(value, safe=''), safe=''), value + ' ',
                                ' ' + value, value + 'x', value[:1], 'x' * 128]:
                    variant = copy.deepcopy(base)
                    variant[transport][key] = changed
                    variants.append(variant)
    rng.shuffle(variants)
    result = []
    for index in range(count):
        case = copy.deepcopy(variants[index % len(variants)])
        case['id'] = f'fuzz-{seed}-{index}'
        result.append(case)
    return result
