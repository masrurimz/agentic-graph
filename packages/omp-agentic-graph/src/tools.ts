import { createAgenticGraphTools, type ToolApi, type ToolDef } from "./tools-def";

export default function agenticGraphTools(pi: ToolApi): ToolDef[] {
	return createAgenticGraphTools(pi);
}
