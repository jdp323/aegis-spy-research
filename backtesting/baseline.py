"""Research-only price-index baselines. No brokerage or execution integration."""
import argparse
import csv
import hashlib
import io
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import urlopen

SOURCE = 'https://fred.stlouisfed.org/graph/?g=1&cosd=2016-10-01&coed=2026-09-30&id=SP500'
DOWNLOAD = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500&cosd=2016-10-01&coed=2026-09-30'
STRATEGIES = ('cash', 'buy_hold', 'trend_200', 'momentum_252')
COSTS = (0, 5, 10, 25)

def signal(prices, i, strategy):
    if strategy == 'cash': return 0.0
    if strategy == 'buy_hold': return 1.0
    if strategy == 'trend_200':
        return float(i >= 199 and prices[i] > sum(prices[i-199:i+1]) / 200)
    if strategy == 'momentum_252':
        return float(i >= 252 and prices[i] > prices[i-252])
    raise ValueError(strategy)

def simulate(dates, prices, strategy, bps, start, end):
    """Signal at close t-2; rebalance at close t-1; earn close t-1 to t return.

    This conservative extra lag avoids same-close signal execution. Each evaluation
    starts from cash and charges initial entry and terminal liquidation. No interest.
    """
    if bps < 0 or bps >= 10000: raise ValueError('Invalid one-way cost')
    indices = [i for i, d in enumerate(dates) if start <= d <= end and i >= 254]
    if not indices: raise ValueError('Insufficient history in evaluation window')
    wealth, peak, drawdown, previous, turnover = 1.0, 1.0, 0.0, 0.0, 0.0
    returns = []
    exposures = []
    for j, i in enumerate(indices):
        position = signal(prices, i-2, strategy)
        change = abs(position-previous)
        factor = (1-change*bps/10000) * (1+position*(prices[i]/prices[i-1]-1))
        turnover += change
        if j == len(indices)-1:
            factor *= 1-position*bps/10000
            turnover += position
        wealth *= factor
        peak = max(peak, wealth)
        drawdown = min(drawdown, wealth/peak-1)
        returns.append(factor-1)
        exposures.append(position)
        previous = position
    n = len(returns)
    mean = sum(returns)/n
    sd = math.sqrt(sum((x-mean)**2 for x in returns)/(n-1)) if n > 1 else 0
    years = (date.fromisoformat(dates[indices[-1]])-date.fromisoformat(dates[indices[0]-1])).days/365.25
    return dict(strategy=strategy, one_way_cost_bps=bps, start=dates[indices[0]], end=dates[indices[-1]],
                observations=n, total_return=wealth-1, annualized_return=wealth**(1/years)-1,
                annualized_volatility=sd*math.sqrt(252), sharpe_zero_cash=mean/sd*math.sqrt(252) if sd else None,
                max_drawdown=drawdown, average_exposure=sum(exposures)/n, one_way_turnover=turnover)

def parse_data(raw):
    rows = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    dates, prices = [], []
    for row in rows:
        d = row.get('observation_date', row.get('DATE'))
        value = row.get('SP500')
        if not d or d > '2026-09-30' or d < '2016-10-01' or value in (None, '', '.'): continue
        date.fromisoformat(d)
        p = float(value)
        if not math.isfinite(p) or p <= 0: raise ValueError('Invalid price')
        if dates and d <= dates[-1]: raise ValueError('Dates must be strictly increasing')
        dates.append(d)
        prices.append(p)
    if len(prices) < 1000: raise ValueError('Fewer than 1000 valid daily observations')
    return dates, prices

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1]/'backtests')
    parser.add_argument('--cache', type=Path, default=Path('work/aegis_data/SP500.csv'))
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    provenance = dict(source_page='https://fred.stlouisfed.org/series/SP500', download_url=DOWNLOAD,
                      retrieved_utc=datetime.now(timezone.utc).isoformat(), cutoff='2026-09-30',
                      permission='Public retrieval; copyrighted index data. Raw data retained only in local work cache; do not redistribute.',
                      data_type='S&P 500 daily closing price index; dividends excluded; current vintage')
    try:
        if args.offline:
            raw = args.cache.read_bytes()
            provenance['retrieval_mode'] = 'offline_cache'
        else:
            with urlopen(DOWNLOAD, timeout=60) as response: raw = response.read()
            args.cache.parent.mkdir(parents=True, exist_ok=True)
            args.cache.write_bytes(raw)
            provenance['retrieval_mode'] = 'public_download'
        dates, prices = parse_data(raw)
        provenance.update(sha256=hashlib.sha256(raw).hexdigest(), first=dates[0], last=dates[-1], observations=len(prices))
        # Fixed chronological holdout. Rules are declared without parameter fitting.
        # It is a historical holdout, not a truly unseen prospective test.
        windows = [('development', '2017-10-01', '2021-12-31'), ('historical_holdout', '2022-01-01', '2026-09-30')]
        windows += [('year_'+str(y), f'{y}-01-01', min(f'{y}-12-31', '2026-09-30')) for y in range(2022, 2027)]
        results = []
        for name, start, end in windows:
            if dates[-1] < start: continue
            for strategy in STRATEGIES:
                for cost in COSTS:
                    results.append(dict(window=name, **simulate(dates, prices, strategy, cost, start, end)))
        payload = dict(status='RESEARCH_PROXY_ONLY_NOT_VALIDATED_FOR_TRADING', provenance=provenance, results=results)
        lines = ['# AEGIS baseline research', '', 'Status: research proxy only; no strategy approved for trading.', '',
                 '## Method', '',
                 'Rules were fixed before this run: cash (0% return), fully invested buy-and-hold, close above trailing 200-session mean, and positive 252-session price momentum. Long/cash only; no tuning or leverage. Signals use data through t−2, hypothetical rebalancing occurs at close t−1, and exposure earns return to close t. Each window starts from cash; initial entry and final liquidation are charged. Costs are 0, 5, 10 and 25 basis points per one-way unit turnover.', '',
                 'Development: 2017-10-01–2021-12-31. Historical holdout: 2022-01-01–2026-09-30. Annual holdout folds carry historical feature context but reset equity and positions. No model is trained or retuned. The holdout was selected today: its history may already be familiar, so it is not evidence of prospective performance.', '',
                 '## Historical holdout results', '',
                 '| Rule | Cost bps | Annualized return | Max drawdown | Volatility | Turnover |',
                 '|---|---:|---:|---:|---:|---:|']
        for r in results:
            if r['window']=='historical_holdout':
                lines.append(f"| {r['strategy']} | {r['one_way_cost_bps']} | {r['annualized_return']:.2%} | {r['max_drawdown']:.2%} | {r['annualized_volatility']:.2%} | {r['one_way_turnover']:.0f} |")
        lines += ['', '## Limitations and decision', '',
                  'This index cannot be bought directly. Price-only history excludes dividends, cash yield, fund expenses, taxes, spread variation, tracking error, market impact and executable prices. Costs are assumed sensitivity values, not measured broker costs. Daily closing data cannot establish actual fills. Current-vintage data may be revised. A single US large-cap index and roughly ten years of history provide weak generalization evidence; all tested rules and cost variants are disclosed in results.json. No selected winner, significance claim, expected profit, or real-account recommendation is made.', '',
                  'Next gate: obtain appropriately licensed tradable-instrument total-return data, audit corporate actions and executable timing, compare against interest-bearing cash, then register an untouched prospective paper experiment. Failures or absent inputs do not authorize live execution.', '',
                  '## Provenance', '', f"Source: [FRED SP500](https://fred.stlouisfed.org/series/SP500). Retrieved {provenance['retrieved_utc']}. Valid observations: {len(prices)} from {dates[0]} through {dates[-1]}. SHA256: `{provenance['sha256']}`. Raw copyrighted observations are not bundled with deliverables."]
        report = '\n'.join(lines)+'\n'
    except Exception as exc:
        payload = dict(status='BLOCKED_DATA_FETCH_OR_VALIDATION', provenance=provenance, error=repr(exc), results=[])
        report = '# AEGIS baseline research\n\nBlocked: '+repr(exc)+'\n\nNo performance results were produced. Fixed rules remain in baseline.py for a reproducible retry. No trading is authorized.\n'
    (args.out/'results.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    (args.out/'baseline_report.md').write_text(report, encoding='utf-8')
    print(json.dumps({k:v for k,v in payload.items() if k!='results'}, indent=2))
    return 0 if payload['results'] else 1

if __name__ == '__main__': raise SystemExit(main())
