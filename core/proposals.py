"""Paper evaluation only; input attestations do not prove brokerage reconciliation."""
import json
import re
from dataclasses import asdict
from pathlib import Path
from core.service import ROOT, read
from risk.v2 import RiskEngineV2, AccountSnapshot, CycleLedger, MarketQuote, MarketSession, Proposal, StrategyEvidence

def evaluate_file(path):
    raw = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    data = dict(raw['account'])
    data['ledger'] = CycleLedger(**data['ledger'])
    p = Proposal(**raw['proposal'])
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', p.proposal_id):
        raise ValueError('Invalid proposal ID')
    registry = {k: StrategyEvidence(**v) for k,v in read('research/strategy_registry.json', {}).items()}
    engine = RiskEngineV2(ROOT/'risk/control_v2.sqlite', registry)
    try:
        decision = engine.evaluate(AccountSnapshot(**data), MarketQuote(**raw['quote']), MarketSession(**raw['session']), p)
    finally:
        engine.close()
    artifact = {'decision': asdict(decision), 'proposal': asdict(p),
                'scope': 'Paper validation only; supplied attestations require independent verification before a live manual-review alert'}
    directory = ROOT/'research/proposals'; directory.mkdir(exist_ok=True)
    # Preserve every evaluation rather than overwriting earlier failures.
    import time
    (directory/f'{p.proposal_id}_{time.time_ns()}.json').write_text(json.dumps(artifact, indent=2), encoding='utf-8')
    return artifact
