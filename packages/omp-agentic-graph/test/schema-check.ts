import { Schema } from "effect";
import {
	parametersFromSchema,
	SearchParams,
	TraceParams,
	SyncParams,
	RememberParams,
} from "../src/schema.ts";

for (const [name, schema] of [
	["SearchParams", SearchParams],
	["TraceParams", TraceParams],
	["SyncParams", SyncParams],
	["RememberParams", RememberParams],
] as const) {
	const json = parametersFromSchema(schema as any);
	console.log(`--- ${name} ---`);
	console.log(JSON.stringify(json, null, 2));
}

// also test decode
const raw = { query: "foo", scope: "code", limit: 5 };
const decoded = Schema.decodeUnknownSync(SearchParams)(raw);
console.log("--- decoded SearchParams ---");
console.log(decoded);
