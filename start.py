"""Lancement local : python start.py [--admin] [--port 8000]."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import venv

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description="Préparer puis lancer Gaboma Hub en local.")
parser.add_argument("--admin", action="store_true", help="Créer un compte administrateur avec saisie interactive.")
parser.add_argument("--port", type=int, default=8000)
args = parser.parse_args()
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10 minimum est requis. Python 3.12 ou 3.13 est recommandé.")
if not 1024 <= args.port <= 65535: raise SystemExit("Choisir un port entre 1024 et 65535.")
venv_path = root / ".venv"
python = venv_path / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
if not python.exists(): venv.EnvBuilder(with_pip=True).create(venv_path)
requirements = root / "requirements.txt"
digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
stamp = venv_path / ".hub-dependencies"
def run(*command): subprocess.run([str(python), *command], cwd=root, check=True)
try:
    if not stamp.exists() or stamp.read_text().strip() != digest:
        run("-m", "pip", "install", "-r", "requirements.txt")
        stamp.write_text(digest)
    run("manage.py", "migrate", "--noinput")
    run("manage.py", "seed_hub")
    run("manage.py", "collectstatic", "--noinput")
    if args.admin: run("manage.py", "createsuperuser")
    print(f"\nGaboma Hub : http://127.0.0.1:{args.port}/\nAdministration : http://127.0.0.1:{args.port}/admin/\nCtrl+C pour arrêter.\n", flush=True)
    run("manage.py", "runserver", f"127.0.0.1:{args.port}")
except KeyboardInterrupt:
    print("\nHub arrêté.")
except subprocess.CalledProcessError as exc:
    raise SystemExit(exc.returncode)
