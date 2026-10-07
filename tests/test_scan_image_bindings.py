"""Image receipts require exact ordered layers, not equal scanner config IDs."""
import copy
import hashlib

import pytest

from tools.scan_container_images import archive_digest, build_binding


def inputs():
    layers = ['sha256:' + 'a' * 64, 'sha256:' + 'b' * 64]
    return ({'Id': 'sha256:' + '1' * 64, 'RootFS': {'Layers': layers}},
            {'Metadata': {'ImageID': 'sha256:' + '2' * 64, 'DiffIDs': list(layers)}},
            'sha256:' + '3' * 64)


def test_distinct_config_ids_with_equal_layers_are_explicitly_recorded():
    inspection, report, archive = inputs()
    # Sensitive metadata is never included in the allowlisted receipt.
    inspection['Config'] = {'Env': ['PASSWORD=private']}
    receipt = build_binding('worker', 'worker:test', inspection, report, archive)
    assert receipt['ordered_layers_match'] is True
    assert receipt['config_ids_match'] is False
    assert receipt['runtime_image_id'] == inspection['Id']
    assert receipt['scanner_image_id'] == report['Metadata']['ImageID']
    assert receipt['export_archive_sha256'] == archive
    assert 'Config' not in receipt


@pytest.mark.parametrize('layers', [None, [], ['invalid'],
                                  ['sha256:' + 'b' * 64, 'sha256:' + 'a' * 64],
                                  ['sha256:' + 'a' * 64]])
def test_invalid_missing_or_reordered_scanner_layers_rejected(layers):
    inspection, report, archive = inputs()
    report['Metadata']['DiffIDs'] = layers
    with pytest.raises(ValueError):
        build_binding('worker', 'worker:test', inspection, report, archive)


@pytest.mark.parametrize('field', ['runtime_id', 'scanner_id', 'runtime_layers', 'archive'])
def test_missing_binding_information_rejected(field):
    inspection, report, archive = copy.deepcopy(inputs())
    if field == 'runtime_id':
        inspection.pop('Id')
    elif field == 'scanner_id':
        report['Metadata'].pop('ImageID')
    elif field == 'runtime_layers':
        inspection.pop('RootFS')
    else:
        archive = ''
    with pytest.raises(ValueError):
        build_binding('worker', 'worker:test', inspection, report, archive)


def test_archive_digest_hashes_exact_export_bytes(tmp_path):
    archive = tmp_path / 'image.tar'
    archive.write_bytes(b'export bytes\x00')
    assert archive_digest(archive) == 'sha256:' + hashlib.sha256(b'export bytes\x00').hexdigest()
