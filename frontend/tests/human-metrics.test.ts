import assert from "node:assert/strict";
import test from "node:test";

import { accuracyQualityLabel, formatAccuracy, formatPercentagePointChange, formatWinPercent } from "../src/lib/human-metrics.ts";

test("human metric formatters are null safe and presentation only", () => {
  assert.equal(formatAccuracy(91.4), "91%");
  assert.equal(formatAccuracy(null), "—");
  assert.equal(formatWinPercent(52.6), "53%");
  assert.equal(formatWinPercent(Number.NaN), "—");
  assert.equal(accuracyQualityLabel("excellent"), "Отличная");
  assert.equal(accuracyQualityLabel(null), null);
  assert.equal(formatPercentagePointChange(6), "+6 п.п.");
  assert.equal(formatPercentagePointChange(-2.35), "−2,4 п.п.");
  assert.equal(formatPercentagePointChange(null), null);
});
