# Token-Savings Potential

Crystal can reduce repeated conversation-history input in long sessions, but the savings must be measured against the compression Hermes would already perform.

## Four accounting layers

Keep these numbers separate:

1. **Gross history reduction** — reduction of only the replaceable conversation-history slice at a Crystal boundary.
2. **Post-compression total-request reduction** — reduction after including the fixed system/tool prompt and comparing with default Hermes compression.
3. **Full-day net logical-token reduction** — weights calls before and after the first boundary and subtracts Facet, Crystallizer, and Gem Cutter maintenance.
4. **Billable-equivalent or dollar reduction** — also depends on provider caching and billing mode.

A large history ratio is not a daily savings claim.

## Calibrated planning range

One measured busy-session calibration produced:

- 386,895 estimated source-history tokens across three Crystal boundaries;
- 22,845 estimated Crystal replacement tokens;
- **94.1% gross reduction of the replaceable history slice**;
- about **32–38% estimated reduction in total request size after a boundary** once the fixed prompt and default Hermes compression were included.

For two genuinely busy, long front-door sessions, a defensible planning estimate is:

- **about 30% net logical tokens saved** as a single planning number;
- **25–35%** as a normal busy-day range;
- potentially **35–45%** for very long, tool-heavy sessions;
- near **0%**, or slight overhead, for short sessions that never reach a compression boundary.

The measured 94.1% figure applies only to the history slice. Do not present it as total request, daily, billable, or dollar savings.

## Estimation method

For each Crystal replacement boundary:

```text
history_reduction
  = 1 - crystal_replacement_history / source_history

default_total_request
  = fixed_system_and_tools + default_compressed_history

crystal_total_request
  = fixed_system_and_tools + crystal_render + hot_tail

post_boundary_request_reduction
  = 1 - crystal_total_request / default_total_request
```

Then estimate the day:

```text
full_day_net
  ~= post_boundary_request_reduction
     * share_of_calls_after_first_boundary
     - crystal_worker_maintenance_drag
```

Use token estimates consistently on both sides. Do not mix character estimates, provider-reported tokens, and cached-input counters without labeling the difference.

## Inputs that materially change the result

Recompute when any of these changes:

- model context window;
- default Hermes threshold, target ratio, tail budget, or summary behavior;
- stable system prompt and tool-schema size;
- Crystal render budget and hot-tail size;
- Facet, Crystallizer, or Gem Cutter cadence;
- session length and tool-result volume;
- provider cache pricing and billing mode.

## Telemetry for honest reports

Track latest and cumulative values without storing transcript content:

- provider input/output and cache-read input when available;
- Crystal render and hot-tail tokens;
- source and replacement estimates at every boundary;
- replacement and fallback counts;
- per-worker calls and input/output tokens;
- maintenance tokens per meaningful turn;
- Gem Cutter no-op and rewrite distribution;
- quality flags that caused maintenance.

A single cumulative provider counter is not enough unless callback frequency and cached-input semantics are understood.

## Interpretation

Crystal mainly helps long sessions after they cross a compression boundary. It is not a universal per-call discount. Short conversations can see no benefit and may incur small maintenance overhead. Logical-token savings can also exceed billable savings when the provider discounts cached input, while subscription plans may expose no useful dollar comparison at all.
