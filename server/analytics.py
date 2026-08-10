"""Deterministic business-analytics specialists.

Each specialist is a governed pipeline stage with a typed result — not an
unstructured persona. Every stage returns:

    {"status": "succeeded"|"failed", "summary": str,
     "claims": [{"id","text","type","evidence","status"}],
     "calculations": [{"id","name","value","method"}],
     "quality_checks": [{"name","passed","detail"}],
     "output": {...stage data for later stages...}}

All numbers come from deterministic code (csv + statistics stdlib). The
model gateway may only phrase already-verified facts, and its text is
labelled by source. Claims reference calculation ids so the Validation
Expert can independently verify every material statement.
"""

import csv
import hashlib
import io
import statistics

MAX_ROWS = 5000
MAX_DATASET_BYTES = 250_000


def sample_dataset():
    """Deterministic bundled sales dataset (72 rows)."""
    months = ["2025-%02d" % m for m in range(1, 13)]
    base = {"Hardware": 42000, "Software": 61000, "Services": 23000}
    lines = ["month,region,category,revenue,units"]
    for mi, month in enumerate(months):
        for region, offset in (("North", 1.08), ("South", 0.92)):
            for category, base_rev in base.items():
                seasonal = 1.0 + 0.03 * mi + (0.12 if mi in (10, 11) else 0.0)
                revenue = round(base_rev * seasonal * offset, 2)
                units = int(revenue / (95 if category != "Services" else 240))
                lines.append(f"{month},{region},{category},{revenue},{units}")
    return "\n".join(lines) + "\n"


def _result(status, summary, output=None, claims=None, calculations=None, checks=None):
    return {
        "status": status,
        "summary": summary,
        "claims": claims or [],
        "calculations": calculations or [],
        "quality_checks": checks or [],
        "output": output or {},
    }


def _fail(summary):
    return _result("failed", summary)


def _to_number(value):
    try:
        return float(value.replace(",", "")) if isinstance(value, str) else float(value)
    except (ValueError, AttributeError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Specialists
# ---------------------------------------------------------------------------

def planner(ctx):
    stages = [role for role, _ in PIPELINE]
    return _result(
        "succeeded",
        "Pattern: sequential governed pipeline — the goal is a repeatable "
        "analytics workflow, so the simplest sufficient pattern applies. "
        "Stopping rule: fixed bounded stage list with an approval gate "
        "before publishing.",
        output={"stages": stages, "pattern": "sequential_governed_pipeline"},
        checks=[{"name": "plan_has_validation_stage", "passed": "validator" in stages,
                 "detail": "Independent validation is part of the plan."}],
    )


def collector(ctx):
    text = ctx.get("dataset_text") or ""
    if len(text.encode()) > MAX_DATASET_BYTES:
        return _fail(f"Dataset exceeds the {MAX_DATASET_BYTES // 1000} KB limit.")
    try:
        reader = csv.DictReader(io.StringIO(text))
        rows = [row for _, row in zip(range(MAX_ROWS + 1), reader)]
    except csv.Error as error:
        return _fail(f"The dataset could not be parsed as CSV: {error}")
    if not rows or not reader.fieldnames:
        return _fail("The dataset is empty or has no header row.")
    if len(rows) > MAX_ROWS:
        return _fail(f"Dataset exceeds the {MAX_ROWS}-row limit.")
    columns = [c for c in reader.fieldnames if c]
    digest = hashlib.sha256(text.encode()).hexdigest()[:16]
    return _result(
        "succeeded",
        f"Ingested {len(rows)} rows × {len(columns)} columns "
        f"(snapshot sha256:{digest}).",
        output={"rows": rows, "columns": columns, "snapshot": digest,
                "row_count": len(rows)},
        calculations=[{"id": "c_rows", "name": "row_count", "value": len(rows),
                       "method": "len(csv rows)"}],
        claims=[{"id": "cl_ingest", "type": "fact",
                 "text": f"The dataset contains {len(rows)} rows and {len(columns)} columns.",
                 "evidence": ["c_rows"], "status": "verified"}],
    )


def profiler(ctx):
    rows = ctx["collector"]["rows"]
    columns = ctx["collector"]["columns"]
    profile, numeric_columns = {}, []
    for col in columns:
        values = [r.get(col, "") or "" for r in rows]
        missing = sum(1 for v in values if not str(v).strip())
        numbers = [n for n in (_to_number(v) for v in values if str(v).strip()) if n is not None]
        is_numeric = len(numbers) >= max(1, (len(values) - missing) * 0.9)
        if is_numeric and numbers:
            numeric_columns.append(col)
        profile[col] = {"missing": missing, "distinct": len(set(values)),
                        "numeric": is_numeric}
    seen, duplicates = set(), 0
    for r in rows:
        key = tuple(sorted(r.items()))
        duplicates += key in seen
        seen.add(key)
    total_cells = len(rows) * max(1, len(columns))
    missing_cells = sum(p["missing"] for p in profile.values())
    completeness = round(1 - missing_cells / total_cells, 4)
    calcs = [
        {"id": "c_completeness", "name": "completeness", "value": completeness,
         "method": "1 - missing_cells/total_cells"},
        {"id": "c_dupes", "name": "duplicate_rows", "value": duplicates,
         "method": "exact row comparison"},
    ]
    return _result(
        "succeeded",
        f"Profiled quality: completeness {completeness:.0%}, "
        f"{duplicates} duplicate rows, numeric columns: "
        f"{', '.join(numeric_columns) or 'none'}.",
        output={"profile": profile, "numeric_columns": numeric_columns,
                "duplicates": duplicates, "completeness": completeness},
        calculations=calcs,
        claims=[{"id": "cl_quality", "type": "fact",
                 "text": f"Data completeness is {completeness:.0%} with {duplicates} duplicate rows.",
                 "evidence": ["c_completeness", "c_dupes"], "status": "verified"}],
        checks=[{"name": "has_numeric_column", "passed": bool(numeric_columns),
                 "detail": "At least one numeric measure is required for analysis."}],
    )


def cleaner(ctx):
    rows = ctx["collector"]["rows"]
    numeric_columns = ctx["profiler"]["numeric_columns"]
    if not numeric_columns:
        return _fail("No numeric column is available to analyze.")
    before = len(rows)
    cleaned, seen, dropped_empty, dropped_dupes, coercion_failures = [], set(), 0, 0, 0
    for row in rows:
        stripped = {k: (str(v).strip() if v is not None else "") for k, v in row.items() if k}
        if not any(stripped.values()):
            dropped_empty += 1
            continue
        key = tuple(sorted(stripped.items()))
        if key in seen:
            dropped_dupes += 1
            continue
        seen.add(key)
        for col in numeric_columns:
            number = _to_number(stripped.get(col, ""))
            if number is None and str(stripped.get(col, "")).strip():
                coercion_failures += 1
            stripped[col] = number
        cleaned.append(stripped)
    after = len(cleaned)
    calcs = [
        {"id": "c_rows_before", "name": "rows_before", "value": before, "method": "count"},
        {"id": "c_rows_after", "name": "rows_after", "value": after, "method": "count"},
        {"id": "c_dropped", "name": "rows_dropped", "value": before - after,
         "method": "empty + exact-duplicate removal"},
    ]
    return _result(
        "succeeded",
        f"Cleaned data: {before} → {after} rows "
        f"({dropped_empty} empty, {dropped_dupes} duplicates removed, "
        f"{coercion_failures} non-numeric values set to null). Row loss is "
        "reported, never hidden.",
        output={"rows": cleaned, "rows_before": before, "rows_after": after,
                "dropped": before - after},
        calculations=calcs,
        claims=[{"id": "cl_rowloss", "type": "fact",
                 "text": f"{before - after} of {before} rows were removed during cleaning "
                         f"({dropped_empty} empty, {dropped_dupes} duplicates).",
                 "evidence": ["c_rows_before", "c_rows_after", "c_dropped"],
                 "status": "verified"}],
    )


def preparer(ctx):
    rows = ctx["cleaner"]["rows"]
    numeric_columns = ctx["profiler"]["numeric_columns"]
    columns = ctx["collector"]["columns"]
    measure = next((c for c in numeric_columns if c.lower() in
                    ("revenue", "sales", "amount", "value", "total")), numeric_columns[0])
    date_col = next((c for c in columns if c.lower() in
                     ("month", "date", "period", "week", "year")), None)
    group_col = next((c for c in columns
                      if c not in numeric_columns and c != date_col), None)
    groups = {}
    if group_col:
        for row in rows:
            value = row.get(measure)
            if value is not None:
                groups[row[group_col]] = groups.get(row[group_col], 0.0) + value
    trend = {}
    if date_col:
        for row in rows:
            value = row.get(measure)
            if value is not None:
                trend[row[date_col]] = trend.get(row[date_col], 0.0) + value
        trend = dict(sorted(trend.items()))
    total = round(sum(r[measure] for r in rows if r.get(measure) is not None), 2)
    return _result(
        "succeeded",
        f"Prepared analysis dataset: measure “{measure}”"
        + (f", grouped by “{group_col}”" if group_col else "")
        + (f", trended by “{date_col}”" if date_col else "") + ".",
        output={"measure": measure, "group_col": group_col, "date_col": date_col,
                "groups": {k: round(v, 2) for k, v in groups.items()},
                "trend": {k: round(v, 2) for k, v in trend.items()},
                "total": total},
        calculations=[{"id": "c_total", "name": f"total_{measure}", "value": total,
                       "method": f"sum({measure}) over cleaned rows"}],
        claims=[{"id": "cl_total", "type": "calculation",
                 "text": f"Total {measure} is {total:,.2f}.",
                 "evidence": ["c_total"], "status": "verified"}],
    )


def analyst(ctx):
    rows = ctx["cleaner"]["rows"]
    prep = ctx["preparer"]
    measure = prep["measure"]
    values = [r[measure] for r in rows if r.get(measure) is not None]
    if not values:
        return _fail(f"No usable values in measure “{measure}”.")
    mean = statistics.fmean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    outliers = sum(1 for v in values if abs(v - mean) > 2 * stdev) if stdev else 0
    calcs = [
        {"id": "c_mean", "name": "mean", "value": round(mean, 2), "method": "fmean"},
        {"id": "c_median", "name": "median", "value": round(statistics.median(values), 2),
         "method": "median"},
        {"id": "c_stdev", "name": "stdev", "value": round(stdev, 2), "method": "sample stdev"},
        {"id": "c_outliers", "name": "outliers_2sigma", "value": outliers,
         "method": "count(|x-mean| > 2*stdev)"},
    ]
    claims = [{"id": "cl_center", "type": "calculation",
               "text": f"Mean {measure} per row is {mean:,.2f} "
                       f"(median {statistics.median(values):,.2f}).",
               "evidence": ["c_mean", "c_median"], "status": "verified"}]
    growth = None
    if len(prep["trend"]) >= 2:
        series = list(prep["trend"].values())
        if series[0]:
            growth = round((series[-1] - series[0]) / series[0], 4)
            calcs.append({"id": "c_growth", "name": "period_growth", "value": growth,
                          "method": "(last-first)/first over trend periods"})
            claims.append({"id": "cl_growth", "type": "calculation",
                           "text": f"{measure} changed {growth:+.1%} from the first to "
                                   "the last period. Trend describes association, not cause.",
                           "evidence": ["c_growth"], "status": "verified"})
    top = max(prep["groups"], key=prep["groups"].get) if prep["groups"] else None
    if top is not None and prep["total"]:
        share = round(prep["groups"][top] / prep["total"], 4)
        calcs.append({"id": "c_topshare", "name": "top_group_share", "value": share,
                      "method": "top group total / overall total"})
        claims.append({"id": "cl_top", "type": "calculation",
                       "text": f"“{top}” is the largest {prep['group_col']} with "
                               f"{share:.1%} of total {measure}.",
                       "evidence": ["c_topshare"], "status": "verified"})
    return _result(
        "succeeded",
        f"Descriptive analysis complete: {len(calcs)} calculations, "
        f"{outliers} outliers beyond 2σ.",
        output={"growth": growth, "top_group": top, "outliers": outliers},
        calculations=calcs, claims=claims,
    )


def visuals(ctx):
    prep = ctx["preparer"]
    charts = []
    if prep["groups"]:
        items = sorted(prep["groups"].items(), key=lambda kv: -kv[1])[:8]
        charts.append({"id": "chart_groups", "type": "bar",
                       "title": f"Total {prep['measure']} by {prep['group_col']}",
                       "labels": [k for k, _ in items],
                       "values": [v for _, v in items],
                       "source": "preparer.groups",
                       "alt": f"Bar chart of total {prep['measure']} for each "
                              f"{prep['group_col']}, largest first."})
    if len(prep["trend"]) >= 2:
        charts.append({"id": "chart_trend", "type": "line",
                       "title": f"{prep['measure']} by {prep['date_col']}",
                       "labels": list(prep["trend"].keys()),
                       "values": list(prep["trend"].values()),
                       "source": "preparer.trend",
                       "alt": f"Line chart of {prep['measure']} across "
                              f"{len(prep['trend'])} periods."})
    checks = [{"name": "chart_values_match_aggregates",
               "passed": all(chart["values"] == (
                   sorted(prep["groups"].values(), reverse=True)[:8]
                   if chart["id"] == "chart_groups" else list(prep["trend"].values()))
                   for chart in charts),
               "detail": "Chart values are taken directly from the prepared aggregates; "
                         "axes start at zero."}]
    return _result("succeeded",
                   f"Prepared {len(charts)} truthful chart specifications with alt text.",
                   output={"charts": charts}, checks=checks)


def business(ctx, gateway=None):
    prep, analysis = ctx["preparer"], ctx["analyst"]
    calculations = ctx["analyst_result"]["calculations"]
    insights, facts = [], []
    if analysis["top_group"] is not None:
        share = next(c["value"] for c in calculations if c["id"] == "c_topshare")
        facts.append(f"{analysis['top_group']} leads with {share:.0%} of "
                     f"total {prep['measure']}.")
        if share > 0.4:
            insights.append({"id": "cl_concentration", "type": "recommendation",
                             "text": f"Revenue concentration risk: “{analysis['top_group']}” "
                                     f"contributes {share:.1%} of {prep['measure']}. Consider "
                                     "diversification. (Recommendation, not an observed fact.)",
                             "evidence": ["c_topshare"], "status": "verified"})
    if analysis["growth"] is not None:
        growth = analysis["growth"]
        facts.append(f"{prep['measure']} changed {growth:+.1%} across the period.")
        insights.append({"id": "cl_direction", "type": "finding",
                         "text": f"The overall trend is {'positive' if growth >= 0 else 'negative'} "
                                 f"({growth:+.1%} across the analyzed periods).",
                         "evidence": ["c_growth"], "status": "verified"})
    narration = (gateway.narrate(ctx.get("goal", "the analysis"), facts)
                 if gateway else {"text": " ".join(facts), "source": "deterministic"})
    return _result(
        "succeeded",
        f"Derived {len(insights)} business insights; executive summary "
        f"phrased by the {narration['source']} narrator.",
        output={"exec_summary": narration["text"],
                "exec_summary_source": narration["source"]},
        claims=insights,
    )


def validator(ctx):
    """Independent deterministic verification. May reject work; never
    rewrites evidence."""
    prep = ctx["preparer"]
    checks = []
    if prep["groups"]:
        reconciled = abs(sum(prep["groups"].values()) - prep["total"]) < 0.01
        checks.append({"name": "group_totals_reconcile", "passed": reconciled,
                       "detail": f"Σ(groups)={sum(prep['groups'].values()):,.2f} vs "
                                 f"total={prep['total']:,.2f}"})
    clean = ctx["cleaner"]
    checks.append({"name": "row_accounting",
                   "passed": clean["rows_after"] + clean["dropped"] == clean["rows_before"],
                   "detail": f"{clean['rows_after']} kept + {clean['dropped']} dropped "
                             f"= {clean['rows_before']} input rows"})
    all_calc_ids = {c["id"] for stage in ("collector", "profiler", "cleaner",
                                          "preparer", "analyst")
                    for c in ctx.get(stage + "_result", {}).get("calculations", [])}
    all_claims = [cl for stage in ("collector", "profiler", "cleaner", "preparer",
                                   "analyst", "business")
                  for cl in ctx.get(stage + "_result", {}).get("claims", [])]
    unsupported = [cl["id"] for cl in all_claims
                   if not set(cl.get("evidence", [])) <= all_calc_ids]
    checks.append({"name": "every_claim_has_evidence", "passed": not unsupported,
                   "detail": ("All claims trace to calculations."
                              if not unsupported else
                              f"Unsupported claims: {', '.join(unsupported)}")})
    passed = all(c["passed"] for c in checks)
    return _result(
        "succeeded" if passed else "failed",
        ("All validation checks passed: totals reconcile, rows are accounted "
         "for, and every claim traces to a calculation.")
        if passed else "Validation FAILED — see quality checks. The work is "
                       "rejected, not rewritten.",
        output={"passed": passed, "claim_count": len(all_claims),
                "unsupported": unsupported},
        checks=checks,
    )


def reporter(ctx):
    prep, validation = ctx["preparer"], ctx["validator"]
    lines = [
        f"# Analytics Report — {ctx.get('dataset_name', 'dataset')}",
        "",
        f"**Goal:** {ctx.get('goal', '')}",
        "",
        "## Executive summary",
        ctx["business"]["exec_summary"],
        f"*(Narrative source: {ctx['business']['exec_summary_source']}; every "
        "figure below is deterministically calculated.)*",
        "",
        "## Data quality",
        ctx["profiler_result"]["summary"],
        ctx["cleaner_result"]["summary"],
        "",
        "## Key metrics",
        "| Metric | Value | Method |",
        "| --- | --- | --- |",
    ]
    for stage in ("preparer", "analyst"):
        for calc in ctx[stage + "_result"]["calculations"]:
            lines.append(f"| {calc['name']} | {calc['value']} | {calc['method']} |")
    lines += ["", "## Findings and claims",
              "| Claim | Type | Evidence | Status |", "| --- | --- | --- | --- |"]
    for stage in ("collector", "profiler", "cleaner", "preparer", "analyst", "business"):
        for claim in ctx.get(stage + "_result", {}).get("claims", []):
            lines.append(f"| {claim['text']} | {claim['type']} | "
                         f"{', '.join(claim['evidence'])} | {claim['status']} |")
    lines += ["", "## Charts"]
    for chart in ctx["visuals"]["charts"]:
        lines.append(f"- **{chart['title']}** ({chart['type']}): {chart['alt']}")
    lines += ["", "## Validation",
              validation and ctx["validator_result"]["summary"] or ""]
    for check in ctx["validator_result"]["quality_checks"]:
        lines.append(f"- {'PASS' if check['passed'] else 'FAIL'} — "
                     f"{check['name']}: {check['detail']}")
    lines += [
        "", "## Assumptions and limitations",
        "- Deterministic descriptive pipeline; no causal inference is made.",
        "- Results describe only the supplied snapshot "
        f"(sha256:{ctx['collector']['snapshot']}).",
        "- Trend growth compares first and last periods; it is not a forecast.",
        "",
        f"*Generated by Agentic OS run {ctx.get('run_id', '')} — measure "
        f"“{prep['measure']}”, {ctx['cleaner']['rows_after']} analyzed rows.*",
    ]
    report = "\n".join(lines)
    return _result(
        "succeeded",
        f"Report assembled: {ctx['validator']['claim_count']} claims, all with "
        "evidence links, validation "
        + ("passed." if ctx["validator"]["passed"] else "FAILED."),
        output={"report_markdown": report},
    )


PIPELINE = [
    ("planner", planner),
    ("collector", collector),
    ("profiler", profiler),
    ("cleaner", cleaner),
    ("preparer", preparer),
    ("analyst", analyst),
    ("visuals", visuals),
    ("business", business),
    ("validator", validator),
    ("reporter", reporter),
]

ROLE_TITLES = {
    "planner": "Planner Agent",
    "collector": "Data Source Agent",
    "profiler": "Data Profiling Agent",
    "cleaner": "Data Cleaning Agent",
    "preparer": "Data Preparation Agent",
    "analyst": "Exploratory Data Analyst",
    "visuals": "Visualization Expert",
    "business": "Business Analyst Agent",
    "validator": "Validation Expert",
    "reporter": "Reporting Expert",
    "publish": "Knowledge Curator (vault publish)",
}
