"""Only execute the small authored fixtures; never arbitrary downloaded source."""
import copy
import importlib.util
from pathlib import Path
import sqlite3

import pytest

SPEC = importlib.util.spec_from_file_location('training_prepare', Path(__file__).parents[1] / 'tools/training/prepare.py')
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)


def test_corpus_split_and_message_boundary():
    rows = prepare.examples()
    prepare.validate(rows)
    for row in rows:
        messages = prepare.messages(row)
        assert len(messages) == 3
        assert 'untrusted_source' in messages[1]['content']
        assert 'review' not in messages[1]['content']
    duplicate = copy.deepcopy(rows[0])
    duplicate.update(id='duplicate', split='test', family='different')
    with pytest.raises(ValueError, match='leakage'):
        prepare.validate(rows+[duplicate])


@pytest.mark.parametrize('change', [{'license':'unknown'}, {'origin':'protected-benchmark'},
    {'source':'-----BEGIN RSA PRIVATE KEY-----'}, {'contract':'x'*16001}, {'extra':'instruction'}])
def test_reject_unreviewed_or_secret_data(change):
    rows = prepare.examples()
    rows[0].update(change)
    with pytest.raises(ValueError):
        prepare.validate(rows)


def test_dataset_never_overwrites(tmp_path):
    prepare.write_dataset(tmp_path / 'data')
    with pytest.raises(FileExistsError):
        prepare.write_dataset(tmp_path / 'data')


@pytest.mark.parametrize('row', prepare.examples(), ids=lambda r:r['id'])
def test_authored_repairs_preserve_behavior_and_close_boundary(row, tmp_path):
    fixed, vulnerable = {}, {}
    exec(compile(row['repair'], '<authored-fix>', 'exec'), fixed)
    exec(compile(row['source'], '<authored-control>', 'exec'), vulnerable)
    if row['cwe'] == 'CWE-22':
        root=tmp_path/'public';root.mkdir()
        (root/'notes.txt').write_text('public',encoding='utf-8')
        sibling=tmp_path/'public-private';sibling.mkdir()
        (sibling/'secret.txt').write_text('private',encoding='utf-8')
        assert fixed['read_public'](root,'notes.txt') == 'public'
        for attack in ['../public-private/secret.txt', str(sibling/'secret.txt')]:
            with pytest.raises(ValueError):
                fixed['read_public'](root,attack)
        # A sibling target defeats the naive canonical-prefix control.
        if row['family']=='common-path':
            assert vulnerable['read_public'](root,'../public-private/secret.txt') == 'private'
        elif row['family']=='relative-to':
            assert vulnerable['read_public'](root,str(sibling/'secret.txt')) == 'private'
        else:
            assert vulnerable['read_public'](root,'../public-private/secret.txt') == 'private'
    else:
        with sqlite3.connect(':memory:') as conn:
            conn.execute('CREATE TABLE people(id INTEGER,name TEXT,email TEXT)')
            conn.executemany('INSERT INTO people VALUES (?,?,?)',[(1,'alice','alice@test'),(2,"O\'Neil","O\'Neil@test")])
            value='alice@test' if row['family']=='lookup-email' else 'alice'
            assert fixed['lookup'](conn,value) == vulnerable['lookup'](conn,value)
            assert fixed['lookup'](conn,"' OR 1=1 --") in [[],(0,)]
            assert vulnerable['lookup'](conn,"' OR 1=1 --") not in [[],(0,)]
