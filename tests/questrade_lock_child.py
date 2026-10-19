"""Fixture subprocess for OS lock serialization; no network or credentials."""
import sys,time
from pathlib import Path
from data.questrade_vault import locked
if __name__=='__main__':
 with locked(Path(sys.argv[1]),timeout=5):
  with Path(sys.argv[2]).open('a') as f:f.write('enter '+sys.argv[3]+'\n');f.flush()
  time.sleep(.15)
  with Path(sys.argv[2]).open('a') as f:f.write('exit '+sys.argv[3]+'\n')
