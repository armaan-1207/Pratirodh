"""Scan local image exports without mounting the Docker socket in the scanner."""
import argparse
from pathlib import Path
import subprocess
import tempfile

SCANNER = 'aquasec/trivy@sha256:af6acf9a6b85dfe389a1941505c0ce9efef52a4719635e1a962f022a3d855daa'
ROLES = ('dashboard', 'runner', 'worker', 'requests-demo')


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
    for role, image in zip(ROLES, args.images):
        with tempfile.TemporaryDirectory(prefix='image-scan-', dir=output) as temporary:
            archive = Path(temporary) / 'image.tar'
            run('docker', 'image', 'save', '-o', str(archive), image)
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


if __name__ == '__main__':
    main()
