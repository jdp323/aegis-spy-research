"""Public routing visibility: counts only, never recipient identities."""
import json
from core.storage import ROOT
def display(config,root=ROOT):
    if not config.get('signals',{}).get('shared',False):return 'signals.shared: OFF'
    try:
        d=json.loads((root/'monitoring/access.json').read_text(encoding='utf-8'));members=d.get('members',d.get('users',{}))
        members=list(members.values()) if isinstance(members,dict) else members
        n=sum(isinstance(m,dict) and not m.get('revoked_at') and m.get('active',True) and m.get('status','active') not in ('revoked','left') for m in members)
        return 'signals.shared: ON ('+str(n)+' guests)'
    except (OSError,ValueError,TypeError):return 'signals.shared: ON (guest count UNAVAILABLE)'
