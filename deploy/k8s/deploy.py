"""Deployment sequenced explicitly: dependencies, migrations, web, ingress."""
import argparse
import json
import re
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--context', required=True)
parser.add_argument('--image', required=True, help='Published image pinned by sha256 digest')
parser.add_argument('--render', action='store_true', help='Print manifests without contacting the cluster')
args = parser.parse_args()
if not re.fullmatch(r'[^\s]+@sha256:[0-9a-f]{64}', args.image):
    parser.error('Provide an immutable image reference with its full sha256 digest.')
if not args.context.strip():
    parser.error('An explicit Kubernetes context is required.')
command = ['kubectl', '--context', args.context, '-n', 'gaboma-hub']

def run(*parts, data=None, capture=False):
    return subprocess.run(command + list(parts), input=data, text=True, check=True,
                          stdout=subprocess.PIPE if capture else None)

def manifest(name):
    content = json.loads((ROOT / name).read_text(encoding='utf-8'))
    def replace(value):
        if isinstance(value, dict):
            return {k: replace(v) for k, v in value.items()}
        if isinstance(value, list):
            return [replace(v) for v in value]
        return args.image if value == 'gaboma-hub:replace' else value
    return replace(content)

files = ['namespace.json', 'infra.json', 'migration.json', 'web.json', 'ingress.json']
if args.render:
    print(json.dumps({'apiVersion': 'v1', 'kind': 'List', 'items': [item for name in files
          for item in manifest(name).get('items', [manifest(name)])]}, indent=2))
    raise SystemExit(0)

# Secrets and certificate must already exist; do not print their contents.
run('get', 'secret', 'hub-secrets', 'hub-tls', '-o', 'name')
for name in ['infra.json']:
    run('apply', '-f', '-', data=json.dumps(manifest(name)))
for name in ['hub-db', 'hub-redis']:
    run('rollout', 'status', 'deployment/' + name, '--timeout=300s')
job = manifest('migration.json')['items'][0]
job['metadata']['name'] = 'hub-migrate-' + str(time.time_ns())
run('create', '-f', '-', data=json.dumps(job))
run('wait', '--for=condition=complete', 'job/' + job['metadata']['name'], '--timeout=320s')
# Failed migrations stop execution before changing the web deployment.
run('apply', '-f', '-', data=json.dumps(manifest('web.json')))
run('rollout', 'status', 'deployment/hub-web', '--timeout=300s')
run('apply', '-f', '-', data=json.dumps(manifest('ingress.json')))
run('get', 'pods,svc,ingress,pvc')
