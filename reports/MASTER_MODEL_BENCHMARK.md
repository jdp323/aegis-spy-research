# Model resources and failure isolation

Actual mini inference: **NOT_RUN**. Preflight measured 212418560 available bytes against 1610612736 required. Refusal took 0.015999999828636646s. This2GB host did not safely meet the1536MiB-free headroom requirement; the separate neural environment was not installed. Pinned public weights/code were downloaded and hashed. No invented neural forecast, latency or profitability is reported.

The model worker is a separate supervised process. It has no Telegram producer or entry authority. Its child is offline, has a45s wall deadline,768MiB Windows job memory bound, one torch/BLAS thread and low process priority. It refuses without headroom and stops if headroom falls below512MiB. Output is bounded on disk instead of accumulated in RAM. Provider/AI/bot secrets are excluded from the environment. Each result is append-only in its own database, with cutoff/source/input/model/config hashes and actual completion/availability. Restart read times do not duplicate an identical trial; changed input data is a new revision.

Actual isolated Python fixture results (not neural benchmarks):

| Fixture | Result | Seconds |
|---|---|---:|
| timeout | TIMEOUT | 0.5 |
| malformed | CONTAINMENT_OR_PROTOCOL_FAILED | 0.219 |
| crash | MODEL_PROCESS_FAILED | 0.203 |
| memory | MODEL_PROCESS_FAILED | 0.188 |
| output | OUTPUT_TOO_LARGE | 0.265 |

Parent progress: 45 ticks; largest measured tick gap 0.031999999890103936s. These128MiB-capped fixture children used injected preflight headroom solely to exercise containment. They do not establish that actual neural inference preserves live-session deadlines. That remains a future operational measurement.

After adequate memory is available, run the separate setup and genuine completed-input benchmark in SETUP.md. Missing weights, bad dimensions/OHLC, nonfinite outputs, future/partial/gapped inputs, expiry/early-close/DST and append-only records are covered by isolated tests. Real pinned mini deterministic regression is explicitly pending, not silently counted as a skipped passing test.
