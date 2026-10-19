"""Resolve the user's installed runtimes and private local storage."""
import os,shutil,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def python_executable():
    return os.environ.get('AEGIS_PYTHON') or sys.executable

def node_executable():
    value=os.environ.get('AEGIS_NODE') or shutil.which('node')
    if not value:raise RuntimeError('NODE_NOT_FOUND: install Node.js22 or set AEGIS_NODE')
    return value

def private_directory():
    return Path(os.environ.get('AEGIS_PRIVATE_DIR',str(ROOT/'.private'))).expanduser()
