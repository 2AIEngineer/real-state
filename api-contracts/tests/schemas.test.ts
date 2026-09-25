/**
 * Deep comparison of every contract with the OpenAPI schema of the backend
 * (`tests/openapi.json`): for each operation, the path and query parameters,
 * the request body and the success response are compared field by field —
 * names, required or optional, nullable, type, enum values, nested objects and
 * lists. `routes.test.ts` checks the routes themselves; this file checks that
 * nothing inside them is ambiguous or out of date.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { z } from "zod";

import { endpoints } from "../src/index";

type Json = Record<string, any>;

const openapi = JSON.parse(readFileSync(new URL("./openapi.json", import.meta.url), "utf8")) as Json;
const components: Record<string, Json> = openapi.components.schemas;

/** A shape both sides are reduced to before being compared. */
type Shape =
  | { kind: "object"; nullable: boolean; props: Record<string, { shape: Shape; required: boolean }> }
  | { kind: "map"; nullable: boolean }
  | { kind: "array"; nullable: boolean; items: Shape }
  | { kind: "enum"; nullable: boolean; values: string[] }
  | { kind: "scalar"; nullable: boolean; type: string }
  | { kind: "file"; nullable: boolean }
  | { kind: "any"; nullable: boolean };

// ------------------------------------------------------------------ OpenAPI side

function resolve(schema: Json): Json {
  let current = schema;
  while (current?.$ref) current = components[current.$ref.split("/").pop()!];
  return current ?? {};
}

function fromOpenApi(raw: Json, side: "request" | "response"): Shape {
  let nullable = Boolean(raw.nullable);
  let schema = raw;
  if (schema.allOf?.length === 1) schema = { ...resolve(schema.allOf[0]), nullable: nullable || schema.nullable };
  const variants: Json[] | undefined = schema.oneOf ?? schema.anyOf;
  if (variants) {
    const resolved = variants.map(resolve);
    const nullEnum = resolved.filter((v) => v.enum?.length === 1 && v.enum[0] === null);
    const blankEnum = resolved.filter((v) => v.enum?.length === 1 && v.enum[0] === "");
    const rest = resolved.filter((v) => !nullEnum.includes(v) && !blankEnum.includes(v));
    if (nullEnum.length) nullable = true;
    if (rest.length === 1) {
      const inner = fromOpenApi(rest[0], side);
      if (inner.kind === "enum" && blankEnum.length) inner.values = [...inner.values, ""].sort();
      return { ...inner, nullable: nullable || inner.nullable } as Shape;
    }
    // "an e-mail or an empty string" (drf-spectacular: a blank-allowed string field).
    if (rest.length && rest.every((v) => v.type === "string" && !v.enum)) {
      return { kind: "scalar", nullable, type: "string" };
    }
    return { kind: "any", nullable };
  }
  schema = { ...resolve(schema), nullable: nullable || resolve(schema).nullable };
  nullable = Boolean(schema.nullable);
  if (schema.enum) {
    return { kind: "enum", nullable, values: schema.enum.filter((v: unknown) => v !== null).map(String).sort() };
  }
  if (schema.type === "array") return { kind: "array", nullable, items: fromOpenApi(schema.items ?? {}, side) };
  if (schema.type === "object" || schema.properties) {
    if (!schema.properties) return { kind: "map", nullable };
    const hidden = side === "request" ? "readOnly" : "writeOnly";
    const required = new Set<string>(schema.required ?? []);
    const props: Record<string, { shape: Shape; required: boolean }> = {};
    for (const [name, value] of Object.entries<Json>(schema.properties)) {
      if (value[hidden]) continue;
      props[name] = { shape: fromOpenApi(value, side), required: required.has(name) };
    }
    return { kind: "object", nullable, props };
  }
  if (schema.format === "binary") return { kind: "file", nullable };
  if (["string", "integer", "number", "boolean"].includes(schema.type)) {
    return { kind: "scalar", nullable, type: schema.type };
  }
  return { kind: "any", nullable };
}

// ---------------------------------------------------------------------- Zod side

function fromJsonSchema(schema: Json, defs: Json): Shape {
  if (schema.$ref) return fromJsonSchema(defs[schema.$ref.split("/").pop()!], defs);
  const variants: Json[] | undefined = schema.anyOf ?? schema.oneOf;
  if (variants) {
    const nonNull = variants.filter((v) => v.type !== "null");
    const nullable = nonNull.length < variants.length;
    if (nonNull.length === 1) {
      const inner = fromJsonSchema(nonNull[0], defs);
      return { ...inner, nullable: nullable || inner.nullable } as Shape;
    }
    if (nonNull.every((v) => v.const !== undefined || v.enum)) {
      const values = nonNull.flatMap((v) => (v.enum ?? [v.const]).map(String)).sort();
      return { kind: "enum", nullable, values };
    }
    // "an e-mail or an empty string": a string, as the API describes it.
    if (nonNull.every((v) => v.type === "string" || typeof v.const === "string")) {
      return { kind: "scalar", nullable, type: "string" };
    }
    return { kind: "any", nullable };
  }
  const types: string[] = Array.isArray(schema.type) ? schema.type : schema.type ? [schema.type] : [];
  const nullable = types.includes("null");
  const type = types.find((t) => t !== "null");
  if (schema.enum || schema.const !== undefined) {
    const values = (schema.enum ?? [schema.const]).filter((v: unknown) => v !== null).map(String).sort();
    return { kind: "enum", nullable, values };
  }
  if (type === "array") return { kind: "array", nullable, items: fromJsonSchema(schema.items ?? {}, defs) };
  if (type === "object") {
    if (!schema.properties) return { kind: "map", nullable };
    const required = new Set<string>(schema.required ?? []);
    const props: Record<string, { shape: Shape; required: boolean }> = {};
    for (const [name, value] of Object.entries<Json>(schema.properties)) {
      props[name] = { shape: fromJsonSchema(value, defs), required: required.has(name) };
    }
    return { kind: "object", nullable, props };
  }
  if (type && ["string", "integer", "number", "boolean"].includes(type)) return { kind: "scalar", nullable, type };
  return { kind: "any", nullable };
}

function fromZod(schema: z.ZodType, io: "input" | "output"): Shape {
  const json = z.toJSONSchema(schema, { io, unrepresentable: "any", target: "draft-2020-12" }) as Json;
  return fromJsonSchema(json, json.$defs ?? {});
}

// -------------------------------------------------------------------- comparison

function compare(expected: Shape, actual: Shape, path: string, problems: string[]): void {
  // A file field is described by the API as binary; Zod cannot describe a Blob.
  if (expected.kind === "file" && actual.kind === "any") return;
  if (expected.kind === "any" || expected.kind === "map") {
    if (!["any", "map", "object"].includes(actual.kind)) problems.push(`${path}: free-form in the API, ${actual.kind} in the contract`);
    return;
  }
  if (expected.nullable !== actual.nullable) {
    problems.push(`${path}: ${expected.nullable ? "nullable" : "never null"} in the API, ${actual.nullable ? "nullable" : "never null"} in the contract`);
  }
  if (expected.kind !== actual.kind) {
    problems.push(`${path}: ${expected.kind} in the API, ${actual.kind} in the contract`);
    return;
  }
  if (expected.kind === "scalar" && actual.kind === "scalar" && expected.type !== actual.type) {
    problems.push(`${path}: ${expected.type} in the API, ${actual.type} in the contract`);
  }
  if (expected.kind === "enum" && actual.kind === "enum" && expected.values.join() !== actual.values.join()) {
    problems.push(`${path}: values ${expected.values.join("|")} in the API, ${actual.values.join("|")} in the contract`);
  }
  if (expected.kind === "array" && actual.kind === "array") compare(expected.items, actual.items, `${path}[]`, problems);
  if (expected.kind === "object" && actual.kind === "object") {
    const names = new Set([...Object.keys(expected.props), ...Object.keys(actual.props)]);
    for (const name of [...names].sort()) {
      const want = expected.props[name];
      const got = actual.props[name];
      if (!want) problems.push(`${path}.${name}: not in the API`);
      else if (!got) problems.push(`${path}.${name}: missing from the contract`);
      else {
        if (want.required !== got.required) {
          problems.push(`${path}.${name}: ${want.required ? "required" : "optional"} in the API, ${got.required ? "required" : "optional"} in the contract`);
        }
        compare(want.shape, got.shape, `${path}.${name}`, problems);
      }
    }
  }
}

function parameters(operation: Json, where: "query" | "path"): Shape {
  const props: Record<string, { shape: Shape; required: boolean }> = {};
  for (const p of operation.parameters ?? []) {
    if (p.in !== where) continue;
    props[p.name] = { shape: fromOpenApi(p.schema ?? {}, "request"), required: Boolean(p.required) };
  }
  return { kind: "object", nullable: false, props };
}

type Endpoint = {
  method: string;
  path: string;
  status: number;
  body?: z.ZodType | null;
  bodyType?: "json" | "multipart";
  response?: z.ZodType | null;
  pathParams?: z.ZodType;
  queryParams?: z.ZodType;
};

for (const [name, endpoint] of Object.entries(endpoints as Record<string, Endpoint>)) {
  const operation = openapi.paths[endpoint.path]?.[endpoint.method.toLowerCase()];
  if (!operation) continue; // reported by routes.test.ts
  test(`${name}: parameters, body and response match the API`, () => {
    const problems: string[] = [];
    const empty: Shape = { kind: "object", nullable: false, props: {} };
    compare(parameters(operation, "path"), endpoint.pathParams ? fromZod(endpoint.pathParams, "input") : empty, "path", problems);
    compare(parameters(operation, "query"), endpoint.queryParams ? fromZod(endpoint.queryParams, "input") : empty, "query", problems);

    const content = operation.requestBody?.content ?? {};
    const bodySchema = content["application/json"]?.schema ?? content["multipart/form-data"]?.schema;
    if (bodySchema && endpoint.body) {
      compare(fromOpenApi(bodySchema, "request"), fromZod(endpoint.body, "input"), "body", problems);
      const multipart = !content["application/json"] || Object.values<Json>(resolve(bodySchema).properties ?? {}).some(
        (p) => resolve(p).format === "binary" || resolve(p.items ?? {}).format === "binary",
      );
      if (multipart !== (endpoint.bodyType === "multipart")) problems.push(`bodyType: ${multipart ? "multipart" : "json"} in the API`);
    } else if (Boolean(bodySchema) !== Boolean(endpoint.body)) {
      problems.push(`body: ${bodySchema ? "expected by the API" : "the API takes none"}`);
    }

    const answer = operation.responses[String(endpoint.status)]?.content?.["application/json"]?.schema;
    if (answer && endpoint.response) compare(fromOpenApi(answer, "response"), fromZod(endpoint.response, "output"), "response", problems);
    else if (Boolean(answer) !== Boolean(endpoint.response)) {
      problems.push(`response: ${answer ? "the API returns a body" : "the API returns none"}`);
    }
    assert.deepEqual(problems, []);
  });
}
