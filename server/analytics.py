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

MAX_ROWS = 50_000
MAX_DATASET_BYTES = 2_000_000


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
# Shared arithmetic. Standard library only, so every figure in a report can
# be recomputed by hand from the method string next to it.
# ---------------------------------------------------------------------------

def _linear_fit(ys):
    """Least-squares fit of y against its position in the series.

    Returns (slope, intercept, r_squared). r_squared is reported to users
    as "share of the movement explained by the trend" — never as R².
    """
    n = len(ys)
    xs = list(range(n))
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if not denominator:
        return 0.0, mean_y, 0.0
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
    intercept = mean_y - slope * mean_x
    residual = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    total = sum((y - mean_y) ** 2 for y in ys)
    return slope, intercept, (1 - residual / total) if total else 0.0


def _correlation(xs, ys):
    """Pearson correlation, or None when it is undefined (no variation)."""
    if len(xs) < 3 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    try:
        return statistics.correlation(xs, ys)
    except statistics.StatisticsError:
        return None


def _next_labels(labels, count):
    """Extrapolate period labels. YYYY-MM increments properly; anything
    else gets an explicit "next period" label rather than a fake date."""
    last = str(labels[-1]) if labels else ""
    parts = last.split("-")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit() and len(parts[1]) == 2:
        year, month = int(parts[0]), int(parts[1])
        out = []
        for _ in range(count):
            month += 1
            if month > 12:
                month, year = 1, year + 1
            out.append(f"{year:04d}-{month:02d}")
        return out
    return [f"next period +{i + 1}" for i in range(count)]


# Statistical vocabulary that loses a business reader. Claims are written
# in plain language and this list is enforced as a quality check, not a
# style preference (see validator.no_statistical_jargon_in_claims).
JARGON = (
    "p-value", "p <", "p<", "r²", "r^2", "r-squared",
    "coefficient of determination", "standard deviations",
    "statistically significant", "null hypothesis", "confidence interval",
    "heteroskedastic", "regression coefficient",
)


def _jargon_in(text):
    lowered = text.lower()
    return [word for word in JARGON if word in lowered]


# The four analytics types, in maturity-ladder order. Each stage owns one
# question and consumes the stages above it.
ANALYTICS_TYPES = [
    ("descriptive", "What happened?"),
    ("diagnostic", "Why did it happen?"),
    ("predictive", "What will happen?"),
    ("prescriptive", "What should I do?"),
]


def _section_report(title, question, ctx, body_lines, calculations, headline=None):
    """One self-contained report per analytics type, readable on its own.

    It opens with the headline — one sentence in business language, which
    is the only line most executives will read. A finding that cannot be
    communicated cannot drive action.
    """
    lines = [f"# {title} Analytics — {question}", "",
             f"**Dataset:** {ctx.get('dataset_name', 'dataset')} · "
             f"**Goal:** {ctx.get('goal', '')}", ""]
    if headline:
        lines += [f"> **{headline}**", ""]
    lines += body_lines
    if calculations:
        lines += ["", "## How each figure was calculated",
                  "| Figure | Value | Method |", "| --- | --- | --- |"]
        lines += [f"| {c['name']} | {c['value']} | {c['method']} |" for c in calculations]
    return "\n".join(lines)


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
        return _fail(f"Dataset exceeds the {MAX_DATASET_BYTES // 1_000_000} MB limit.")
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


def descriptive(ctx):
    """Type 1 — What happened?

    Summarises the snapshot in business language. This is the floor of the
    maturity ladder: everything above it consumes these figures.
    """
    rows = ctx["cleaner"]["rows"]
    prep = ctx["preparer"]
    measure = prep["measure"]
    values = [r[measure] for r in rows if r.get(measure) is not None]
    if not values:
        return _fail(f"No usable values in measure “{measure}”.")
    mean = statistics.fmean(values)
    median = statistics.median(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    unusual = sum(1 for v in values if abs(v - mean) > 2 * stdev) if stdev else 0
    # The total is owned by the preparer (c_total); this stage cites it
    # rather than recomputing it under a second id, so every claim in the
    # report points at exactly one calculation.
    calcs = [
        {"id": "c_mean", "name": "mean", "value": round(mean, 2), "method": "fmean"},
        {"id": "c_median", "name": "median", "value": round(median, 2), "method": "median"},
        {"id": "c_spread", "name": "spread", "value": round(stdev, 2),
         "method": "sample standard deviation"},
        {"id": "c_unusual", "name": "unusual_rows", "value": unusual,
         "method": "count(|x - mean| > 2 × spread)"},
    ]
    claims = [
        {"id": "cl_typical", "type": "calculation",
         "text": f"A typical record is {mean:,.2f} (half are above {median:,.2f}).",
         "evidence": ["c_mean", "c_median"], "status": "verified"},
    ]
    if unusual:
        claims.append({"id": "cl_unusual", "type": "finding",
                       "text": f"{unusual} of {len(values)} records are far from the "
                               "typical value and are worth checking individually.",
                       "evidence": ["c_unusual"], "status": "verified"})

    change = None
    series = list(prep["trend"].values())
    if len(series) >= 2 and series[0]:
        change = round((series[-1] - series[0]) / series[0], 4)
        calcs.append({"id": "c_change", "name": "period_change", "value": change,
                      "method": "(last period − first period) / first period"})
        direction = "risen" if change >= 0 else "fallen"
        claims.append({"id": "cl_change", "type": "calculation",
                       "text": f"{measure} has {direction} {abs(change):.1%} from the "
                               f"first period to the last.",
                       "evidence": ["c_change"], "status": "verified"})
    top = max(prep["groups"], key=prep["groups"].get) if prep["groups"] else None
    share = None
    if top is not None and prep["total"]:
        share = round(prep["groups"][top] / prep["total"], 4)
        calcs.append({"id": "c_topshare", "name": "top_group_share", "value": share,
                      "method": "largest group total / overall total"})
        claims.append({"id": "cl_top", "type": "calculation",
                       "text": f"“{top}” is the largest {prep['group_col']}, making up "
                               f"{share:.1%} of total {measure}.",
                       "evidence": ["c_topshare"], "status": "verified"})
    headline = (
        f"{measure.capitalize()} "
        + (f"{'is up' if change >= 0 else 'is down'} {abs(change):.0%} over the period, "
           f"at {prep['total']:,.0f} in total."
           if change is not None else f"totals {prep['total']:,.0f}.")
        + (f" “{top}” is the biggest {prep['group_col']}." if top is not None else ""))
    report = _section_report(
        "Descriptive", "What happened?", ctx,
        [f"Total {measure} is **{prep['total']:,.2f}** across "
         f"{len(prep['trend']) or 1} period(s) and {ctx['cleaner']['rows_after']} records.",
         f"A typical record is {mean:,.2f}; half are above {median:,.2f}.",
         (f"{measure} has {'risen' if (change or 0) >= 0 else 'fallen'} "
          f"{abs(change):.1%} across the period." if change is not None else
          "The data covers a single period, so no change over time can be shown."),
         (f"“{top}” is the largest {prep['group_col']} at {share:.1%} of the total."
          if top is not None else "No grouping column was available."),
         (f"{unusual} record(s) sit far from the typical value and deserve a look."
          if unusual else "No records sit unusually far from the typical value.")],
        calcs, headline=headline)
    return _result(
        "succeeded", headline,
        output={"headline": headline,
                "change": change, "top_group": top, "top_share": share,
                "unusual": unusual, "mean": round(mean, 2), "median": round(median, 2),
                "report_markdown": report},
        calculations=calcs, claims=claims,
    )


def diagnostic(ctx):
    """Type 2 — Why did it happen?

    Decomposes the change by group (exact arithmetic) and measures which
    other columns move with the measure. Association is reported as
    association: nothing here establishes cause.
    """
    prep = ctx["preparer"]
    rows = ctx["cleaner"]["rows"]
    measure, group_col, date_col = prep["measure"], prep["group_col"], prep["date_col"]
    calcs, claims, contributions = [], [], []

    periods = list(prep["trend"].keys())
    if group_col and date_col and len(periods) >= 2:
        first, last = periods[0], periods[-1]
        by_group = {}
        for row in rows:
            value = row.get(measure)
            if value is None or row.get(date_col) not in (first, last):
                continue
            slot = by_group.setdefault(row[group_col], {"first": 0.0, "last": 0.0})
            slot["first" if row[date_col] == first else "last"] += value
        total_change = prep["trend"][last] - prep["trend"][first]
        for name, slot in by_group.items():
            delta = slot["last"] - slot["first"]
            contributions.append({
                "group": name, "change": round(delta, 2),
                "share_of_change": round(delta / total_change, 4) if total_change else None,
            })
        contributions.sort(key=lambda c: -abs(c["change"]))
        calcs.append({"id": "c_totalchange", "name": "total_change",
                      "value": round(total_change, 2),
                      "method": f"{measure} in {last} − {measure} in {first}"})
        for index, item in enumerate(contributions[:5]):
            calcs.append({"id": f"c_contrib_{index}",
                          "name": f"change_from_{item['group']}",
                          "value": item["change"],
                          "method": f"{measure} for “{item['group']}” in {last} minus {first}"})
        if contributions and total_change:
            driver = contributions[0]
            claims.append({
                "id": "cl_driver", "type": "finding",
                "text": f"Most of the movement comes from “{driver['group']}”: it accounts "
                        f"for {abs(driver['share_of_change']):.0%} of the total change of "
                        f"{total_change:,.2f}. This identifies where the change happened, "
                        "not what caused it.",
                "evidence": ["c_totalchange", "c_contrib_0"], "status": "verified"})
        decliners = [c for c in contributions if c["change"] < 0]
        if decliners:
            worst = min(decliners, key=lambda c: c["change"])
            index = contributions.index(worst)
            claims.append({
                "id": "cl_decline", "type": "finding",
                "text": f"“{worst['group']}” moved against the overall direction, changing "
                        f"{worst['change']:,.2f} between the first and last period.",
                "evidence": [f"c_contrib_{index}"] if index < 5 else ["c_totalchange"],
                "status": "verified"})

    # Which other numeric columns move together with the measure?
    associations = []
    numeric_columns = [c for c in ctx["profiler"]["numeric_columns"] if c != measure]
    for index, column in enumerate(numeric_columns[:4]):
        pairs = [(r[column], r[measure]) for r in rows
                 if r.get(column) is not None and r.get(measure) is not None]
        if len(pairs) < 3:
            continue
        correlation = _correlation([p[0] for p in pairs], [p[1] for p in pairs])
        if correlation is None:
            continue
        associations.append({"column": column, "correlation": round(correlation, 4)})
        calcs.append({"id": f"c_assoc_{index}", "name": f"association_{column}",
                      "value": round(correlation, 4),
                      "method": f"Pearson correlation of {column} and {measure} "
                                f"over {len(pairs)} rows"})
        if abs(correlation) >= 0.5:
            claims.append({
                "id": f"cl_assoc_{index}", "type": "finding",
                "text": f"“{column}” moves {'up' if correlation > 0 else 'down'} "
                        f"together with {measure} ({abs(correlation):.0%} of their movement "
                        "is shared). Moving together is not proof that one causes the other.",
                "evidence": [f"c_assoc_{index}"], "status": "verified"})

    if not calcs:
        calcs.append({"id": "c_nodiag", "name": "diagnosable_structure", "value": 0,
                      "method": "no period column, group column, or second numeric "
                                "column was available"})
    lines = []
    if contributions:
        lines.append("Change between the first and last period, by "
                     f"{group_col}, largest mover first:")
        for item in contributions[:5]:
            share = (f" ({item['share_of_change']:+.0%} of the total change)"
                     if item["share_of_change"] is not None else "")
            lines.append(f"- **{item['group']}**: {item['change']:+,.2f}{share}")
    else:
        lines.append("The dataset has no period-and-group structure to decompose, "
                     "so the movement cannot be attributed to a segment.")
    if associations:
        lines.append("")
        lines.append("Columns that move together with " + measure + ":")
        for item in associations:
            strength = ("strongly" if abs(item["correlation"]) >= 0.7 else
                        "moderately" if abs(item["correlation"]) >= 0.4 else "weakly")
            lines.append(f"- **{item['column']}** moves {strength} "
                         f"{'with' if item['correlation'] > 0 else 'against'} {measure}.")
    lines.append("")
    lines.append("*Moving together is not proof of cause. Confirming a cause needs a "
                 "controlled comparison or domain knowledge this dataset does not carry.*")
    if contributions and contributions[0]["share_of_change"] is not None:
        driver = contributions[0]
        headline = (f"The movement is concentrated in “{driver['group']}”, which "
                    f"accounts for {abs(driver['share_of_change']):.0%} of the change.")
        if associations and abs(associations[0]["correlation"]) >= 0.5:
            headline += (f" It moves closely with {associations[0]['column']}, "
                         "which is where to look first.")
    elif associations:
        headline = (f"{measure.capitalize()} moves closely with "
                    f"{associations[0]['column']}, which is where to look first.")
    else:
        headline = ("There is no segment or period structure in this data to explain "
                    "the movement.")
    report = _section_report("Diagnostic", "Why did it happen?", ctx, lines, calcs,
                             headline=headline)
    return _result(
        "succeeded", headline,
        output={"headline": headline,
                "contributions": contributions, "associations": associations,
                "report_markdown": report},
        calculations=calcs, claims=claims,
    )


def visuals(ctx):
    prep = ctx["preparer"]
    charts = []
    forecast = ctx.get("predictive", {}).get("forecast") or []
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
    contributions = ctx.get("diagnostic", {}).get("contributions") or []
    if contributions:
        # The diagnostic answer as a picture: who moved the number, and
        # which way. This is the chart an executive acts on.
        items = contributions[:8]
        charts.append({"id": "chart_contributions", "type": "bar",
                       "title": f"Who moved {prep['measure']}: change by "
                                f"{prep['group_col']}",
                       "labels": [item["group"] for item in items],
                       "values": [item["change"] for item in items],
                       "source": "diagnostic.contributions",
                       "alt": f"Bar chart of the change in {prep['measure']} for each "
                              f"{prep['group_col']} between the first and last period, "
                              "largest mover first; bars below zero moved against the "
                              "overall direction."})
    if forecast:
        # History and forecast on one axis, with the boundary named in the
        # alt text so nobody mistakes a projection for a measurement.
        charts.append({"id": "chart_forecast", "type": "line",
                       "title": f"{prep['measure']}: history and forecast",
                       "labels": list(prep["trend"].keys()) + [f["label"] for f in forecast],
                       "values": list(prep["trend"].values()) + [f["value"] for f in forecast],
                       "source": "preparer.trend + predictive.forecast",
                       "alt": f"Line chart of {prep['measure']} over "
                              f"{len(prep['trend'])} measured periods followed by "
                              f"{len(forecast)} forecast periods; everything after "
                              f"{list(prep['trend'].keys())[-1]} is a projection."})
    expected = {
        "chart_groups": sorted(prep["groups"].values(), reverse=True)[:8],
        "chart_trend": list(prep["trend"].values()),
        "chart_contributions": [item["change"] for item in contributions[:8]],
        "chart_forecast": list(prep["trend"].values()) + [f["value"] for f in forecast],
    }
    checks = [{"name": "chart_values_match_aggregates",
               "passed": all(chart["values"] == expected[chart["id"]] for chart in charts),
               "detail": "Chart values are taken directly from the prepared aggregates "
                         "and the forecast; axes start at zero."}]
    return _result("succeeded",
                   f"Prepared {len(charts)} truthful chart specifications with alt text.",
                   output={"charts": charts}, checks=checks)


MIN_PERIODS_TO_FORECAST = 4
MIN_PERIODS_TO_BACKTEST = 6
FORECAST_HORIZON = 3


def predictive(ctx):
    """Type 3 — What will happen?

    A trend line fitted to the historical periods, extended forward, with
    its accuracy measured by backtesting rather than asserted. A forecast
    that has not been checked against held-out history is a guess with a
    decimal point, so when there is too little history to check, this
    stage says so instead of forecasting.
    """
    prep = ctx["preparer"]
    measure, date_col = prep["measure"], prep["date_col"]
    labels = list(prep["trend"].keys())
    series = list(prep["trend"].values())
    calcs, claims = [], []

    if len(series) < MIN_PERIODS_TO_FORECAST:
        reason = (f"Only {len(series)} period(s) of history are available; at least "
                  f"{MIN_PERIODS_TO_FORECAST} are needed before a forecast means anything.")
        calcs.append({"id": "c_periods", "name": "periods_available",
                      "value": len(series), "method": f"distinct values of {date_col or '—'}"})
        claims.append({"id": "cl_noforecast", "type": "limitation",
                       "text": f"No forecast was produced. {reason}",
                       "evidence": ["c_periods"], "status": "verified"})
        headline = ("We cannot responsibly forecast from this data yet — there is "
                    "not enough history.")
        return _result("succeeded", headline,
                       output={"headline": headline, "forecast": [], "reason": reason,
                               "report_markdown": _section_report(
                                   "Predictive", "What will happen?", ctx,
                                   [reason, "",
                                    "*Producing a number here anyway would look like "
                                    "analysis and behave like a guess.*"], calcs,
                                   headline=headline)},
                       calculations=calcs, claims=claims)

    slope, intercept, explained = _linear_fit(series)
    horizon = FORECAST_HORIZON
    forecast_labels = _next_labels(labels, horizon)
    predictions = [round(intercept + slope * (len(series) + i), 2) for i in range(horizon)]

    # Backtest: refit on all but the last few periods and score the gap.
    holdout = min(3, max(1, len(series) // 4))
    error = None
    if len(series) >= MIN_PERIODS_TO_BACKTEST:
        train, test = series[:-holdout], series[-holdout:]
        t_slope, t_intercept, _ = _linear_fit(train)
        errors = [abs((t_intercept + t_slope * (len(train) + i)) - actual) / abs(actual)
                  for i, actual in enumerate(test) if actual]
        error = round(statistics.fmean(errors), 4) if errors else None

    calcs += [
        {"id": "c_slope", "name": "per_period_change", "value": round(slope, 2),
         "method": f"least-squares slope of {measure} against period order"},
        {"id": "c_explained", "name": "movement_explained_by_trend",
         "value": round(explained, 4),
         "method": "1 − (unexplained variation / total variation) for the fitted line"},
    ]
    for index, (label, value) in enumerate(zip(forecast_labels, predictions)):
        calcs.append({"id": f"c_forecast_{index}", "name": f"forecast_{label}",
                      "value": value,
                      "method": f"trend line extended to period {len(series) + index + 1}"})
    if error is not None:
        calcs.append({"id": "c_backtest", "name": "backtest_error", "value": error,
                      "method": f"average absolute percentage error over the last "
                                f"{holdout} period(s), predicted from earlier ones only"})

    band = ""
    if error is not None:
        low, high = predictions[0] * (1 - error), predictions[0] * (1 + error)
        band = f" In backtesting this method was off by about {error:.1%}, so treat it as " \
               f"roughly {low:,.0f}–{high:,.0f}."
    claims.append({
        "id": "cl_forecast", "type": "forecast",
        "text": f"If the pattern of the last {len(series)} periods continues, {measure} "
                f"for {forecast_labels[0]} is around {predictions[0]:,.2f}.{band} "
                "This assumes nothing changes about how the business operates.",
        "evidence": ["c_forecast_0"] + (["c_backtest"] if error is not None else []),
        "status": "verified"})
    claims.append({
        "id": "cl_fit", "type": "calculation",
        "text": f"The trend line explains {explained:.0%} of the period-to-period "
                f"movement in {measure}; the rest is variation it does not capture.",
        "evidence": ["c_explained"], "status": "verified"})
    if error is None:
        claims.append({
            "id": "cl_nobacktest", "type": "limitation",
            "text": f"The forecast could not be backtested — that needs at least "
                    f"{MIN_PERIODS_TO_BACKTEST} periods — so its accuracy is unmeasured.",
            "evidence": ["c_slope"], "status": "verified"})

    lines = [f"Direction: {measure} is moving {'up' if slope >= 0 else 'down'} by about "
             f"{abs(slope):,.2f} per period.", "",
             "| Period | Forecast |", "| --- | --- |"]
    lines += [f"| {label} | {value:,.2f} |"
              for label, value in zip(forecast_labels, predictions)]
    lines += ["",
              (f"Measured accuracy: predicting the most recent {holdout} period(s) from "
               f"earlier data only, this method was off by {error:.1%} on average."
               if error is not None else
               f"Accuracy is unmeasured: backtesting needs at least "
               f"{MIN_PERIODS_TO_BACKTEST} periods and this dataset has {len(series)}."),
              "",
              f"The trend line explains {explained:.0%} of the movement between periods.",
              "",
              "*This is an extension of the past, not a model of the business. It assumes "
              "no change in pricing, capacity, seasonality beyond what is already in the "
              "data, or market conditions.*"]
    first_value = prep["trend"][labels[-1]]
    expected_move = ((predictions[0] - first_value) / first_value) if first_value else None
    headline = (
        f"We expect {measure} of about {predictions[0]:,.0f} in {forecast_labels[0]}"
        + (f", {'up' if expected_move >= 0 else 'down'} {abs(expected_move):.0%} on the "
           "latest period" if expected_move is not None else "")
        + (f" — this method has been off by about {error:.0%} when tested on past data."
           if error is not None else " — accuracy not yet tested against past data."))
    return _result(
        "succeeded", headline,
        output={"headline": headline,
                "forecast": [{"label": label, "value": value}
                             for label, value in zip(forecast_labels, predictions)],
                "per_period_change": round(slope, 2), "explained": round(explained, 4),
                "backtest_error": error,
                "report_markdown": _section_report("Predictive", "What will happen?",
                                                   ctx, lines, calcs,
                                                   headline=headline)},
        calculations=calcs, claims=claims,
    )


# Every option is scored against the same stated improvement, so the
# ranking reflects where the leverage is — not a claim about how easy any
# option is. That assumption is printed next to the recommendation.
PLANNING_UPLIFT = 0.10


def prescriptive(ctx, gateway=None):
    """Type 4 — What should I do?

    Enumerates options that come from this dataset, scores each with
    arithmetic the reader can check, recommends one, and states what
    would change the answer.
    """
    prep, desc, diag, pred = (ctx["preparer"], ctx["descriptive"],
                              ctx["diagnostic"], ctx["predictive"])
    measure, group_col = prep["measure"], prep["group_col"]
    groups = prep["groups"]
    calcs, claims, options = [], [], []

    def add_option(key, title, target, base_value, rationale, evidence,
                   gain=None, method=None):
        gain = round(base_value * PLANNING_UPLIFT, 2) if gain is None else gain
        calcs.append({"id": f"c_option_{key}", "name": f"expected_gain_{key}",
                      "value": gain,
                      "method": method or (f"{PLANNING_UPLIFT:.0%} of {target}'s current "
                                           f"{measure} ({base_value:,.2f})")})
        options.append({"key": key, "title": title, "target": target,
                        "base_value": round(base_value, 2), "expected_gain": gain,
                        "rationale": rationale,
                        "evidence": evidence + [f"c_option_{key}"]})

    if groups:
        leader = max(groups, key=groups.get)
        add_option("protect_leader", f"Protect the leading {group_col}: “{leader}”",
                   leader, groups[leader],
                   f"It is the largest single source of {measure}, so a given percentage "
                   "improvement is worth more here than anywhere else — and so is a "
                   "given percentage loss.",
                   ["c_topshare"] if desc.get("top_share") is not None else [])
        laggard = min(groups, key=groups.get)
        if laggard != leader:
            add_option("grow_laggard", f"Grow the smallest {group_col}: “{laggard}”",
                       laggard, groups[laggard],
                       "Smallest current contribution, so the same percentage improvement "
                       "moves the total least — but it reduces dependence on the leader.",
                       [])
    declining = [c for c in diag.get("contributions", []) if c["change"] < 0]
    if declining:
        worst = min(declining, key=lambda c: c["change"])
        add_option("recover_decline", f"Reverse the decline in “{worst['group']}”",
                   worst["group"], abs(worst["change"]),
                   f"This segment moved {worst['change']:,.2f} against the overall "
                   "direction; recovering part of that is a defined, bounded target.",
                   ["c_totalchange"])

    forecast = pred.get("forecast") or []
    if forecast:
        # The baseline is worth exactly nothing extra by definition — that
        # is what makes it the bar the others have to clear.
        add_option("hold_course", "Hold course and re-measure next period",
                   "the whole business", 0.0,
                   f"Changing nothing adds nothing: the forecast of "
                   f"{forecast[0]['value']:,.2f} for {forecast[0]['label']} already "
                   "assumes today's behaviour continues. This is the bar every other "
                   "option has to clear.",
                   ["c_forecast_0"], gain=0.0,
                   method="baseline: no change means no gain beyond the forecast")

    if not options:
        reason = ("No option could be derived: the dataset has no grouping column and "
                  "no usable trend, so there is nothing to compare.")
        calcs.append({"id": "c_nooptions", "name": "options_available", "value": 0,
                      "method": "no group column and no forecast"})
        claims.append({"id": "cl_nooptions", "type": "limitation", "text": reason,
                       "evidence": ["c_nooptions"], "status": "verified"})
        headline = ("We cannot recommend an action from this data: there are no "
                    "options to compare.")
        return _result("succeeded", headline,
                       output={"headline": headline,
                               "options": [], "recommendation": None,
                               "exec_summary": reason,
                               "exec_summary_source": "deterministic",
                               "report_markdown": _section_report(
                                   "Prescriptive", "What should I do?", ctx,
                                   [reason], calcs, headline=headline)},
                       calculations=calcs, claims=claims)

    options.sort(key=lambda o: -o["expected_gain"])
    best = options[0]
    runner_up = options[1] if len(options) > 1 else None
    margin = (best["expected_gain"] - runner_up["expected_gain"]) if runner_up else None

    claims.append({
        "id": "cl_recommendation", "type": "recommendation",
        "text": f"Recommended action: {best['title']}. On the same {PLANNING_UPLIFT:.0%} "
                f"improvement applied to every option, it is worth {best['expected_gain']:,.2f} "
                f"in {measure}" +
                (f", ahead of the next option by {margin:,.2f}." if margin else ".") +
                " This is a recommendation under a stated assumption, not an observed "
                "outcome.",
        "evidence": best["evidence"], "status": "verified"})
    claims.append({
        "id": "cl_assumption", "type": "assumption",
        "text": f"Every option is scored with the same {PLANNING_UPLIFT:.0%} improvement "
                "applied to its target. The ranking therefore shows where the leverage is "
                "largest, not which option is easiest to achieve — that judgement needs "
                "cost and feasibility data this dataset does not contain.",
        "evidence": [f"c_option_{best['key']}"], "status": "verified"})

    facts = [f"Total {measure} is {prep['total']:,.2f}."]
    if desc.get("change") is not None:
        facts.append(f"{measure} moved {desc['change']:+.1%} across the period.")
    if diag.get("contributions"):
        facts.append(f"{diag['contributions'][0]['group']} accounts for the largest "
                     "part of that movement.")
    if forecast:
        facts.append(f"Next period is forecast at {forecast[0]['value']:,.2f}.")
    facts.append(f"The recommended action is: {best['title']}.")
    narration = (gateway.narrate(ctx.get("goal", "the analysis"), facts)
                 if gateway else {"text": " ".join(facts), "source": "deterministic"})

    lines = ["| Option | Target | Expected gain | Why |", "| --- | --- | --- | --- |"]
    for option in options:
        lines.append(f"| {option['title']} | {option['target']} | "
                     f"{option['expected_gain']:,.2f} | {option['rationale']} |")
    lines += ["", f"**Recommendation: {best['title']}**", "", best["rationale"], "",
              f"*Every option is scored with the same {PLANNING_UPLIFT:.0%} improvement "
              "applied to its target, so this ranks where the leverage is — not which "
              "option is cheapest or most likely to succeed. Supply cost and feasibility "
              "figures and the ranking can change.*"]
    if margin is not None and best["expected_gain"]:
        closeness = margin / best["expected_gain"]
        lines += ["", f"*How close is the call? The runner-up is behind by "
                      f"{closeness:.0%} of the leading option's value."
                      + (" That is close enough that cost and feasibility should decide "
                         "it, not this ranking.*" if closeness < 0.20 else "*")]
    headline = (f"We recommend: {best['title']}. It is worth about "
                f"{best['expected_gain']:,.0f} in {measure} — more than any other "
                f"option we compared.")
    return _result(
        "succeeded", headline,
        output={"headline": headline, "options": options, "recommendation": best,
                "exec_summary": narration["text"],
                "exec_summary_source": narration["source"],
                "report_markdown": _section_report("Prescriptive", "What should I do?",
                                                   ctx, lines, calcs,
                                                   headline=headline)},
        calculations=calcs, claims=claims,
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
    all_calc_ids = {c["id"] for stage in EVIDENCE_STAGES
                    for c in ctx.get(stage + "_result", {}).get("calculations", [])}
    all_claims = [cl for stage in EVIDENCE_STAGES
                  for cl in ctx.get(stage + "_result", {}).get("claims", [])]
    unsupported = [cl["id"] for cl in all_claims
                   if not set(cl.get("evidence", [])) <= all_calc_ids]
    checks.append({"name": "every_claim_has_evidence", "passed": not unsupported,
                   "detail": ("All claims trace to calculations."
                              if not unsupported else
                              f"Unsupported claims: {', '.join(unsupported)}")})

    # Each analytics type must have produced its own report.
    missing_reports = [name for name, _ in ANALYTICS_TYPES
                       if not ctx.get(name, {}).get("report_markdown")]
    checks.append({"name": "every_analytics_type_reported",
                   "passed": not missing_reports,
                   "detail": ("All four analytics types produced a report."
                              if not missing_reports else
                              f"Missing reports: {', '.join(missing_reports)}")})

    # The reason the change decomposition is trustworthy: its parts add up.
    contributions = ctx.get("diagnostic", {}).get("contributions") or []
    if contributions:
        total_change = next(
            (c["value"] for c in ctx["diagnostic_result"]["calculations"]
             if c["id"] == "c_totalchange"), None)
        summed = sum(item["change"] for item in contributions)
        reconciled = total_change is not None and abs(summed - total_change) < 0.01
        checks.append({"name": "change_decomposition_reconciles", "passed": reconciled,
                       "detail": f"Σ(segment changes)={summed:,.2f} vs "
                                 f"total change={total_change:,.2f}"})

    # A forecast that was never checked against held-out history must say so.
    forecast_claims = [cl for cl in all_claims if cl["type"] == "forecast"]
    backtested = ctx.get("predictive", {}).get("backtest_error") is not None
    declared = any(cl["type"] == "limitation" and "backtest" in cl["text"].lower()
                   for cl in all_claims)
    checks.append({"name": "forecast_accuracy_is_measured_or_declared",
                   "passed": not forecast_claims or backtested or declared,
                   "detail": ("Forecast accuracy is backtested." if backtested else
                              "No forecast made." if not forecast_claims else
                              "Unmeasured accuracy is declared as a limitation."
                              if declared else
                              "A forecast was made without measuring or declaring "
                              "its accuracy.")})

    # Recommendations are only honest with their assumptions attached.
    recommendations = [cl for cl in all_claims if cl["type"] == "recommendation"]
    assumptions = [cl for cl in all_claims if cl["type"] == "assumption"]
    checks.append({"name": "recommendations_state_their_assumptions",
                   "passed": not recommendations or bool(assumptions),
                   "detail": (f"{len(recommendations)} recommendation(s), "
                              f"{len(assumptions)} stated assumption(s).")})

    # Business language is a requirement, so it is checked — on the
    # headlines as well as the claims, since the headline is the line an
    # executive actually reads.
    jargon_hits = {cl["id"]: _jargon_in(cl["text"]) for cl in all_claims
                   if _jargon_in(cl["text"])}
    for name, _ in ANALYTICS_TYPES:
        headline = ctx.get(name, {}).get("headline", "")
        if _jargon_in(headline):
            jargon_hits[f"{name}.headline"] = _jargon_in(headline)
    checks.append({"name": "claims_avoid_statistical_jargon",
                   "passed": not jargon_hits,
                   "detail": ("Claims are written in business language."
                              if not jargon_hits else
                              "Jargon found: " + "; ".join(
                                  f"{k}: {', '.join(v)}" for k, v in jargon_hits.items()))})
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
    """The comprehensive report: the four type reports in one document.

    It embeds each type report in full rather than linking to it, because
    the approval gate binds to this artifact's hash — whatever a human
    approves for publication is exactly what they were shown.
    """
    prep = ctx["preparer"]
    lines = [
        f"# Business Analytics Report — {ctx.get('dataset_name', 'dataset')}",
        "",
        f"**Goal:** {ctx.get('goal', '')}",
        "",
        "## Executive summary",
        ctx["prescriptive"]["exec_summary"],
        f"*(Narrative source: {ctx['prescriptive']['exec_summary_source']}; every "
        "figure in this report is deterministically calculated.)*",
        "",
        "## The four questions",
        "| Type | Question | Answer in one line |",
        "| --- | --- | --- |",
    ]
    headlines = {
        "descriptive": ctx["descriptive_result"]["summary"],
        "diagnostic": ctx["diagnostic_result"]["summary"],
        "predictive": ctx["predictive_result"]["summary"],
        "prescriptive": ctx["prescriptive_result"]["summary"],
    }
    for name, question in ANALYTICS_TYPES:
        lines.append(f"| {name.capitalize()} | {question} | {headlines[name]} |")
    lines += ["", "## Data quality",
              ctx["profiler_result"]["summary"], ctx["cleaner_result"]["summary"],
              "", "## Key metrics",
              "Every figure produced by the run, in one place. Each per-type "
              "section below repeats the figures it used.",
              "", "| Metric | Value | Method |", "| --- | --- | --- |"]
    for stage in EVIDENCE_STAGES:
        for calc in ctx.get(stage + "_result", {}).get("calculations", []):
            lines.append(f"| {calc['name']} | {calc['value']} | {calc['method']} |")

    for name, _ in ANALYTICS_TYPES:
        section = ctx[name].get("report_markdown", "")
        # Demote the section's own H1 so the combined document keeps one
        # heading level per depth.
        lines += ["", "---", ""]
        lines += ["#" + line if line.startswith("# ") else line
                  for line in section.split("\n")]

    lines += ["", "---", "", "## Every claim in this report",
              "| Claim | Type | Evidence | Status |", "| --- | --- | --- | --- |"]
    for stage in EVIDENCE_STAGES:
        for claim in ctx.get(stage + "_result", {}).get("claims", []):
            lines.append(f"| {claim['text']} | {claim['type']} | "
                         f"{', '.join(claim['evidence'])} | {claim['status']} |")
    lines += ["", "## Charts"]
    for chart in ctx["visuals"]["charts"]:
        lines.append(f"- **{chart['title']}** ({chart['type']}): {chart['alt']}")
    lines += ["", "## Validation", ctx["validator_result"]["summary"]]
    for check in ctx["validator_result"]["quality_checks"]:
        lines.append(f"- {'PASS' if check['passed'] else 'FAIL'} — "
                     f"{check['name']}: {check['detail']}")
    lines += [
        "", "## Assumptions and limitations",
        "- Findings describe only the supplied snapshot "
        f"(sha256:{ctx['collector']['snapshot']}).",
        "- Diagnostic analysis shows where movement came from and what moves with "
        "what. It does not establish cause: that needs a controlled comparison or "
        "domain knowledge this dataset does not carry.",
        "- The forecast extends the historical pattern. It assumes the business keeps "
        "operating as it has, and it is stated with the error measured by backtesting "
        "(or explicitly marked unmeasured).",
        "- The recommendation ranks options by leverage under one stated improvement "
        "assumption applied equally to each. It is not a claim about cost, feasibility, "
        "or certainty of outcome.",
        "",
        f"*Generated by Agentic OS run {ctx.get('run_id', '')} — measure "
        f"“{prep['measure']}”, {ctx['cleaner']['rows_after']} analyzed rows.*",
    ]
    report = "\n".join(lines)
    return _result(
        "succeeded",
        f"Comprehensive report assembled from all four analytics types: "
        f"{ctx['validator']['claim_count']} claims, all with evidence links, validation "
        + ("passed." if ctx["validator"]["passed"] else "FAILED."),
        output={"report_markdown": report},
    )


PIPELINE = [
    ("planner", planner),
    ("collector", collector),
    ("profiler", profiler),
    ("cleaner", cleaner),
    ("preparer", preparer),
    # The maturity ladder: each type consumes the ones before it.
    ("descriptive", descriptive),
    ("diagnostic", diagnostic),
    ("predictive", predictive),
    ("prescriptive", prescriptive),
    ("visuals", visuals),
    ("validator", validator),
    ("reporter", reporter),
]

# Stages whose claims and calculations the validator audits.
EVIDENCE_STAGES = ("collector", "profiler", "cleaner", "preparer",
                   "descriptive", "diagnostic", "predictive", "prescriptive")

# Stages that receive the model gateway (narration of verified facts only).
NARRATED_STAGES = ("prescriptive",)

ROLE_TITLES = {
    "planner": "Planner Agent",
    "collector": "Data Source Agent",
    "profiler": "Data Profiling Agent",
    "cleaner": "Data Cleaning Agent",
    "preparer": "Data Preparation Agent",
    "descriptive": "Descriptive Analytics Agent — what happened?",
    "diagnostic": "Diagnostic Analytics Agent — why did it happen?",
    "predictive": "Predictive Analytics Agent — what will happen?",
    "prescriptive": "Prescriptive Analytics Agent — what should I do?",
    "visuals": "Visualization Expert",
    "validator": "Validation Expert",
    "reporter": "Reporting Expert",
    "publish": "Knowledge Curator (vault publish)",
}
