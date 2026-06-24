import { describe, expect, it } from "vitest";
import type { EdgeResponse, TaskResponse } from "../types";
import { getDefaultStepId, getStepSequence, topologicalOrder } from "../utils/stepper-order";

function makeTask(overrides: Partial<TaskResponse> = {}): TaskResponse {
	return {
		id: "task-1",
		title: "Test Task",
		description: "",
		status: "not_started",
		is_goal_node: false,
		due_date: null,
		priority: null,
		estimated_minutes: null,
		subtasks: [],
		dependency_ids: [],
		dependent_ids: [],
		is_locked: false,
		sub_board_id: null,
		sub_board_progress: null,
		created_at: "2025-01-01T00:00:00Z",
		...overrides,
	};
}

describe("topologicalOrder", () => {
	it("orders prerequisites before dependents", () => {
		const tasks = [
			makeTask({ id: "c", created_at: "2025-01-03T00:00:00Z" }),
			makeTask({ id: "a", created_at: "2025-01-01T00:00:00Z" }),
			makeTask({ id: "b", created_at: "2025-01-02T00:00:00Z" }),
		];
		const edges: EdgeResponse[] = [
			{ source: "a", target: "b" },
			{ source: "b", target: "c" },
		];
		const order = topologicalOrder(tasks, edges).map((t) => t.id);
		expect(order).toEqual(["a", "b", "c"]);
	});

	it("tie-breaks independent ready nodes by created_at then id", () => {
		const tasks = [
			makeTask({ id: "z", created_at: "2025-01-01T00:00:00Z" }),
			makeTask({ id: "a", created_at: "2025-01-01T00:00:00Z" }),
			makeTask({ id: "m", created_at: "2024-12-31T00:00:00Z" }),
		];
		const order = topologicalOrder(tasks, []).map((t) => t.id);
		// m has the earliest created_at; a before z by id at equal timestamp
		expect(order).toEqual(["m", "a", "z"]);
	});

	it("includes every task exactly once", () => {
		const tasks = [makeTask({ id: "a" }), makeTask({ id: "b" }), makeTask({ id: "c" })];
		const order = topologicalOrder(tasks, [{ source: "a", target: "c" }]);
		expect(order).toHaveLength(3);
		expect(new Set(order.map((t) => t.id)).size).toBe(3);
	});

	it("does not drop tasks if an unexpected cycle exists", () => {
		const tasks = [makeTask({ id: "a" }), makeTask({ id: "b" })];
		const edges: EdgeResponse[] = [
			{ source: "a", target: "b" },
			{ source: "b", target: "a" },
		];
		const order = topologicalOrder(tasks, edges);
		expect(order).toHaveLength(2);
	});

	it("handles an empty board", () => {
		expect(topologicalOrder([], [])).toEqual([]);
	});
});

describe("getStepSequence", () => {
	it("returns every task as one linear sequence in dependency order", () => {
		const tasks = [
			makeTask({ id: "t1", status: "done", created_at: "2025-01-01T00:00:00Z" }),
			makeTask({ id: "t2", status: "in_progress", created_at: "2025-01-02T00:00:00Z" }),
			makeTask({ id: "t3", status: "not_started", created_at: "2025-01-03T00:00:00Z" }),
			makeTask({
				id: "t4",
				status: "not_started",
				is_locked: true,
				created_at: "2025-01-04T00:00:00Z",
			}),
			makeTask({
				id: "goal",
				status: "not_started",
				is_locked: true,
				is_goal_node: true,
				created_at: "2025-01-05T00:00:00Z",
			}),
		];
		const edges: EdgeResponse[] = [
			{ source: "t1", target: "t2" },
			{ source: "t2", target: "t3" },
			{ source: "t3", target: "t4" },
			{ source: "t4", target: "goal" },
		];
		// All tasks present, including done and locked ones; goal node last.
		expect(getStepSequence(tasks, edges).map((t) => t.id)).toEqual([
			"t1",
			"t2",
			"t3",
			"t4",
			"goal",
		]);
	});

	it("serializes parallel branches into one sequence with prerequisites first", () => {
		// root -> a, root -> b (a and b are parallel), both -> goal
		const tasks = [
			makeTask({ id: "root", created_at: "2025-01-01T00:00:00Z" }),
			makeTask({ id: "a", created_at: "2025-01-02T00:00:00Z" }),
			makeTask({ id: "b", created_at: "2025-01-03T00:00:00Z" }),
			makeTask({ id: "goal", is_goal_node: true, created_at: "2025-01-04T00:00:00Z" }),
		];
		const edges: EdgeResponse[] = [
			{ source: "root", target: "a" },
			{ source: "root", target: "b" },
			{ source: "a", target: "goal" },
			{ source: "b", target: "goal" },
		];
		const order = getStepSequence(tasks, edges).map((t) => t.id);
		expect(order).toHaveLength(4);
		// Single sequence: root first, goal last, a and b serialized in between.
		expect(order[0]).toBe("root");
		expect(order[3]).toBe("goal");
		expect(order.slice(1, 3).sort()).toEqual(["a", "b"]);
	});
});

describe("getDefaultStepId", () => {
	it("prefers the first in_progress task", () => {
		const steps = [
			makeTask({ id: "a", status: "done" }),
			makeTask({ id: "b", status: "in_progress" }),
			makeTask({ id: "c", status: "not_started" }),
		];
		expect(getDefaultStepId(steps)).toBe("b");
	});

	it("falls back to the first not-done task", () => {
		const steps = [
			makeTask({ id: "a", status: "done" }),
			makeTask({ id: "b", status: "not_started" }),
			makeTask({ id: "c", status: "not_started" }),
		];
		expect(getDefaultStepId(steps)).toBe("b");
	});

	it("falls back to the first task when everything is done", () => {
		const steps = [makeTask({ id: "a", status: "done" }), makeTask({ id: "b", status: "done" })];
		expect(getDefaultStepId(steps)).toBe("a");
	});

	it("returns null for an empty sequence", () => {
		expect(getDefaultStepId([])).toBeNull();
	});
});
