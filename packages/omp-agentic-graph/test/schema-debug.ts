import { Schema } from "effect";
import * as S from "../src/schema";

async function main() {
	const raw = await fetch("http://127.0.0.1:28195/correlate", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ target: "README.md", scope: "code", limit: 2 }),
	}).then((r) => r.json());

	console.log("keys:", Object.keys(raw));
	console.log("memory_results present:", "memory_results" in raw);
	const decoded = Schema.decodeUnknownSync(S.CorrelateResponse)(raw);
	console.log("decoded:", decoded);
}

main().catch((e) => {
	console.error(e);
	throw e;
});
