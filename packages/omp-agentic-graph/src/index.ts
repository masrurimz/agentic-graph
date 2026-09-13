import * as client from "./client";

interface ExtensionContext {
	cwd: string;
}

interface ExtensionAPI {
	cwd: string;
	on: (event: string, handler: (event: unknown, ctx: ExtensionContext) => void | Promise<void>) => void;
	logger: {
		info: (msg: string, meta?: Record<string, unknown>) => void;
		error: (msg: string, meta?: Record<string, unknown>) => void;
		warn: (msg: string, meta?: Record<string, unknown>) => void;
	};
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

function recordFrom(value: unknown): Record<string, unknown> {
	return isRecord(value) ? value : {};
}

function extractTouchedFiles(_toolName: string, input: Record<string, unknown>): string[] {
	const refs: string[] = [];
	if (Array.isArray(input.paths)) {
		refs.push(...input.paths.filter((x): x is string => typeof x === "string"));
	}
	if (typeof input.path === "string") {
		refs.push(input.path);
	}
	if (typeof input.paths === "string") {
		refs.push(input.paths);
	}
	return refs;
}

function isTextContent(c: unknown): c is { type: "text"; text: string } {
	const rec = recordFrom(c);
	return rec.type === "text" && typeof rec.text === "string";
}

function extractTextContent(value: unknown): string {
	if (typeof value === "string") return value;
	const arr = Array.isArray(value) ? value : [];
	return arr.filter(isTextContent).map(c => c.text).join("\n");
}

export default function agenticGraphExtension(pi: ExtensionAPI): void {
	pi.on("session_start", async (_event, ctx) => {
		try {
			await client.sync(ctx.cwd, false);
			pi.logger.info("agentic-graph synced", { cwd: ctx.cwd });
		} catch (e) {
			pi.logger.warn("agentic-graph sync failed on session_start", { error: String(e) });
		}
	});

	pi.on("tool_result", async (event, ctx) => {
		const ev = recordFrom(event);
		const toolName = typeof ev.toolName === "string" ? ev.toolName : "unknown";
		const input = recordFrom(ev.input);
		const content = ev.content;
		const isError = ev.isError === true;
		const result = content ? JSON.stringify(content) : isError ? "error" : "ok";
		const touchedFiles = extractTouchedFiles(toolName, input);

		try {
			await client.trace("", toolName, input, result, touchedFiles, [], "");
		} catch (e) {
			pi.logger.warn("agentic-graph trace failed", { error: String(e) });
		}
	});

	pi.on("turn_end", async (event, ctx) => {
		const ev = recordFrom(event);
		const message = recordFrom(ev.message);
		const text = extractTextContent(message.content);
		if (text) {
			try {
				await client.remember(text, "agentic_graph_turn", []);
			} catch (e) {
				pi.logger.warn("agentic-graph remember failed on turn_end", { error: String(e) });
			}
		}

		try {
			await client.sync(ctx.cwd, false);
		} catch (e) {
			pi.logger.warn("agentic-graph sync failed on turn_end", { error: String(e) });
		}
	});
}
