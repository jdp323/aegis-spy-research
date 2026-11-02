"""Free-only runtime network policy; capability is never inferred from cost."""
from datetime import datetime, timezone, timedelta
from threading import Lock
import time

VERSION = 'free-only-provider-v1'
MODE = 'FREE_ONLY'


class PolicyRefusal(RuntimeError):
    pass


def free_only(config=None):
    config = config or {}
    if config.get('operating_mode', MODE) != MODE:
        raise ValueError('ONLY_FREE_ONLY_MODE_SUPPORTED')
    return True


def validate_free_policy(config):
    free_only(config)
    if config.get('paid_api_enabled', False) or config.get('paid_model_enabled', False):
        raise ValueError('PAID_DEPENDENCY_FORBIDDEN')
    option_provider=config.get('option_data_provider', 'ALPACA')
    # Preserve an existing dormant Questrade preference without activating it.
    # Runtime free policy independently prevents keepalive/polling/stream use.
    if option_provider is not None and (not isinstance(option_provider,str) or option_provider.upper() not in ('ALPACA', 'QUESTRADE', 'UNCONFIGURED', 'NONE')):
        raise ValueError('OPTION_PROVIDER_NOT_VERIFIED_FREE')
    return config


def allow_alpaca(path, params, purpose='RESEARCH', now=None):
    """Explicit allowlist. A probe cannot silently become a streaming grant."""
    now = now or datetime.now(timezone.utc)
    if purpose not in ('RESEARCH', 'CAPABILITY_PROBE', 'HISTORICAL_RESEARCH'):
        raise PolicyRefusal('UNKNOWN_REQUEST_PURPOSE')
    feed = params.get('feed')
    if path in ('/v1beta1/news', '/v1/corporate-actions'):
        return True
    if path == '/v2/stocks/SPY/quotes/latest' and feed == 'iex':
        return True
    if path == '/v2/stocks/SPY/bars' and feed == 'iex':
        return True
    # Exactly the diagnostic endpoints used by the existing bounded checker.
    if purpose == 'CAPABILITY_PROBE':
        if path == '/v2/stocks/SPY/quotes/latest' and feed == 'sip':
            return True
        if path == '/v1beta1/options/snapshots/SPY' and feed == 'opra' and params.get('limit') == 1:
            return True
        raise PolicyRefusal('PROBE_ENDPOINT_NOT_ALLOWLISTED')
    if purpose == 'HISTORICAL_RESEARCH' and path == '/v2/stocks/SPY/bars' and feed == 'sip':
        try:
            end = datetime.fromisoformat(params['end'].replace('Z', '+00:00'))
            if end.tzinfo is not None and end <= now - timedelta(minutes=15):
                return True
        except (KeyError, TypeError, ValueError):
            pass
        raise PolicyRefusal('SIP_HISTORY_REQUIRES_EXPLICIT_DELAYED_END')
    raise PolicyRefusal('FREE_ONLY_CAPABILITY_NOT_APPROVED')


def runtime_streams(config=None):
    validate_free_policy(config or {})
    # IEX remains one exchange; absent consolidated/option access is not false
    # freshness, and historical or indicative responses cannot enable streams.
    return [('iex', False)]


class RequestBudget:
    """Process-wide no-wait budget shared by the adapter's client instances.

    This is not a provider quota guarantee across unrelated programs/accounts.
    Policy/rate refusal happens before any credentials or network transport.
    """
    def __init__(self, requests_per_minute=100, simultaneous=4, clock=time.monotonic):
        self.maximum = requests_per_minute
        self.simultaneous = simultaneous
        self.clock = clock
        self.started = []
        self.active = 0
        self.lock = Lock()

    def enter(self):
        with self.lock:
            now = self.clock()
            self.started = [v for v in self.started if 0 <= now-v < 60]
            if self.active >= self.simultaneous or len(self.started) >= self.maximum:
                raise PolicyRefusal('LOCAL_MARKET_DATA_BUDGET_EXHAUSTED')
            self.active += 1
            self.started.append(now)

    def leave(self):
        with self.lock:
            self.active = max(0, self.active-1)


BUDGET = RequestBudget()


def capability_record(probe, *, credentials_configured=None):
    """Secret-free as-of observations. Unknown permissions are not invented."""
    capabilities = {}
    by = {x['feed']: x for x in probe.get('probes', [])}
    for feed in ('IEX', 'SIP', 'OPRA'):
        item = by.get(feed)
        responded = bool(item and item.get('status') == 'MARKET_ENDPOINT_RESPONSE_RECEIVED')
        refused = bool(item and item.get('provider_error_class') in ('HTTP_401', 'HTTP_403'))
        access = 'RESPONSE_RECEIVED' if responded else 'REFUSED' if refused else 'UNKNOWN'
        capabilities[feed] = {
            'access': access,
            'stock_bars': 'UNKNOWN',
            'stock_quotes': access if feed != 'OPRA' else 'NOT_APPLICABLE',
            'option_bbo': access if feed == 'OPRA' else 'NOT_APPLICABLE',
            'option_source_timestamps': 'UNKNOWN',
            'greeks': 'UNKNOWN', 'greek_source_timestamps': 'UNKNOWN',
            'greek_units': 'UNKNOWN', 'point_in_time_chain_neighbors': 'UNKNOWN',
            'liquidity': 'UNKNOWN', 'multiplier_deliverable': 'UNKNOWN',
            'delay_status': 'UNVERIFIED',
            'entitlement_evidence': item.get('provider_error_class', item.get('status')) if item else 'UNKNOWN',
            'refusal_cause': 'UNKNOWN; status alone does not distinguish authentication from permissions',
            'redistribution_scope': 'UNKNOWN; no new raw-data guest routing authorized',
            'request_rate_policy': '100/minute and four simultaneous requests per adapter process; provider/account quotas remain separate',
            'latest_probe': item,
            'runtime_use': 'SINGLE_EXCHANGE_UNDERLYING_RESEARCH' if feed == 'IEX' else 'POLICY_DISABLED_UNVERIFIED',
            'entry_eligibility_proved': False,
        }
    capabilities['INDICATIVE_OPTIONS'] = {
        'access': 'NOT_REQUESTED', 'delay_status': 'DELAYED_TRADES_MODIFIED_QUOTES',
        'runtime_use': 'FORBIDDEN_FOR_EXECUTABLE_QUOTES_AND_PNL',
        'source': 'https://docs.alpaca.markets/us/reference/optionchain',
    }
    for provider in ('QUESTRADE', 'IBKR'):
        capabilities[provider] = {'access': 'NOT_CONFIGURED_OR_VERIFIED', 'continuous_free_option_bbo': 'UNKNOWN', 'runtime_use': 'NOT_ENABLED', 'credentials_collected': False}
    capabilities['TRADIER'] = {'runtime_use': 'EXCLUDED_CANADIAN_RESIDENCE_PLAN', 'access': 'NOT_REQUESTED', 'account_opened': False}
    return {'version': VERSION, 'operating_mode': MODE, 'as_of': probe.get('at'),
            'credentials_configured': credentials_configured,
            'incremental_subscription_budget_usd': 0,
            'recurring_paid_dependencies': [], 'capabilities': capabilities,
            'option_performance': 'NOT_MEASURED', 'live_signal_ready': False,
            'limits': ['A configured credential is not entitlement or freshness.',
                       'Closed-session observations cannot establish live-session delivery.',
                       'No account, balance, order or subscription endpoint used.',
                       'Existing privacy/sharing decisions remain unchanged.']}
