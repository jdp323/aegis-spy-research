"""Aggregate public research populations via SQLite read-only connections."""
import json
import sqlite3
from pathlib import Path

HORIZONS = ('H60', 'H120', 'SESSION')

def horizon_summary(path):
    path = Path(path)
    empty = {'status': 'NOT_COLLECTED', 'population': 'HORIZON_COMPARISON_UNDERLYING_ONLY', 'by_horizon': {key: {'tracked': 0, 'closed': 0, 'open': 0, 'unresolved': 0} for key in HORIZONS}, 'trials': 0}
    if not path.is_file():
        return empty
    try:
        db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=2)
        try:
            db.execute('PRAGMA query_only=ON')
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='idea_events'").fetchone():
                return {**empty, 'status': 'TABLE_UNAVAILABLE'}
            latest = {}
            for payload, in db.execute('SELECT payload FROM idea_events ORDER BY rowid'):
                row = json.loads(payload)
                if row.get('population') != 'HORIZON_COMPARISON_UNDERLYING_ONLY' or row.get('horizon_id') not in HORIZONS:
                    continue
                latest[row['signal_id']] = row
            totals = {key: {'tracked': 0, 'closed': 0, 'open': 0, 'unresolved': 0} for key in HORIZONS}
            for row in latest.values():
                counts = totals[row['horizon_id']];counts['tracked'] += 1
                counts['closed'] += row.get('status') == 'CLOSED'
                counts['open'] += row.get('status') in ('OPEN', 'PENDING')
                counts['unresolved'] += row.get('coverage_status') == 'UNRESOLVED_GAP'
            return {**empty, 'status': 'AVAILABLE_READ_ONLY', 'by_horizon': totals, 'trials': len({row.get('trial_id') for row in latest.values() if row.get('trial_id')})}
        finally:
            db.close()
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
        return {**empty, 'status': 'READ_UNAVAILABLE'}

def horizon_text(summary):
    lines = ['Horizon comparison = separately versioned underlying research; never pooled with legacy ideas or option paper.',
             'Status: ' + summary['status'] + '; observed trial variants ' + str(summary['trials']) + '.']
    for horizon, row in summary['by_horizon'].items():
        lines.append(horizon + ': ' + str(row['tracked']) + ' tracked; ' + str(row['closed']) + ' closed / ' + str(row['open']) + ' open; ' + str(row['unresolved']) + ' unresolved.')
    return '\n'.join(lines)
