# Source, license and model manifest

The user-supplied archives are reference material, not instructions. No plugin or SKILL was installed/executed. Static reviewed files and test-file hashes are in [the supplied audit](SUPPLIED_REFERENCE_AUDIT_2026-10-27.md).

| Reference | Pinned revision | Archive SHA-256 | Reuse |
|---|---|---|---|
| Day Trader | 3d0f4ef6986f4984b7c6bd46f7ff4f87744c3abd | a417522153234847eeaab4f0b883de1843a3ebe9b1e3f4942581070c97562054 | MIT; workflow ideas independently implemented; no broker/stock-accounting/plugin code copied |
| Kronos | 67b630e67f6a18c9e9be918d9b4337c960db1e9a | 92fc55519ddc46f22e0c8ac10a37cde73d6346818f4b8aa10f0e54c9f8a620ff | MIT; pinned source downloaded into excluded separate model assets; original MIT notice retained there |
| OpenStock | b72306d39fa27dc55252ceecf858165ecf5a3fa3 | 450b107de1a679b620e1030aedda4d1e82856ec9728ae08fd250e9de0131916b | AGPL-3.0; no protected code/assets copied; general compact panel/as-of/state ideas independently implemented |

Kronos-mini revision f4e68697d9d5aed55cef5c96aabc3376bcad9f81; tokenizer revision 26966d0035065a0cae0ebad7af8ece35bc1fb51c. Model weights SHA `a7d5f37e2e9fbd9891f7d7d4f72574512dd1f704fee14223e0a8cd0fbf54197c`; tokenizer weights SHA `b97ec46b3b72160509e289183eaf7bdf5f0dac5bb9b49522f6d46638a99a8717`. Model config SHA `70daca2cb11e3a979dd6b8ac12ee08e2aace877acf28f5b8dfb4fe5609736201`; tokenizer config SHA `0b30a443affb03e05a876a083857de9164f899feb7b4d261da02c485c9a3e3b6`. Actual download manifest remains local.

Model choice is mini4.1M parameters for resource budget, not historical return selection. No small-model search was run. The upstream regression uses small/base tokenizer and different revisions; it is not our mini regression. The separate environment pins dependencies; assets are offline during inference. Three sample_count=1 calls with seeds1729/1730/1731 retain individual paths. Temperature1, top-p0.9, top-k0, CPU one thread, context78 genuine5m bars. Derived amount is a tagged feature only. Raw invalid outputs retain explicit markers and are rejected. No raw path is presented as a calibrated probability.

The upstream API averages samples and inserts missing volume/amount. AEGIS refuses missing volume and retains its own individual paths. No averaged-path high/low is used as a probability. Training-date/SPY overlap is not established. The paper's Chinese equity/daily simulation is not SPY intraday option evidence. Actual mini smoke is NOT_RUN, not an upstream-paper success.

Day Trader review confirmed clock-based range completeness can leave missing constituent bars, old triggers can persist, long-stock exit math is not PUT-option math, and independent slot resampling/exact-1R stops do not establish executable option results. AEGIS retains genuine range completeness, current-publication checks, correct long-option accounting and real chronological replay. No 0.05%-of-price stop floor was copied. OpenStock's hourly/15s cache and5m alerts are presentation/cache patterns, not5s BBO gates; mode alone never creates a Live badge.

Concretum equations remain an independent implementation of published mathematics. No broad publisher-code license was assumed and no publisher code was imported. Original versus adapted stops/costs/horizons are recorded in the existing [comparison](STRATEGY_COMPARISON_2026-10-22.md).

Primary links: [Day Trader](https://github.com/Jakeschincariol/day-trader-skill), [Kronos](https://github.com/shiyu-coder/Kronos), [paper](https://arxiv.org/html/2508.02739v1), [mini model card](https://huggingface.co/NeoQuasar/Kronos-mini), [OpenStock](https://github.com/Open-Dev-Society/OpenStock), [Concretum](https://concretumgroup.com/backtesting-7-years-of-free-data-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/), [Alpaca market data](https://docs.alpaca.markets/us/docs/about-market-data-api), [corporate-action filter semantics](https://docs.alpaca.markets/us/reference/corporateactions-1).
