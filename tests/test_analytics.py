"""The four business-analytics agents.

Each type answers one question, and each is tested against figures
computed independently here rather than against whatever the pipeline
happens to produce. The honest-refusal paths matter as much as the happy
path: a forecast from three data points, or a recommendation with no
options to compare, must decline rather than invent.
"""

import statistics
import unittest

from server import analytics


def run_pipeline(dataset_text, goal="Analyze the data", name="test.csv", gateway=None):
    ctx = {"goal": goal, "dataset_name": name, "dataset_text": dataset_text,
           "run_id": "test-run"}
    results = {}
    for role, stage in analytics.PIPELINE:
        result = (stage(ctx, gateway=gateway)
                  if role in analytics.NARRATED_STAGES else stage(ctx))
        results[role] = result
        if result["status"] == "failed":
            return ctx, results
        ctx[role] = result["output"]
        ctx[role + "_result"] = result
    return ctx, results


# A dataset with arithmetic that is easy to verify by hand: two teams,
# six months, a straight line up for one and flat for the other.
def linear_dataset():
    lines = ["month,team,sales"]
    for index in range(6):
        month = f"2025-{index + 1:02d}"
        lines.append(f"{month},Alpha,{100 + 10 * index}")
        lines.append(f"{month},Beta,50")
    return "\n".join(lines) + "\n"


class FourAnalyticsTypesTestCase(unittest.TestCase):
    def test_every_type_runs_and_produces_its_own_report(self):
        ctx, results = run_pipeline(analytics.sample_dataset())
        for name, question in analytics.ANALYTICS_TYPES:
            self.assertEqual(results[name]["status"], "succeeded", name)
            report = ctx[name]["report_markdown"]
            self.assertIn(question, report, name)
            # Each report stands alone: it names its dataset and shows its
            # own arithmetic.
            self.assertIn("How each figure was calculated", report)

    def test_the_comprehensive_report_contains_all_four(self):
        ctx, results = run_pipeline(analytics.sample_dataset())
        combined = results["reporter"]["output"]["report_markdown"]
        for name, question in analytics.ANALYTICS_TYPES:
            self.assertIn(question, combined, name)
        # It embeds rather than links: what a human approves is what gets
        # published, so the hash has to cover the whole thing. Only the
        # section's own H1 is demoted; every other line appears verbatim.
        for name, _ in analytics.ANALYTICS_TYPES:
            body = "\n".join(ctx[name]["report_markdown"].split("\n")[1:])
            self.assertIn(body, combined, f"{name} section is not embedded in full")

    # -- descriptive ------------------------------------------------------
    def test_descriptive_figures_match_an_independent_calculation(self):
        ctx, _ = run_pipeline(linear_dataset())
        values = [100 + 10 * i for i in range(6)] + [50] * 6
        self.assertAlmostEqual(ctx["preparer"]["total"], sum(values), places=2)
        self.assertAlmostEqual(ctx["descriptive"]["mean"],
                               round(statistics.fmean(values), 2), places=2)
        # Alpha 100->150, Beta 50->50: total 150 -> 200, a third up.
        self.assertAlmostEqual(ctx["descriptive"]["change"], 1 / 3, places=4)
        self.assertEqual(ctx["descriptive"]["top_group"], "Alpha")

    def test_descriptive_claims_are_written_in_business_language(self):
        _, results = run_pipeline(analytics.sample_dataset())
        for name, _ in analytics.ANALYTICS_TYPES:
            for claim in results[name]["claims"]:
                self.assertEqual(analytics._jargon_in(claim["text"]), [],
                                 f"{name}: {claim['text']}")

    # -- diagnostic -------------------------------------------------------
    def test_diagnostic_decomposition_adds_up_to_the_total_change(self):
        ctx, _ = run_pipeline(linear_dataset())
        contributions = ctx["diagnostic"]["contributions"]
        self.assertEqual({c["group"] for c in contributions}, {"Alpha", "Beta"})
        alpha = next(c for c in contributions if c["group"] == "Alpha")
        self.assertAlmostEqual(alpha["change"], 50.0, places=2)   # 100 -> 150
        beta = next(c for c in contributions if c["group"] == "Beta")
        self.assertAlmostEqual(beta["change"], 0.0, places=2)     # flat
        self.assertAlmostEqual(sum(c["change"] for c in contributions), 50.0, places=2)
        self.assertAlmostEqual(alpha["share_of_change"], 1.0, places=4)

    def test_diagnostic_states_association_without_asserting_cause(self):
        ctx, results = run_pipeline(analytics.sample_dataset())
        claims = results["diagnostic"]["claims"]
        self.assertTrue(claims, "the sample dataset has structure to diagnose")
        for claim in claims:
            text = claim["text"].lower()
            if "caus" in text:
                # Any sentence that reaches for cause must disown it in the
                # same breath, not three paragraphs later.
                self.assertRegex(text, r"not (what caused|proof)")
        self.assertIn("not proof", ctx["diagnostic"]["report_markdown"].lower())
        self.assertIn("controlled comparison",
                      ctx["diagnostic"]["report_markdown"].lower())

    # -- predictive -------------------------------------------------------
    def test_the_forecast_extends_a_straight_line_exactly(self):
        """Alpha+Beta per month is 150,160,...,200 — a line of slope 10."""
        ctx, _ = run_pipeline(linear_dataset())
        self.assertAlmostEqual(ctx["predictive"]["per_period_change"], 10.0, places=2)
        forecast = ctx["predictive"]["forecast"]
        self.assertEqual([f["label"] for f in forecast],
                         ["2025-07", "2025-08", "2025-09"])
        self.assertAlmostEqual(forecast[0]["value"], 210.0, places=2)
        self.assertAlmostEqual(forecast[2]["value"], 230.0, places=2)
        # A perfect line is perfectly explained, and backtests to no error.
        self.assertAlmostEqual(ctx["predictive"]["explained"], 1.0, places=4)
        self.assertAlmostEqual(ctx["predictive"]["backtest_error"], 0.0, places=6)

    def test_too_little_history_declines_to_forecast(self):
        data = "month,team,sales\n2025-01,A,10\n2025-02,A,20\n2025-03,A,30\n"
        ctx, results = run_pipeline(data)
        self.assertEqual(results["predictive"]["status"], "succeeded")
        self.assertEqual(ctx["predictive"]["forecast"], [])
        self.assertIn("not enough history", results["predictive"]["summary"].lower())
        types = {c["type"] for c in results["predictive"]["claims"]}
        self.assertEqual(types, {"limitation"})

    def test_a_forecast_without_a_backtest_declares_that(self):
        rows = "\n".join(f"2025-{m:02d},A,{100 + m}" for m in range(1, 6))
        ctx, results = run_pipeline("month,team,sales\n" + rows + "\n")
        self.assertTrue(ctx["predictive"]["forecast"])
        self.assertIsNone(ctx["predictive"]["backtest_error"])
        self.assertTrue(any(c["type"] == "limitation"
                            for c in results["predictive"]["claims"]))
        self.assertIn("unmeasured", ctx["predictive"]["report_markdown"].lower())
        # The validator accepts it only because the gap is declared.
        self.assertTrue(ctx["validator"]["passed"])

    # -- prescriptive -----------------------------------------------------
    def test_options_are_ranked_by_arithmetic_the_reader_can_check(self):
        ctx, _ = run_pipeline(linear_dataset())
        options = ctx["prescriptive"]["options"]
        by_key = {o["key"]: o for o in options}
        # Alpha totals 750, Beta 300; 10% of each is the expected gain.
        self.assertAlmostEqual(by_key["protect_leader"]["expected_gain"], 75.0, places=2)
        self.assertAlmostEqual(by_key["grow_laggard"]["expected_gain"], 30.0, places=2)
        # Doing nothing is worth nothing extra — that is what makes it the bar.
        self.assertAlmostEqual(by_key["hold_course"]["expected_gain"], 0.0, places=2)
        self.assertEqual(ctx["prescriptive"]["recommendation"]["key"], "protect_leader")
        self.assertEqual([o["expected_gain"] for o in options],
                         sorted((o["expected_gain"] for o in options), reverse=True))

    def test_a_recommendation_always_carries_its_assumption(self):
        _, results = run_pipeline(analytics.sample_dataset())
        claims = results["prescriptive"]["claims"]
        self.assertTrue(any(c["type"] == "recommendation" for c in claims))
        assumption = next(c for c in claims if c["type"] == "assumption")
        self.assertIn("10%", assumption["text"])
        self.assertIn("not which option is easiest", assumption["text"])

    def test_nothing_to_compare_means_no_recommendation(self):
        # One column of numbers: no segments, no periods, no options.
        ctx, results = run_pipeline("sales\n10\n20\n30\n40\n")
        self.assertEqual(results["prescriptive"]["status"], "succeeded")
        self.assertEqual(ctx["prescriptive"]["options"], [])
        self.assertIsNone(ctx["prescriptive"]["recommendation"])
        self.assertTrue(any(c["type"] == "limitation"
                            for c in results["prescriptive"]["claims"]))

    # -- validation of the whole ladder -----------------------------------
    def test_the_validator_enforces_the_new_guarantees(self):
        ctx, _ = run_pipeline(analytics.sample_dataset())
        names = {c["name"]: c for c in ctx["validator_result"]["quality_checks"]}
        for required in ("every_analytics_type_reported",
                         "change_decomposition_reconciles",
                         "forecast_accuracy_is_measured_or_declared",
                         "recommendations_state_their_assumptions",
                         "claims_avoid_statistical_jargon"):
            self.assertIn(required, names)
            self.assertTrue(names[required]["passed"], required)
        self.assertTrue(ctx["validator"]["passed"])

    def test_the_jargon_check_actually_fires(self):
        """Guard against a check that can only ever pass."""
        self.assertEqual(analytics._jargon_in("Costs are rising significantly."), [])
        self.assertEqual(
            analytics._jargon_in("The coefficient of determination (R²) is 0.87."),
            ["r²", "coefficient of determination"])
        self.assertEqual(
            analytics._jargon_in("There is a statistically significant result (p < 0.05)."),
            ["p <", "statistically significant"])

    # -- business language ------------------------------------------------
    def test_every_type_leads_with_a_headline_a_board_can_read(self):
        """The brief's core skill: findings translated into business
        language. Each type answers its question in one plain sentence,
        and that sentence is the stage's summary and the top of its
        report — not a footnote."""
        ctx, results = run_pipeline(analytics.sample_dataset())
        for name, _ in analytics.ANALYTICS_TYPES:
            headline = ctx[name]["headline"]
            self.assertEqual(analytics._jargon_in(headline), [], name)
            self.assertEqual(results[name]["summary"], headline, name)
            self.assertIn(headline, ctx[name]["report_markdown"], name)
        # And each reads as its own question's answer.
        self.assertRegex(ctx["descriptive"]["headline"], r"(up|down|totals)")
        self.assertIn("accounts for", ctx["diagnostic"]["headline"])
        self.assertTrue(ctx["predictive"]["headline"].startswith("We expect"))
        self.assertTrue(ctx["prescriptive"]["headline"].startswith("We recommend"))

    def test_headlines_are_checked_for_jargon_too(self):
        """The check must cover the line executives read, not only claims."""
        ctx, _ = run_pipeline(analytics.sample_dataset())
        ctx["descriptive"]["headline"] = "The mean has increased by 2.3 standard deviations."
        recheck = analytics.validator(ctx)
        check = next(c for c in recheck["quality_checks"]
                     if c["name"] == "claims_avoid_statistical_jargon")
        self.assertFalse(check["passed"])
        self.assertIn("descriptive.headline", check["detail"])

    def test_the_diagnostic_answer_is_also_a_chart(self):
        """A finding that cannot be communicated cannot drive action."""
        ctx, _ = run_pipeline(analytics.sample_dataset())
        chart = next(c for c in ctx["visuals"]["charts"]
                     if c["id"] == "chart_contributions")
        self.assertEqual(chart["values"],
                         [item["change"] for item in ctx["diagnostic"]["contributions"]])
        self.assertIn("moved against the overall direction", chart["alt"])

    def test_the_forecast_chart_is_labelled_as_a_projection(self):
        ctx, _ = run_pipeline(analytics.sample_dataset())
        chart = next(c for c in ctx["visuals"]["charts"] if c["id"] == "chart_forecast")
        self.assertIn("projection", chart["alt"])
        measured = len(ctx["preparer"]["trend"])
        self.assertEqual(len(chart["values"]),
                         measured + len(ctx["predictive"]["forecast"]))


if __name__ == "__main__":
    unittest.main()
