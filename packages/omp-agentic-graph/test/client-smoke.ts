import * as client from "../src/client";

async function main() {
	console.log("health:", await client.health());
	console.log(
		"search:",
		await client.search("graph", "code", 2),
	);
	console.log("sync:", await client.sync("/home/zahid/work/labs/agentic-graph", false));
	console.log("trace:", await client.trace("", "test_tool", { a: 1 }, "ok", ["README.md"], [], ""));
	console.log("correlate:", await client.correlate("README.md", "code", 2));
}

main().catch((e) => {
	console.error(e);
	throw e;
});
