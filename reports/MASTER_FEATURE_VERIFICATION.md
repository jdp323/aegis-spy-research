# Feature and function verification map

Public full suite: tests 765/765; backtesting 7/7; monitoring 4/4; node 61/61. Installed final suite: tests 758/758; backtesting 7/7; monitoring 4/4; node 60/60. Original installed baseline: tests 724/724; backtesting 7/7; monitoring 4/4; node 56/56. Complete result/status files remain local; this map does not claim every indexed function was behaviorally exercised.

Dynamic registry: 36 commands, 540 role/argument cases, status PASS. Owner/guest/stranger/revoked/expired invitation paths, callbacks, FORCE/VOID/reconciliation and private routing are tested in the real handler harness and full suites. External provider and phone receipt are distinct evidence.

Schedule verification: 24 scenarios; actual notifier fake calls 388, status PASS. Full normal/restart, holiday, DST, early-close, stale/outage/backfill and missing calendar paths retain every expected slot. No real guest/development broadcast was sent. Main menu and all typed commands remain.

| Area | Feature status | Verification / limit |
|---|---|---|
| Registry, arguments, roles, callbacks, sharing | TESTED IN ISOLATION | Complete command harness and Python/Node suites; live guest receipt not inferred |
| Status/premarket/plan/update/recap | TESTED IN ISOLATION | Actual formatters and notifier with fake transport; bounded lines; fictional gallery/transcript |
| Primary lifecycle and cooldown | TESTED IN ISOLATION | Opposing candidate, one plan, restart, deadline, unresolved/admin cancellation, dedupe and immutable fields |
| Storage and isolation | TESTED IN ISOLATION | Append-only migration/transactions, WAL-aware backup/restore, model/simulation refusal; no private historical rows rewritten |
| Feed adapters and gates | TESTED IN ISOLATION; external access separately observed | Source/receipt/skew/heartbeat/bar continuity and malformed responses; live-session readiness pending |
| Local service group/HTTP | VERIFIED IN OPERATION — bounded sample | Seven components, completed phases, listener/dispatcher and HTTP progress; cold failures and cycle misses remain |
| Model adapter and containment | TESTED IN ISOLATION | Raw paths/calendar/failure fixtures; real inference BLOCKED_RESOURCE_HEADROOM |
| Strategy and option evaluation | Infrastructure TESTED IN ISOLATION | Frozen reproduction; actual profitable option strategy not established |
| Genuine option-reference path | TESTED IN ISOLATION; live data BLOCKED | OPRA403; no genuine live contract/premium is supplied by a fixture |
| Three-session engineering acceptance | IMPLEMENTED, EXTERNAL VERIFICATION PENDING | Native observer plus new per-session denominator/latency report; future real sessions required |
| Questrade/Reddit/scanner/overnight expansion | DEFERRED OUTSIDE CORE SCOPE | Existing refusal/demo paths retained; no expansion or credential collection |

The module/function index below is a static inventory only. Behavioral coverage follows this map and named tests, not an indexed-function percentage.

| Module | Named functions/methods (static only) |
|---|---|
| core/background_jobs.py | error_fields, __init__, submit, drain, health, close, __init__, _publish, start, finish, summary, run |
| core/bot_commands.py | et_text, execute |
| core/demo.py | run_demo |
| core/directional_research.py | view, record, capture_future_quote, resolve, daily_score |
| core/entry_publication.py | binding, digest, envelope, check |
| core/exchange_calendar.py |  |
| core/feed_health.py | clock_text, text_for, quote_line, stream_line |
| core/fill_flow.py | begin, execute |
| core/idea_config.py | settings |
| core/idea_service.py | context, candidates, trend_line_details, legacy_idea_text, trend_line, idea_text, recap_levels, preopen_text, scheduled_preopen, permit, tick, emit, send, compose |
| core/isolation.py | assert_real |
| core/market_view.py | premarket_view, recap_view, plan_view, plain_reason, build, details, observe |
| core/observed_context.py | evaluate, reject |
| core/paper_actions.py | execute |
| core/paper_chart.py | generate |
| core/paper_service.py | tick |
| core/preflight.py | protected_probe_status, run |
| core/primary_plan.py | current, reserve, state, administrative_close |
| core/proposals.py | evaluate_file |
| core/readiness.py | evaluate, text_for, add |
| core/readonly_state.py | idea_rows, __init__, get, snapshot, put, close |
| core/rejection_trace.py | reason_codes, measure, persist, summary |
| core/research_horizons.py | deadline, from_snapshot, context, describe, candidates |
| core/research_pause.py | advance |
| core/runtime_paths.py | python_executable, node_executable, private_directory |
| core/service.py | read, market, snapshot, notification_status, proposal_status, review |
| core/sessions.py | market_session |
| core/signals.py | tier, build, quote_valid, option_quote_valid, finalize, dict |
| core/simple_config.py | number, validate_new |
| core/spy_research.py | session, analyze, once, run, current |
| core/storage.py | utcnow, iso, encode, __init__, close, transaction, put, put_many, get, reserve, merge_rows, snapshot, event, events, audit, write, write, write, write, write, canonical, write |
| core/upgrade_service.py | read_config, validate_config, fresh, books, enqueue, position_monitoring_incident, reconcile_monitoring_holdings, snapshot, __init__, check, __init__, collect, market_result, maintenance_calendar, close, tick, run, due, stop, idea_publish, prepare, quote_result, sample_result |
| core/v6_service.py | __init__, close, tick |
| core/verdict.py | next_open, direction_of, short, why, current, option_evaluation |
| data/backfill.py | history, continuity, __init__, close, run, tick, __init__, _run, tick, health, close |
| data/clock_health.py | decode_offset, measure, tick, read |
| data/corporate_actions.py | collect |
| data/credentials.py | validate, child_environment, configured, save, configure |
| data/key_verification.py | verify |
| data/local_setup.py | parse_keys, parse_reddit, allowed_request, main, launch, __init__, setup, log_message, reply, valid, do_GET, do_POST |
| data/massive_research.py | __init__, health, get, get_bars, get_underlying_quote, get_option_quote, get_option_chain, get_market_status |
| data/models.py | stamp, finite, quote, unavailable, view |
| data/premarket_authorized.py | collect, verified |
| data/premarket_spy.py | save, collect_once, verified |
| data/providers.py | get_underlying_quote, get_bars, get_option_chain, get_option_quote, get_market_status, health, __init__, get_underlying_quote, get_bars, get_option_chain, get_option_quote, get_market_status, health, __init__, health, get, fail, get_underlying_quote, get_option_quote, get_bars, get_option_chain, __init__, get_bars, __init__, request |
| data/public_https.py | download |
| data/public_spy.py | parse_chart, collect |
| data/questrade.py | origin, transport, redirect_request, __init__, session, limit, get, health, id, parse_quote, fail, get_underlying_quote, get_bars, get_option_chain, get_option_quote, get_market_status, keep_alive |
| data/questrade_check.py | check, main |
| data/questrade_vault.py | locked, __init__, load, save, configure, status |
| data/reliability.py | active, watchdog_age, connection_watchdog_age, quote_diagnostics, describe, __init__, add, close, __init__, check |
| data/replay.py | __init__, datum, get_underlying_quote, get_bars, get_option_chain, get_option_quote, get_market_status, health |
| data/research_hub.py | enrich |
| data/research_inputs.py | safe_url, clean_headline, fresh_headlines, headline_status, __init__, headlines, historical_option_bars, discover_contracts |
| data/secondary_spy.py | parse_daily, collect, refresh |
| data/session_recorder.py | tick, __init__, close, bars, chain, iv_history |
| data/spy_feed.py | validate_quote, fetch_quotes, get |
| data/stream.py | decode, encode, run_feed, main, __init__, log, pulse, key, status, symbols, clock_rejection, clock_recovered, ingest, run, wait, run, stop, watch |
| data/trend_spy.py | load, refresh_lock, refresh |
| features/indicators.py | normalize, resample, ema, calculate, multi_timeframe, from_normalized |
| features/market_regime.py | classify |
| features/spy_patterns.py | describe |
| strategies/concretum.py | complete, bands, decision, share_count, session_replay |
| strategies/idea_setups.py | pending_triggers, levels, detect |
| strategies/idea_setups_v3.py | pending_triggers, levels, detect |
| strategies/published_baselines.py | concretum_signal, first_last, opening_range, compare, compare_context |
| strategies/spy_setups.py | detect |
| options/chain_sanity.py | verify |
| options/command.py | main |
| options/contract_selector.py | expected_move, select |
| options/ledger.py | contract, amount, __init__, close, effective_events, positions, record, void, same |
| options/research_contract.py | current_reference, verified_plan |
| options/trade_plan.py | mismatch, sanity, estimated_bid, horizon, build, exit_conditions |
| backtesting/baseline.py | signal, simulate, parse_data, main |
| backtesting/forward_validation.py | __init__, close, record, observe |
| backtesting/history_sampler.py | window, collect |
| backtesting/idea_tracker.py | evidence, score_text, __init__, close, append, positions, register, observe, summary |
| backtesting/option_baseline.py | open_baseline |
| backtesting/option_dataset.py | inspect |
| backtesting/option_research.py | number, safe_url, _read_component, load, select, replay, random_direction, portfolio, portfolio_marks, assess, __init__, _provenance, quote, chain |
| backtesting/paper_engine.py | __init__, positions, risk_state, open, valid_quote, mark |
| backtesting/premium_accuracy.py | __init__, close, observe, report, stats |
| backtesting/proxy_engine.py | critical_t, candidate, __init__, close, positions, append, risk_state, open, mark, summary, stats |
| backtesting/research_protocol.py | aware, digest, trials, declaration, register, deadline, assign_splits, partition_candidates, re_hash, freeze_selection |
| backtesting/research_statistics.py | _closed, metrics, interval, paired_comparison, concentration, overlap, summarize |
| backtesting/test_baseline.py | setUp, test_signal_cannot_observe_future, test_shock_does_not_create_its_own_exposure, test_entry_and_exit_costs, test_previous_close_signal_waits_one_full_session, test_increasing_cost_reduces_same_path_wealth, test_cash_flat_and_zero_cost, test_buy_hold_matches_endpoints |
| backtesting/underlying_study.py | load_bars, price_frame, _daily, feature_snapshots, generate, context, outcome, evaluate |
| research/basic_trend.py | analyze, text_for, saved_text, on_demand_text |
| research/closing_estimate.py | refresh, load, quantile, estimate |
| research/forward_study.py | verified_cache, rows_from_disk, tick, summary |
| research/live_trend.py | _evaluate_feed, evaluate, text_for |
| research/ratio_study.py | tick, summary, text_for |
| research/shadow_evaluation.py | evaluate |
| research/shadow_forecast.py | sha, future_starts, prepare, validate_result, earlier_session_baseline, __init__, append, close |
| research/source_consensus.py | daily_context, compare_intraday, message_context |
| monitoring/day_schedule.py | due, dispatch |
| monitoring/exit_text.py | format_review |
| monitoring/message_format.py | number, et, plain, measured, horizon_rows, horizon_bias, status_text, idea_text, diagnostics_text, update_text, health_text, interval, score_summary_text, paper_summary_text, position_review_text |
| monitoring/owner_messages.py | price, clock, next_event, reason, status_text, premarket_text, i_verification, verified_option, idea_text, update_text, recap_text |
| monitoring/paper_alerts.py | signal_text, reserve, emit, candidate_alert, position_alerts, lifecycle |
| monitoring/position_monitor.py | review |
| monitoring/position_rules.py | review_deadline |
| monitoring/premarket_brief.py | settings, previous_session, aggregate, build, text_for, update, saved_text, command_text |
| monitoring/receipt_observer.py | __init__, _run, poll, close |
| monitoring/research_alerts.py | settings, load, observe, text_for, context, short_text, changes, change_text, update |
| monitoring/research_populations.py | horizon_summary, horizon_text |
| monitoring/sharing.py | display |
| monitoring/simple_notifications.py | enabled, alerts, calendar_warning, source_pushes |
| monitoring/telegram_test.py | safe_error, main, redirect_request, call |
| monitoring/test_telegram_diagnostics.py | test_auth_error_excludes_secret_url_and_message, test_network_error_never_echoes_reason, test_send_timeout_marks_delivery_uncertain, test_local_error_redacts_details |
| monitoring/trend_evidence.py | record, session_slots |
| monitoring/vault.py | transform, main |
| ops/alert_audit.py | path_outcome, audit, load, ro |
| ops/backup.py | backup, restore |
| ops/ci_tests.py |  |
| ops/completion_verification.py | read, artifact, latest_session, compact_historical_duplicates, extend, checked, latest |
| ops/data_readiness_probe.py | probe, main |
| ops/day_simulation.py | config, inputs, run_scenario, verify, __init__, get, put, event, events, publish |
| ops/demo.py | wrap, fixture, chart, response, v5_result, v5_scene, v5_variant, run, console, __init__, send |
| ops/entry_check.py | main |
| ops/heartbeat.py | validate_url, tick, send |
| ops/hygiene.py | inspect, check, write |
| ops/kronos_infer.py | main, safe_raw |
| ops/live_verify.py | public_crosscheck, sample, report, scheduled |
| ops/master_demo.py | gallery, main |
| ops/master_session.py | summarize, collect, main |
| ops/premium_cap.py | observe, report |
| ops/primary_admin.py | main |
| ops/primary_comparison.py | summarize, run |
| ops/published_replay.py | replay, main |
| ops/receipts.py | listing, confirm, main |
| ops/release_guard.py | path_problem, inspect, git, git_entries, collect, main |
| ops/report.py | option_paper_report, paper_report, grouped |
| ops/reproduce_research.py | _safe_write, compute, report_text, create_run, reproduce, main |
| ops/session_report.py | ro, query, count, receipts, collect, write, main, state |
| ops/setup.py | initialize, safe_status, telegram_api, pair, configure_telegram, main, call, wait |
| ops/setup_shadow.py | fetch, main |
| ops/shadow_benchmark.py | main |
| ops/shadow_worker.py | available_memory, environment, windows_job, bounded, collect_request, step, main, communicate |
| ops/supervisor.py | child_python, runtime_environment, publish_status, alive, clean_stale, stream_restart_due, clear_previous_shutdown, run, start, status, main, shutdown, read, get |
| ops/test_runner.py | run, count, decoded |
| ops/trend_rule_comparison.py | run, main |
| ops/v5_verification.py | extend |
| ops/v6_simulation.py | cases, result, enqueue |
| ops/v6_verification.py | extend |
| ops/verification_packet.py | scan, redact, redact_deep, safe_config, read_json, sha, ro, database, state, manifest, requirements, generated_samples, collect, compact, write, main, shrink, get |
| ops/verify_commands.py | verify |
| dashboard/snapshot_cache.py | _loader, empty_snapshot, _quote, recheck, deactivate, __init__, _run, get |
