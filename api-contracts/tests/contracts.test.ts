/**
 * Parses real API responses (captured by the backend test
 * `tests/test_api_contract_samples.py`) with the generated schemas.
 * A failure means a schema no longer matches what the API returns.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { endpoints } from "../src/index";

type Sample = { method: string; path: string; status: number; body: unknown };

const { samples } = JSON.parse(
  readFileSync(new URL("./samples.json", import.meta.url), "utf8"),
) as { samples: Sample[] };

const byRoute = new Map(
  Object.entries(endpoints).map(([name, endpoint]) => [`${endpoint.method} ${endpoint.path}`, { name, endpoint }]),
);

test("samples were captured", () => {
  assert.ok(samples.length > 50, "run the backend capture first (see README)");
});

for (const sample of samples) {
  test(`${sample.method} ${sample.path}`, () => {
    const route = byRoute.get(`${sample.method} ${sample.path}`);
    assert.ok(route, "no endpoint in the contracts for this route");
    const schema = route.endpoint.response;
    assert.ok(schema, `${route.name} declares no response schema`);
    const result = schema.safeParse(sample.body);
    assert.ok(result.success, result.success ? "" : JSON.stringify(result.error.issues, null, 1));
  });
}
