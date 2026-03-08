import { describe, expect, it } from "vitest";
import type { EdgeResponse, TaskResponse } from "../types";
import { filterBoardForFocusView, isTaskHiddenInFocus } from "../utils/board-filters";

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

describe("filterBoardForFocusView", () => {
	it("shows all done tasks", () => {
		const tasks = [
			makeTask({ id: "t1", status: "done" }),
			makeTask({ id: "t2", status: "done" }),
			makeTask({ id: "t3", status: "done", is_goal_node: true }),
		];
		const edges: EdgeResponse[] = [
			{ source: "t1", target: "t2" },
			{ source: "t2", target: "t3" },
		];

		const result = filterBoardForFocusView(tasks, edges);
		expect(result.tasks).toHaveLength(3);
		expect(result.edges).toHaveLength(2);
	});

	it("shows in_progress tasks", () => {
		const tasks = [
			makeTask({ id: "t1", status: "in_progress" }),
			makeTask({ id: "t2", status: "done" }),
		];
		const result = filterBoardForFocusView(tasks, []);
		expect(result.tasks.map((t) => t.id)).toContain("t1");
	});

	it("shows unlocked not_started tasks", () => {
		const tasks = [
			makeTask({ id: "t1", status: "not_started", is_locked: false }),
			makeTask({ id: "t2", status: "not_started", is_locked: true }),
		];
		const result = filterBoardForFocusView(tasks, []);
		expect(result.tasks).toHaveLength(1);
		expect(result.tasks[0].id).toBe("t1");
	});

	it("hides locked not_started tasks", () => {
		const tasks = [
			makeTask({ id: "t1", status: "not_started", is_locked: true }),
			makeTask({ id: "t2", status: "not_started", is_locked: true }),
		];
		const result = filterBoardForFocusView(tasks, []);
		expect(result.tasks).toHaveLength(0);
	});

	it("always shows the goal node even if locked", () => {
		const tasks = [
			makeTask({ id: "t1", status: "not_started", is_locked: true, is_goal_node: true }),
			makeTask({ id: "t2", status: "not_started", is_locked: true }),
		];
		const result = filterBoardForFocusView(tasks, []);
		expect(result.tasks).toHaveLength(1);
		expect(result.tasks[0].id).toBe("t1");
	});

	it("filters edges to visible tasks only", () => {
		const tasks = [
			makeTask({ id: "t1", status: "done" }),
			makeTask({ id: "t2", status: "not_started", is_locked: true }), // hidden
			makeTask({ id: "t3", status: "not_started", is_locked: true }), // hidden
			makeTask({ id: "goal", status: "not_started", is_locked: true, is_goal_node: true }),
		];
		const edges: EdgeResponse[] = [
			{ source: "t1", target: "t2" }, // t2 hidden -> edge hidden
			{ source: "t2", target: "t3" }, // both hidden -> edge hidden
			{ source: "t1", target: "goal" }, // both visible -> edge kept
		];

		const result = filterBoardForFocusView(tasks, edges);
		expect(result.edges).toHaveLength(1);
		expect(result.edges[0]).toEqual({ source: "t1", target: "goal" });
	});

	it("handles mixed state board correctly", () => {
		const tasks = [
			makeTask({ id: "t1", status: "done" }),
			makeTask({ id: "t2", status: "done" }),
			makeTask({ id: "t3", status: "in_progress" }),
			makeTask({ id: "t4", status: "not_started", is_locked: false }),
			makeTask({ id: "t5", status: "not_started", is_locked: true }),
			makeTask({ id: "t6", status: "not_started", is_locked: true }),
			makeTask({ id: "goal", status: "not_started", is_locked: true, is_goal_node: true }),
		];
		const edges: EdgeResponse[] = [];

		const result = filterBoardForFocusView(tasks, edges);
		// Visible: t1 (done), t2 (done), t3 (in_progress), t4 (unlocked), goal
		expect(result.tasks).toHaveLength(5);
		const ids = result.tasks.map((t) => t.id);
		expect(ids).toContain("t1");
		expect(ids).toContain("t2");
		expect(ids).toContain("t3");
		expect(ids).toContain("t4");
		expect(ids).toContain("goal");
		expect(ids).not.toContain("t5");
		expect(ids).not.toContain("t6");
	});

	it("shows identical graph when all tasks are actionable", () => {
		const tasks = [
			makeTask({ id: "t1", status: "done" }),
			makeTask({ id: "t2", status: "in_progress" }),
			makeTask({ id: "t3", status: "not_started", is_locked: false }),
			makeTask({ id: "goal", status: "not_started", is_locked: false, is_goal_node: true }),
		];
		const edges: EdgeResponse[] = [
			{ source: "t1", target: "t2" },
			{ source: "t2", target: "t3" },
			{ source: "t3", target: "goal" },
		];

		const result = filterBoardForFocusView(tasks, edges);
		expect(result.tasks).toHaveLength(4);
		expect(result.edges).toHaveLength(3);
	});

	it("handles empty board", () => {
		const result = filterBoardForFocusView([], []);
		expect(result.tasks).toHaveLength(0);
		expect(result.edges).toHaveLength(0);
	});
});

describe("isTaskHiddenInFocus", () => {
	it("returns true for locked not_started tasks", () => {
		expect(isTaskHiddenInFocus(makeTask({ status: "not_started", is_locked: true }))).toBe(true);
	});

	it("returns false for done tasks", () => {
		expect(isTaskHiddenInFocus(makeTask({ status: "done" }))).toBe(false);
	});

	it("returns false for in_progress tasks", () => {
		expect(isTaskHiddenInFocus(makeTask({ status: "in_progress" }))).toBe(false);
	});

	it("returns false for unlocked not_started tasks", () => {
		expect(isTaskHiddenInFocus(makeTask({ status: "not_started", is_locked: false }))).toBe(false);
	});

	it("returns false for goal node even if locked", () => {
		expect(
			isTaskHiddenInFocus(makeTask({ status: "not_started", is_locked: true, is_goal_node: true })),
		).toBe(false);
	});
});
