"""Scan local image exports without mounting the Docker socket in the scanner."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

SCANNER = 'aquasec/trivy@sha256:af6acf9a6b85dfe389a1941505c0ce9efef52a4719635e1a962f022a3d855daa'
ROLES = ('dashboard', 'runner', 'worker', 'requests-demo')
DIGEST = re.compile(r'^sha256:[0-9a-f]{64}$')


def build_binding(role, image, inspection, report, archive_sha256):
    """Bind an exported scan to runtime package layers, without equating config IDs."""
    if role not in ROLES or not isinstance(image, str) or not image:
        raise ValueError('Missing or invalid image role/reference')
    if not isinstance(inspection, dict) or not isinstance(report, dict):
        raise ValueError('Missing image inspection or scanner report')
    metadata = report.get('Metadata', {})
    rootfs = inspection.get('RootFS', {})
    if not isinstance(metadata, dict) or not isinstance(rootfs, dict):
        raise ValueError('Missing image layer metadata')
    runtime_id = inspection.get('Id')
    scanner_id = metadata.get('ImageID')
    runtime_layers = rootfs.get('Layers')
    scanner_layers = metadata.get('DiffIDs')
    for label, digest in [('runtime image', runtime_id), ('scanner image', scanner_id),
                          ('export archive', archive_sha256)]:
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
            raise ValueError(f'Missing or invalid {label} digest')
    for label, layers in [('runtime', runtime_layers), ('scanner', scanner_layers)]:
        if not isinstance(layers, list) or not layers or any(
                not isinstance(item, str) or not DIGEST.fullmatch(item) for item in layers):
            raise ValueError(f'Missing or invalid {label} ordered layer identities')
    if runtime_layers != scanner_layers:
        raise ValueError('Scanner/runtime ordered layer identities differ')
    return {'role': role, 'image_reference': image, 'runtime_image_id': runtime_id,
            'scanner_image_id': scanner_id, 'export_archive_sha256': archive_sha256,
            'runtime_diff_ids': runtime_layers, 'scanner_diff_ids': scanner_layers,
            'ordered_layers_match': True,
            'config_ids_match': runtime_id == scanner_id}


def archive_digest(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return 'sha256:' + digest.hexdigest()


def run(*args):
    subprocess.run(args, check=True, timeout=1200)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--images', nargs=4, required=True)
    parser.add_argument('--output', type=Path, default=Path('run_output/container-scan'))
    parser.add_argument('--cache', type=Path, default=Path('run_output/trivy-cache'))
    parser.add_argument('--offline', action='store_true', help='use the existing verified scanner database')
    args = parser.parse_args()
    output, cache = args.output.resolve(), args.cache.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    if not args.offline:
        run('docker', 'pull', SCANNER)
        run('docker', 'run', '--rm', '--mount', f'type=bind,source={cache},target=/cache',
            SCANNER, 'image', '--cache-dir', '/cache', '--db-repository',
            'ghcr.io/aquasecurity/trivy-db:2', '--download-db-only')
    bindings = []
    for role, image in zip(ROLES, args.images):
        inspected = json.loads(subprocess.check_output(
            ['docker', 'image', 'inspect', image], timeout=60))
        if not isinstance(inspected, list) or len(inspected) != 1:
            raise ValueError(f'Expected exactly one local image: {role}')
        # Export the inspected immutable ID; a concurrently moved tag cannot change it.
        image_id = inspected[0]['Id']
        with tempfile.TemporaryDirectory(prefix='image-scan-', dir=output) as temporary:
            archive = Path(temporary) / 'image.tar'
            run('docker', 'image', 'save', '-o', str(archive), image_id)
            run('docker', 'run', '--rm', '--network', 'none', '--mount',
                f'type=bind,source={temporary},target=/input,readonly', '--mount',
                f'type=bind,source={output},target=/audit', '--mount',
                f'type=bind,source={cache},target=/cache,readonly', SCANNER,
                'image', '--input', '/input/image.tar', '--skip-db-update',
                '--cache-backend', 'memory', '--scanners', 'vuln', '--offline-scan',
                '--skip-version-check', '--cache-dir', '/cache', '--timeout', '10m',
                # pip's original BOM mixes build-time and original bundled pins.
                # Actual METADATA and vendor.txt components are audited separately,
                # including reviewed hash-bound security overrides to pip modules.
                '--skip-files', '**/pip/_vendor/bom.cdx.json',
                '--severity', 'HIGH,CRITICAL', '--format', 'json',
                '--output', f'/audit/{role}-trivy.json')
            report = json.loads((output / f'{role}-trivy.json').read_text())
            binding = build_binding(role, image, inspected[0], report, archive_digest(archive))
            binding['scanner_report_sha256'] = 'sha256:' + hashlib.sha256(
                (output / f'{role}-trivy.json').read_bytes()).hexdigest()
            bindings.append(binding)
    (output / 'image-bindings.json').write_text(
        json.dumps({'version': 1, 'images': bindings}, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
