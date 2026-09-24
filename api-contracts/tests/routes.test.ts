/**
 * Checks the operations of the contracts against the OpenAPI schema of the
 * backend (`tests/openapi.json`, see the README): same routes, same headers,
 * same success status. A failure means the contracts drifted from the API.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { endpoints } from "../src/index";

type Parameter = { in: string; name: string; required?: boolean; schema?: { enum?: string[] } };
type Schema = { $ref?: string; properties?: Record<string, { readOnly?: boolean; writeOnly?: boolean }> };
type Operation = {
  parameters?: Parameter[];
  requestBody?: { content: Record<string, { schema: Schema }> };
  responses: Record<string, { content?: Record<string, { schema: Schema }> }>;
};

const openapi = JSON.parse(readFileSync(new URL("./openapi.json", import.meta.url), "utf8")) as {
  paths: Record<string, Record<string, Operation>>;
  components: { schemas: Record<string, Schema> };
};

/** The property names of an object schema of the OpenAPI document, `$ref`s resolved. */
function fields(schema: Schema | undefined, side: "request" | "response"): string[] | null {
  const resolved = schema?.$ref ? openapi.components.schemas[schema.$ref.split("/").pop()!] : schema;
  if (!resolved?.properties) return null;
  const hidden = side === "request" ? "readOnly" : "writeOnly";
  return Object.entries(resolved.properties)
    .filter(([, property]) => !property[hidden])
    .map(([name]) => name)
    .sort();
}

/** The keys of a Zod object schema, or null when it is not one (a list, a page…). */
function shapeKeys(schema: unknown): string[] | null {
  const shape = (schema as { shape?: Record<string, unknown> } | undefined)?.shape;
  return shape ? Object.keys(shape).sort() : null;
}

const METHODS = ["get", "post", "put", "patch", "delete"];
const operations = new Map<string, Operation>();
for (const [path, item] of Object.entries(openapi.paths)) {
  for (const method of METHODS) {
    if (item[method]) operations.set(`${method.toUpperCase()} ${path}`, item[method]);
  }
}
const contracts = new Map(Object.values(endpoints).map((e) => [`${e.method} ${e.path}`, e]));

test("every operation of the API has a contract, and the other way round", () => {
  assert.deepEqual([...contracts.keys()].sort(), [...operations.keys()].sort());
});

for (const [route, operation] of operations) {
  test(`${route}: headers and status`, () => {
    const endpoint = contracts.get(route);
    assert.ok(endpoint, "no contract for this route");
    const required = (operation.parameters ?? []).filter((p) => p.in === "header" && p.required);
    const step = required.find((p) => p.name === "X-UI-Config-Step")?.schema?.enum?.[0] ?? null;
    const ids = required.filter((p) => p.name !== "X-UI-Config-Step").map((p) => p.name);
    const expectedStep = step ?? (ids.length === 2 ? "dashboard" : null);
    assert.equal(endpoint.uiConfigStep, expectedStep);
    assert.deepEqual([...endpoint.requiredHeaders].sort(), [...ids].sort());
    assert.ok(String(endpoint.status) in operation.responses, `status ${endpoint.status} is not documented`);
  });
}

for (const [route, operation] of operations) {
  test(`${route}: body and response fields`, () => {
    const endpoint = contracts.get(route) as { body?: unknown; response?: unknown; status: number };
    const body = operation.requestBody?.content["application/json"]?.schema;
    if (body && endpoint.body) {
      const expected = fields(body, "request");
      if (expected) assert.deepEqual(shapeKeys(endpoint.body), expected, "request body fields");
    }
    const answer = operation.responses[String(endpoint.status)]?.content?.["application/json"]?.schema;
    if (answer && endpoint.response) {
      const expected = fields(answer, "response");
      if (expected) assert.deepEqual(shapeKeys(endpoint.response), expected, "response fields");
    }
  });
}
