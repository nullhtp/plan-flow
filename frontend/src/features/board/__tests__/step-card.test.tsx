import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@tanstack/react-router", () => ({
	useNavigate: () => vi.fn(),
}));
// Chat pulls in react-query/API — stub it out for these structural tests.
vi.mock("../components/TaskChat", () => ({ TaskChat: () => <div data-testid="chat" /> }));

import { StepCard } from "../components/StepCard";
import type { TaskResponse } from "../types";

function makeTask(overrides: Partial<TaskResponse> = {}): TaskResponse {
	return {
		id: "t1",
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

const baseProps = {
	allTasks: [] as TaskResponse[],
	boardId: "board-1",
	onSetStatus: vi.fn(),
	onToggleSubtask: vi.fn(),
};

describe("StepCard", () => {
	it("renders title and description as read-only text (no editable inputs)", () => {
		render(
			<StepCard
				{...baseProps}
				task={makeTask({
					title: "Book truck",
					description: "Call the rental company",
					status: "in_progress",
				})}
			/>,
		);
		expect(screen.getByText("Book truck")).toBeInTheDocument();
		expect(screen.getByText("Call the rental company")).toBeInTheDocument();
		// No text inputs / textareas — title and description are not editable.
		expect(screen.queryByRole("textbox")).toBeNull();
	});

	it("shows a Start button for not_started tasks", () => {
		const onSetStatus = vi.fn();
		render(
			<StepCard
				{...baseProps}
				onSetStatus={onSetStatus}
				task={makeTask({ status: "not_started" })}
			/>,
		);
		fireEvent.click(screen.getByRole("button", { name: "Start task" }));
		expect(onSetStatus).toHaveBeenCalledWith("in_progress");
	});

	it("shows Mark as done / Reset for in_progress tasks", () => {
		const onSetStatus = vi.fn();
		render(
			<StepCard
				{...baseProps}
				onSetStatus={onSetStatus}
				task={makeTask({ status: "in_progress" })}
			/>,
		);
		fireEvent.click(screen.getByRole("button", { name: /mark as done/i }));
		expect(onSetStatus).toHaveBeenCalledWith("done");
		fireEvent.click(screen.getByRole("button", { name: "Reset" }));
		expect(onSetStatus).toHaveBeenCalledWith("not_started");
	});

	it("shows Completed + Reopen for done tasks", () => {
		const onSetStatus = vi.fn();
		render(
			<StepCard {...baseProps} onSetStatus={onSetStatus} task={makeTask({ status: "done" })} />,
		);
		expect(screen.getByText("Completed")).toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: "Reopen" }));
		expect(onSetStatus).toHaveBeenCalledWith("in_progress");
	});

	it("shows a locked note and no status action buttons when locked", () => {
		const dep = makeTask({ id: "d1", title: "Prerequisite", status: "not_started" });
		const task = makeTask({ is_locked: true, dependency_ids: ["d1"] });
		render(<StepCard {...baseProps} allTasks={[dep, task]} task={task} />);
		expect(screen.getByText(/Locked/)).toHaveTextContent("Prerequisite");
		expect(screen.queryByRole("button", { name: "Start task" })).toBeNull();
		expect(screen.queryByRole("button", { name: /mark as done/i })).toBeNull();
	});

	it("lets subtasks be toggled but offers no add or delete affordance", () => {
		const onToggleSubtask = vi.fn();
		const task = makeTask({
			status: "in_progress",
			subtasks: [
				{
					id: "s1",
					title: "Sub A",
					completed: false,
					position: "a",
					action_label: null,
					action_icon: null,
					action_prompt: null,
					created_at: "",
				},
				{
					id: "s2",
					title: "Sub B",
					completed: true,
					position: "b",
					action_label: null,
					action_icon: null,
					action_prompt: null,
					created_at: "",
				},
			],
		});
		render(<StepCard {...baseProps} onToggleSubtask={onToggleSubtask} task={task} />);
		const checkboxes = screen.getAllByRole("checkbox");
		expect(checkboxes).toHaveLength(2);
		fireEvent.click(checkboxes[0]);
		expect(onToggleSubtask).toHaveBeenCalledWith("s1", true);
		// No "add subtask" input.
		expect(screen.queryByPlaceholderText(/add subtask/i)).toBeNull();
		// Only the status buttons exist (Mark as done + Reset) — no per-subtask delete buttons.
		expect(screen.getAllByRole("button")).toHaveLength(2);
	});

	it("offers Open Sub-Board for sub-board tasks instead of subtasks", () => {
		render(
			<StepCard {...baseProps} task={makeTask({ status: "in_progress", sub_board_id: "sb1" })} />,
		);
		expect(screen.getByRole("button", { name: /open sub-board/i })).toBeInTheDocument();
		expect(screen.queryByText("Subtasks")).toBeNull();
	});
});
