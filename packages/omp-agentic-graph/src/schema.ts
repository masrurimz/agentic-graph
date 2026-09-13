import { Schema } from "effect";

const Scope = Schema.Literals(["code", "memory", "all"] as const);
const Count = Schema.Finite;

// Server request/response schemas -----------------------------------------------------------

export const HealthResponse = Schema.Struct({
	ok: Schema.Boolean,
});

export const SyncRequest = Schema.Struct({
	repo_path: Schema.String,
	force: Schema.Boolean.pipe(Schema.optional),
});

export const SyncResponse = Schema.Struct({
	status: Schema.String,
});

export const SearchRequest = Schema.Struct({
	query: Schema.String,
	scope: Scope.pipe(Schema.optional),
	limit: Count.pipe(Schema.optional),
});

export const SearchResponse = Schema.Struct({
	results: Schema.Unknown,
});

export const ExploreRequest = Schema.Struct({
	target: Schema.String,
	direction: Schema.Literals(["callers", "callees"] as const).pipe(Schema.optional),
	depth: Count.pipe(Schema.optional),
});

export const ExploreResponse = Schema.Struct({
	results: Schema.Unknown,
});

export const CorrelateRequest = Schema.Struct({
	target: Schema.String,
	scope: Scope.pipe(Schema.optional),
	limit: Count.pipe(Schema.optional),
});

export const CorrelateResponse = Schema.Struct({
	code_results: Schema.Unknown.pipe(Schema.optional),
	memory_results: Schema.Unknown.pipe(Schema.optional),
	traces: Schema.Unknown.pipe(Schema.optional),
});

export const TraceRequest = Schema.Struct({
	step_id: Schema.String.pipe(Schema.optional),
	tool: Schema.String.pipe(Schema.optional),
	args: Schema.Record(Schema.String, Schema.Unknown).pipe(Schema.optional),
	result: Schema.String.pipe(Schema.optional),
	touched_files: Schema.Array(Schema.String).pipe(Schema.optional),
	touched_symbols: Schema.Array(Schema.String).pipe(Schema.optional),
	parent_step_id: Schema.String.pipe(Schema.optional),
});

export const TraceResponse = Schema.Struct({
	step_id: Schema.String,
});

export const RememberRequest = Schema.Struct({
	data: Schema.String,
	dataset_name: Schema.String.pipe(Schema.optional),
	node_set: Schema.Array(Schema.String).pipe(Schema.optional),
});

export const RememberResponse = Schema.Struct({
	status: Schema.String,
	dataset_id: Schema.String.pipe(Schema.optional),
	dataset_name: Schema.String,
});

export const RecallRequest = Schema.Struct({
	query: Schema.String,
	dataset_name: Schema.String.pipe(Schema.optional),
	node_set: Schema.Array(Schema.String).pipe(Schema.optional),
	top_k: Count.pipe(Schema.optional),
});

export const RecallResponse = Schema.Struct({
	results: Schema.Unknown,
});

// Tool parameter schemas --------------------------------------------------------------------

export const EmptyParams = Schema.Struct({});

export const SearchParams = Schema.Struct({
	query: Schema.String,
	scope: Scope.pipe(Schema.optional),
	limit: Count.pipe(Schema.optional),
});

export const CorrelateParams = Schema.Struct({
	target: Schema.String,
	scope: Scope.pipe(Schema.optional),
	limit: Count.pipe(Schema.optional),
});

export const RecallParams = Schema.Struct({
	query: Schema.String,
	top_k: Count.pipe(Schema.optional),
});

export const RememberParams = Schema.Struct({
	data: Schema.String,
	dataset_name: Schema.String.pipe(Schema.optional),
	node_set: Schema.Array(Schema.String).pipe(Schema.optional),
});

export const TraceParams = Schema.Struct({
	step_id: Schema.String.pipe(Schema.optional),
	tool: Schema.String.pipe(Schema.optional),
	args: Schema.Record(Schema.String, Schema.Unknown).pipe(Schema.optional),
	result: Schema.String.pipe(Schema.optional),
	touched_files: Schema.Array(Schema.String).pipe(Schema.optional),
	touched_symbols: Schema.Array(Schema.String).pipe(Schema.optional),
	parent_step_id: Schema.String.pipe(Schema.optional),
});

export const SyncParams = Schema.Struct({
	repo_path: Schema.String.pipe(Schema.optional),
	force: Schema.Boolean.pipe(Schema.optional),
});

export type SearchParams = typeof SearchParams.Type;
export type CorrelateParams = typeof CorrelateParams.Type;
export type RecallParams = typeof RecallParams.Type;
export type RememberParams = typeof RememberParams.Type;
export type TraceParams = typeof TraceParams.Type;
export type SyncParams = typeof SyncParams.Type;

// JSON schema generator for ToolDef.parameters -----------------------------------------------

export function parametersFromSchema<S extends Schema.Constraint>(
	schema: S,
): Record<string, unknown> {
	const standard = Schema.toStandardJSONSchemaV1(schema);
	const converter = (standard as any)["~standard"].jsonSchema as {
		output: (options: { target: "draft-2020-12" }) => Record<string, unknown>;
	};
	return converter.output({ target: "draft-2020-12" });
}
