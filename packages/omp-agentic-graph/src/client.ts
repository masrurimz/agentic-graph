import { Config, Data, Duration, Effect, Schema } from "effect";
import * as HttpClient from "effect/unstable/http/HttpClient";
import * as HttpClientRequest from "effect/unstable/http/HttpClientRequest";
import * as HttpClientResponse from "effect/unstable/http/HttpClientResponse";
import * as FetchHttpClient from "effect/unstable/http/FetchHttpClient";

import * as S from "./schema";

type ServiceFreeSchema<A> = Schema.Constraint & {
	readonly "Type": A;
	readonly "DecodingServices": never;
};

export class AgenticGraphError extends Data.TaggedError("AgenticGraphError")<{
	reason: "network" | "status" | "decode" | "config";
	message: string;
}> {}

const cogneeConfig = Config.all({
	baseUrl: Config.String("COGNEE_SERVER_URL").pipe(Config.withDefault("http://127.0.0.1:28195")),
	timeout: Config.Number("COGNEE_TIMEOUT").pipe(Config.withDefault(300)),
});

function runEffect<A, E>(
	effect: Effect.Effect<A, E, HttpClient.HttpClient>,
): Promise<A> {
	return Effect.runPromise(effect.pipe(Effect.provide(FetchHttpClient.layer)));
}

function call<A>(
	method: "GET" | "POST",
	path: string,
	body: unknown,
	responseSchema: ServiceFreeSchema<A>,
): Promise<A> {
	const program = Effect.gen(function* () {
		const cfg = yield* cogneeConfig;
		const url = `${cfg.baseUrl}${path}`;

		const request =
			method === "GET"
				? HttpClientRequest.get(url)
				: HttpClientRequest.post(url).pipe(HttpClientRequest.bodyJsonUnsafe(body));

		const response = yield* HttpClient.execute(request).pipe(
			Effect.timeout(Duration.seconds(cfg.timeout)),
		);

		const ok = yield* HttpClientResponse.filterStatusOk(response);
		const json = yield* ok.json;

		return yield* Schema.decodeUnknownEffect(responseSchema)(json, { onExcessProperty: "ignore" });
	}).pipe(
		Effect.mapError((error) => new AgenticGraphError({ reason: "network", message: String(error) })),
	);

	return runEffect(program);
}

export async function search(query: string, scope: string, limit: number): Promise<unknown> {
	const result = await call("POST", "/search", { query, scope, limit }, S.SearchResponse);
	return result.results;
}

export async function explore(target: string, direction: string, depth: number): Promise<unknown> {
	const result = await call("POST", "/explore", { target, direction, depth }, S.ExploreResponse);
	return result.results;
}

export async function correlate(target: string, scope: string, limit: number): Promise<unknown> {
	const result = await call("POST", "/correlate", { target, scope, limit }, S.CorrelateResponse);
	return {
		code_results: result.code_results ?? [],
		memory_results: result.memory_results ?? [],
		traces: result.traces ?? [],
	};
}

export async function recall(query: string, topK: number): Promise<unknown> {
	const result = await call("POST", "/api/v1/recall", { query, top_k: topK }, S.RecallResponse);
	return result.results;
}

export async function remember(
	data: string,
	datasetName: string,
	nodeSet: readonly string[],
): Promise<unknown> {
	const result = await call("POST", "/api/v1/remember", { data, dataset_name: datasetName, node_set: nodeSet }, S.RememberResponse);
	return result;
}

export async function trace(
	stepId: string,
	tool: string,
	args: Record<string, unknown>,
	result: string,
	touchedFiles: readonly string[],
	touchedSymbols: readonly string[],
	parentStepId: string,
): Promise<unknown> {
	const response = await call("POST", "/trace", {
		step_id: stepId,
		tool,
		args,
		result,
		touched_files: touchedFiles,
		touched_symbols: touchedSymbols,
		parent_step_id: parentStepId,
	}, S.TraceResponse);
	return response;
}

export async function sync(repoPath: string, force: boolean): Promise<unknown> {
	const result = await call("POST", "/sync", { repo_path: repoPath, force }, S.SyncResponse);
	return result;
}

export async function health(): Promise<unknown> {
	return call("GET", "/health", undefined, S.HealthResponse);
}
