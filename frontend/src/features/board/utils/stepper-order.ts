import type { EdgeResponse, TaskResponse } from "../types";

/**
 * Topologically sorts all tasks using dependency edges (Kahn's algorithm), so a
 * prerequisite always precedes its dependents. Ready nodes are tie-broken by
 * `created_at` then `id` for deterministic ordering. Tasks not referenced by any
 * edge are still included. Any remainder caused by an unexpected cycle (a valid
 * board is always a DAG) is appended in `created_at` order rather than dropped.
 */
export function topologicalOrder(tasks: TaskResponse[], edges: EdgeResponse[]): TaskResponse[] {
	const byId = new Map(tasks.map((t) => [t.id, t]));
	const indegree = new Map<string, number>();
	const dependents = new Map<string, string[]>(); // prerequisite -> dependents

	for (const t of tasks) {
		indegree.set(t.id, 0);
		dependents.set(t.id, []);
	}
	for (const edge of edges) {
		// edge.source = prerequisite, edge.target = dependent (blocked task)
		if (!byId.has(edge.source) || !byId.has(edge.target)) continue;
		dependents.get(edge.source)?.push(edge.target);
		indegree.set(edge.target, (indegree.get(edge.target) ?? 0) + 1);
	}

	const compareIds = (a: string, b: string): number => {
		const ta = byId.get(a);
		const tb = byId.get(b);
		if (!ta || !tb) return 0;
		if (ta.created_at !== tb.created_at) return ta.created_at < tb.created_at ? -1 : 1;
		return ta.id < tb.id ? -1 : ta.id > tb.id ? 1 : 0;
	};

	const ready = tasks
		.filter((t) => (indegree.get(t.id) ?? 0) === 0)
		.map((t) => t.id)
		.sort(compareIds);

	const order: TaskResponse[] = [];
	const visited = new Set<string>();

	while (ready.length > 0) {
		const id = ready.shift();
		if (id === undefined || visited.has(id)) continue;
		visited.add(id);
		const task = byId.get(id);
		if (task) order.push(task);

		const newlyReady: string[] = [];
		for (const dep of dependents.get(id) ?? []) {
			indegree.set(dep, (indegree.get(dep) ?? 0) - 1);
			if ((indegree.get(dep) ?? 0) === 0) newlyReady.push(dep);
		}
		if (newlyReady.length > 0) {
			ready.push(...newlyReady);
			ready.sort(compareIds);
		}
	}

	if (order.length < tasks.length) {
		const remaining = tasks
			.filter((t) => !visited.has(t.id))
			.sort((a, b) => compareIds(a.id, b.id));
		order.push(...remaining);
	}

	return order;
}

/**
 * The ordered step sequence walked by the Simple stepper: every task on the
 * board flattened into a single linear sequence in dependency order. Parallel
 * branches are serialized into one ordered list — the stepper never shows
 * parallel paths. Tasks of every status (including done and locked) are
 * included so the whole plan can be walked start to finish.
 */
export function getStepSequence(tasks: TaskResponse[], edges: EdgeResponse[]): TaskResponse[] {
	return topologicalOrder(tasks, edges);
}

/**
 * The step the stepper should land on by default: the first `in_progress` task
 * (work already started) if any, otherwise the first task that is not yet done
 * (where the user should resume), otherwise the first task. Returns `null` for
 * an empty sequence.
 */
export function getDefaultStepId(steps: TaskResponse[]): string | null {
	if (steps.length === 0) return null;
	const inProgress = steps.find((t) => t.status === "in_progress");
	if (inProgress) return inProgress.id;
	const firstUndone = steps.find((t) => t.status !== "done");
	return (firstUndone ?? steps[0]).id;
}
