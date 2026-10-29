"""Small, reviewed local repair references; never assertions or training labels.

Original summaries, with primary references. No target-provided documents,
network retrieval, benchmark solutions, or protected tests are indexed here.
"""
import hashlib
import json
import re

VERSION = 'security-v1'
REVIEWED = '2026-10-09'
CARDS = (
    {
        'id': 'CWE-22',
        'title': 'Constrain filesystem access',
        'terms': ('path traversal', 'symlink', 'read_text', 'read_bytes', 'send_file'),
        'guidance': 'Resolve the allowed directory and requested path, including symbolic links, '
                    'before checking containment. Do not use string-prefix comparison or removal '
                    'of dot-dot sequences as the boundary. Preserve permitted file access and '
                    'existing missing-file behavior. Consider link replacement races where an '
                    'attacker can modify the filesystem; canonicalization alone does not prevent them.',
        'references': ('https://cwe.mitre.org/data/definitions/22.html',
                       'https://owasp.org/www-community/attacks/Path_Traversal'),
    },
    {
        'id': 'CWE-89',
        'title': 'Separate SQL data from query structure',
        'terms': ('sql injection', 'sqlite3', 'cursor.execute', 'parameter placeholders'),
        'guidance': 'Bind untrusted values using the database driver parameter API. Do not '
                    'interpolate, concatenate, or manually escape request values into SQL. '
                    'Identifiers and ordering keywords need an explicit allowlist when they cannot '
                    'be bound as values. Preserve legitimate query behavior and existing interfaces.',
        'references': ('https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html',),
    },
)


def retrieve(prompt, max_bytes=2200):
    """Deterministic bounded selection. Prompt text can select, never author, cards."""
    if not isinstance(max_bytes, int) or not 0 <= max_bytes <= 2200:
        raise ValueError('security reference allowance must be between 0 and 2200 bytes')
    corpus = json.dumps({'version': VERSION, 'reviewed': REVIEWED, 'cards': CARDS},
                        sort_keys=True, separators=(',', ':')).encode()
    lowered = prompt.casefold()
    ranked = []
    for card in CARDS:
        explicit = re.search(r'\b' + re.escape(card['id'].casefold()) + r'\b', lowered)
        score = 100 * bool(explicit) + sum(term in lowered for term in card['terms'])
        if score:
            ranked.append((-score, card['id'], card))
    selected, text = [], ''
    for _, _, card in sorted(ranked):
        fragment = f"\n{card['id']}: {card['guidance']}\nReferences: " + ', '.join(card['references']) + '\n'
        if len((text + fragment).encode()) <= max_bytes:
            selected.append(card['id'])
            text += fragment
    return text, {'profile': VERSION, 'reviewed': REVIEWED,
                  'corpus_sha256': hashlib.sha256(corpus).hexdigest(), 'card_ids': selected,
                  'context_sha256': hashlib.sha256(text.encode()).hexdigest()}
