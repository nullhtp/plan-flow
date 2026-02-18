import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// Mock @xyflow/react — Handle components require ReactFlow context
vi.mock("@xyflow/react", () => ({
	Handle: () => null,
	Position: { Top: "top", Bottom: "bottom" },
}));

import { TaskNode } from "../components/TaskNode";
import type { TaskResponse } from "../types";

function makeTask(overrides: Partial<TaskResponse> = {}): TaskResponse {
	return {
		id: "task-1",
		title: "Test Task",
		description: "A task",
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

describe("TaskNode", () => {
	it("renders a basic task without sub-board styling", () => {
		const task = makeTask();
		const { container } = render(
			<TaskNode data={{ task, allTasks: [task], has_sub_board: false }} />,
		);
		expect(screen.getByText("Test Task")).toBeInTheDocument();
		// No dashed border or violet styling
		const node = container.firstChild as HTMLElement;
		expect(node.className).not.toContain("border-dashed");
		expect(node.className).not.toContain("border-violet");
	});

	it("renders dashed purple border when has_sub_board is true", () => {
		const task = makeTask({ sub_board_id: "sb-1" });
		const { container } = render(
			<TaskNode data={{ task, allTasks: [task], has_sub_board: true }} />,
		);
		const node = container.firstChild as HTMLElement;
		expect(node.className).toContain("border-dashed");
		expect(node.className).toContain("border-violet-500");
	});

	it("renders layers icon when has_sub_board is true", () => {
		const task = makeTask({ sub_board_id: "sb-1" });
		render(<TaskNode data={{ task, allTasks: [task], has_sub_board: true }} />);
		// Layers icon is rendered in the top-right corner (absolute positioned div)
		const node = document.querySelector(".absolute.top-2.right-2");
		expect(node).not.toBeNull();
	});

	it("does not render layers icon when has_sub_board is false", () => {
		const task = makeTask();
		render(<TaskNode data={{ task, allTasks: [task], has_sub_board: false }} />);
		const node = document.querySelector(".absolute.top-2.right-2");
		expect(node).toBeNull();
	});

	it("shows sub-board progress instead of subtask count when sub-board exists", () => {
		const task = makeTask({
			sub_board_id: "sb-1",
			sub_board_progress: { task_count: 8, completed_task_count: 3 },
			subtasks: [
				{
					id: "st-1",
					title: "Old subtask",
					completed: false,
					position: "a",
					action_label: null,
					action_icon: null,
					action_prompt: null,
					created_at: "2025-01-01T00:00:00Z",
				},
			],
		});
		render(<TaskNode data={{ task, allTasks: [task], has_sub_board: true }} />);
		expect(screen.getByText("3/8 tasks")).toBeInTheDocument();
	});

	it("shows subtask count when no sub-board", () => {
		const task = makeTask({
			subtasks: [
				{
					id: "st-1",
					title: "Sub 1",
					completed: true,
					position: "a",
					action_label: null,
					action_icon: null,
					action_prompt: null,
					created_at: "2025-01-01T00:00:00Z",
				},
				{
					id: "st-2",
					title: "Sub 2",
					completed: false,
					position: "b",
					action_label: null,
					action_icon: null,
					action_prompt: null,
					created_at: "2025-01-01T00:00:00Z",
				},
			],
		});
		render(<TaskNode data={{ task, allTasks: [task], has_sub_board: false }} />);
		expect(screen.getByText("1/2")).toBeInTheDocument();
	});

	it("applies locked styling when task is locked", () => {
		const dep = makeTask({ id: "dep-1", title: "Prerequisite", status: "not_started" });
		const task = makeTask({
			is_locked: true,
			dependency_ids: ["dep-1"],
		});
		const { container } = render(
			<TaskNode data={{ task, allTasks: [dep, task], has_sub_board: false }} />,
		);
		const node = container.firstChild as HTMLElement;
		expect(node.className).toContain("opacity-60");
		expect(node.title).toContain("Prerequisite");
	});
});
