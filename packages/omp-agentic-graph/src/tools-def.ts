import { Effect, Schema } from "effect";

import * as client from "./client";
import * as S from "./schema";

export interface TextContent {
	type: "text";
	text: string;
}

export interface ToolResult {
	content: TextContent[];
	details?: unknown;
	isError?: boolean;
}

export interface ToolContext {
	cwd: string;
}

export interface ToolApi {
	cwd: string;
}

export interface ToolDef {
	name: string;
	label: string;
	description: string;
	parameters: Record<string, unknown>;
	loadMode: "essential" | "discoverable";
	execute: (
		toolCallId: string,
		params: unknown,
		onUpdate: unknown,
		ctx: ToolContext,
		signal?: AbortSignal,
	) => Promise<ToolResult>;
}

function textResult(obj: unknown): ToolResult {
	return {
		content: [{ type: "text", text: JSON.stringify(obj, null, 2) }],
		details: obj,
	};
}

function errorResult(message: string): ToolResult {
	return {
		content: [{ type: "text", text: message }],
		details: { error: message },
		isError: true,
	};
}

function handleError(e: unknown): ToolResult {
	return errorResult(e instanceof Error ? e.message : String(e));
}

type ServiceFreeSchema<A> = Schema.Constraint & {
	readonly "Type": A;
	readonly "DecodingServices": never;
};

function decodeParams<A>(
	schema: ServiceFreeSchema<A>,
	raw: unknown,
): Promise<A> {
	return Effect.runPromise(Schema.decodeUnknownEffect(schema)(raw, { onExcessProperty: "ignore" }));
}

export function createAgenticGraphTools(_pi: ToolApi): ToolDef[] {
	return [
		{
			name: "agentic_search",
			label: "Agentic Graph Search",
			description: "Search the agentic-graph knowledge graph for code, memories, or both.",
			parameters: S.parametersFromSchema(S.SearchParams),
			loadMode: "essential",
			async execute(_id, raw, _onUpdate, _ctx, _signal) {
				try {
					const params = await decodeParams(S.SearchParams, raw);
					const result = await client.search(
						params.query,
						params.scope ?? "all",
						params.limit ?? 10,
					);
					return textResult(result);
				} catch (e) {
					return handleError(e);
				}
			},
		},
		{
			name: "agentic_correlate",
			label: "Agentic Graph Correlate",
			description: "Find related code and/or memory nodes for a target (symbol, file, concept).",
			parameters: S.parametersFromSchema(S.CorrelateParams),
			loadMode: "essential",
			async execute(_id, raw, _onUpdate, _ctx, _signal) {
				try {
					const params = await decodeParams(S.CorrelateParams, raw);
					const result = await client.correlate(
						params.target,
						params.scope ?? "all",
						params.limit ?? 10,
					);
					return textResult(result);
				} catch (e) {
					return handleError(e);
				}
			},
		},
		{
			name: "agentic_recall",
			label: "Agentic Graph Recall",
			description: "Recall semantically relevant memories from the agentic-graph vector store.",
			parameters: S.parametersFromSchema(S.RecallParams),
			loadMode: "essential",
			async execute(_id, raw, _onUpdate, _ctx, _signal) {
				try {
					const params = await decodeParams(S.RecallParams, raw);
					const result = await client.recall(params.query, params.top_k ?? 5);
					return textResult(result);
				} catch (e) {
					return handleError(e);
				}
			},
		},
		{
			name: "agentic_remember",
			label: "Agentic Graph Remember",
			description: "Persist a text snippet into the agentic-graph vector store as a memory.",
			parameters: S.parametersFromSchema(S.RememberParams),
			loadMode: "essential",
			async execute(_id, raw, _onUpdate, _ctx, _signal) {
				try {
					const params = await decodeParams(S.RememberParams, raw);
					const result = await client.remember(
						params.data,
						params.dataset_name ?? "agentic_graph",
						params.node_set ?? [],
					);
					return textResult(result);
				} catch (e) {
					return handleError(e);
				}
			},
		},
		{
			name: "agentic_trace",
			label: "Agentic Graph Trace",
			description:
				"Append an agentic step (tool call, decision, result, touched files/symbols) to the graph.",
			parameters: S.parametersFromSchema(S.TraceParams),
			loadMode: "discoverable",
			async execute(_id, raw, _onUpdate, _ctx, _signal) {
				try {
					const params = await decodeParams(S.TraceParams, raw);
					const result = await client.trace(
						params.step_id ?? "",
						params.tool ?? "",
						params.args ?? {},
						params.result ?? "",
						params.touched_files ?? [],
						params.touched_symbols ?? [],
						params.parent_step_id ?? "",
					);
					return textResult(result);
				} catch (e) {
					return handleError(e);
				}
			},
		},
		{
			name: "agentic_sync",
			label: "Agentic Graph Sync",
			description: "Re-index the current worktree code into the agentic-graph code graph.",
			parameters: S.parametersFromSchema(S.SyncParams),
			loadMode: "discoverable",
			async execute(_id, raw, _onUpdate, ctx, _signal) {
				try {
					const params = await decodeParams(S.SyncParams, raw);
					const result = await client.sync(params.repo_path ?? ctx.cwd, params.force ?? false);
					return textResult(result);
				} catch (e) {
					return handleError(e);
				}
			},
		},
		{
			name: "agentic_health",
			label: "Agentic Graph Health",
			description: "Check the agentic-graph server health.",
			parameters: S.parametersFromSchema(S.EmptyParams),
			loadMode: "discoverable",
			async execute(_id, _raw, _onUpdate, _ctx, _signal) {
				try {
					const result = await client.health();
					return textResult(result);
				} catch (e) {
					return handleError(e);
				}
			},
		},
	];
}

