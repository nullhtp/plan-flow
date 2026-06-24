import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock router — StepperView only needs useNavigate.
const navigateMock = vi.fn();
vi.mock("@tanstack/react-router", () => ({
	useNavigate: () => navigateMock,
}));

// Mock mutation hooks so no API/query context is required.
const updateMutate = vi.fn();
const deleteMutate = vi.fn();
const updateSubtaskMutate = vi.fn();
vi.mock("../hooks/use-task-mutations", () => ({
	useTaskMutations: () => ({
		updateTask: { mutate: updateMutate },
		deleteTask: { mutate: deleteMutate },
	}),
}));
vi.mock("../hooks/use-subtask-mutations", () => ({
	useSubtaskMutations: () => ({
		createSubtask: { mutate: vi.fn() },
		updateSubtask: { mutate: updateSubtaskMutate },
		deleteSubtask: { mutate: vi.fn() },
	}),
}));

// Stub the celebration (canvas-confetti) and the heavy step content.
vi.mock("../components/Celebration", () => ({ Celebration: () => null }));
vi.mock("../components/StepCard", () => ({
	StepCard: ({
		task,
		onSetStatus,
		onToggleSubtask,
	}: {
		task: { id: string; title: string; subtasks?: { id: string; completed: boolean }[] };
		onSetStatus: (status: string) => void;
		onToggleSubtask: (subtaskId: string, completed: boolean) => void;
	}) => (
		<div>
			<div data-testid="step-task">{task.title}</div>
			<button type="button" onClick={() => onSetStatus("done")}>
				mark-done
			</button>
			{(task.subtasks ?? []).map((st) => (
				<button key={st.id} type="button" onClick={() => onToggleSubtask(st.id, !st.completed)}>
					toggle-{st.id}
				</button>
			))}
		</div>
	),
}));

import { StepperView } from "../components/StepperView";
import type { BoardResponse, EdgeResponse, TaskResponse } from "../types";

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

function makeBoard(
	tasks: TaskResponse[],
	edges: EdgeResponse[] = [],
	overrides: Partial<BoardResponse> = {},
): BoardResponse {
	return {
		id: "board-1",
		goal_id: null,
		title: "Board",
		tasks,
		edges,
		is_completed: false,
		user_meta: null,
		parent_task_id: null,
		parent_board: null,
		role: "owner",
		created_at: "2025-01-01T00:00:00Z",
		...overrides,
	};
}

const noop = () => {};

const chainBoard = () => {
	const tasks = [
		makeTask({ id: "t1", title: "T1", status: "done", created_at: "2025-01-01T00:00:00Z" }),
		makeTask({ id: "t2", title: "T2", status: "in_progress", created_at: "2025-01-02T00:00:00Z" }),
		makeTask({ id: "t3", title: "T3", status: "not_started", created_at: "2025-01-03T00:00:00Z" }),
		makeTask({
			id: "t4",
			title: "T4",
			status: "not_started",
			is_locked: true,
			created_at: "2025-01-04T00:00:00Z",
		}),
	];
	const edges: EdgeResponse[] = [
		{ source: "t1", target: "t2" },
		{ source: "t2", target: "t3" },
		{ source: "t3", target: "t4" },
	];
	return makeBoard(tasks, edges);
};

beforeEach(() => {
	vi.clearAllMocks();
});

describe("StepperView", () => {
	it("walks every task as one sequence (incl. done & locked) and lands on in-progress", () => {
		render(<StepperView board={chainBoard()} onSwitchToAdvanced={noop} />);
		// 4 total tasks in the sequence; in_progress T2 is step 2.
		expect(screen.getByTestId("step-task")).toHaveTextContent("T2");
		expect(screen.getByText("Step 2 of 4")).toBeInTheDocument();
		expect(screen.getByText("1/4 done")).toBeInTheDocument();
	});

	it("disables Next until the current task is done; Previous revisits done steps", () => {
		render(<StepperView board={chainBoard()} onSwitchToAdvanced={noop} />);
		// Lands on the in-progress T2 — Next is gated until it is done.
		expect(screen.getByTestId("step-task")).toHaveTextContent("T2");
		expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
		expect(screen.getByText("Complete this task to continue")).toBeInTheDocument();
		// Previous goes back to the completed T1, where Next is enabled again.
		fireEvent.click(screen.getByRole("button", { name: "Previous" }));
		expect(screen.getByTestId("step-task")).toHaveTextContent("T1");
		const nextBtn = screen.getByRole("button", { name: "Next" });
		expect(nextBtn).toBeEnabled();
		fireEvent.click(nextBtn);
		expect(screen.getByTestId("step-task")).toHaveTextContent("T2");
	});

	it("marks the task done and advances to the next step", () => {
		const tasks = [
			makeTask({
				id: "t2",
				title: "T2",
				status: "in_progress",
				created_at: "2025-01-02T00:00:00Z",
			}),
			makeTask({
				id: "t3",
				title: "T3",
				status: "not_started",
				created_at: "2025-01-03T00:00:00Z",
			}),
		];
		const edges: EdgeResponse[] = [{ source: "t2", target: "t3" }];
		render(<StepperView board={makeBoard(tasks, edges)} onSwitchToAdvanced={noop} />);
		expect(screen.getByTestId("step-task")).toHaveTextContent("T2");
		fireEvent.click(screen.getByText("mark-done"));
		expect(updateMutate).toHaveBeenCalledWith({ taskId: "t2", data: { status: "done" } });
		expect(screen.getByTestId("step-task")).toHaveTextContent("T3");
		expect(screen.getByText("Step 2 of 2")).toBeInTheDocument();
	});

	it("auto-completes the task and advances when the last subtask is checked", () => {
		const sub = (id: string, completed: boolean) => ({
			id,
			title: id,
			completed,
			position: id,
			action_label: null,
			action_icon: null,
			action_prompt: null,
			created_at: "",
		});
		const tasks = [
			makeTask({
				id: "t2",
				title: "T2",
				status: "in_progress",
				created_at: "2025-01-02T00:00:00Z",
				subtasks: [sub("s1", true), sub("s2", false)],
			}),
			makeTask({
				id: "t3",
				title: "T3",
				status: "not_started",
				created_at: "2025-01-03T00:00:00Z",
			}),
		];
		const edges: EdgeResponse[] = [{ source: "t2", target: "t3" }];
		render(<StepperView board={makeBoard(tasks, edges)} onSwitchToAdvanced={noop} />);
		expect(screen.getByTestId("step-task")).toHaveTextContent("T2");
		// Check the last remaining subtask -> task auto-completes and advances.
		fireEvent.click(screen.getByText("toggle-s2"));
		expect(updateSubtaskMutate).toHaveBeenCalledWith({
			subtaskId: "s2",
			data: { completed: true },
		});
		expect(updateMutate).toHaveBeenCalledWith({ taskId: "t2", data: { status: "done" } });
		expect(screen.getByTestId("step-task")).toHaveTextContent("T3");
	});

	it("does not auto-complete while subtasks remain unfinished", () => {
		const sub = (id: string, completed: boolean) => ({
			id,
			title: id,
			completed,
			position: id,
			action_label: null,
			action_icon: null,
			action_prompt: null,
			created_at: "",
		});
		const tasks = [
			makeTask({
				id: "t2",
				title: "T2",
				status: "in_progress",
				subtasks: [sub("s1", false), sub("s2", false)],
			}),
		];
		render(<StepperView board={makeBoard(tasks)} onSwitchToAdvanced={noop} />);
		fireEvent.click(screen.getByText("toggle-s1"));
		expect(updateSubtaskMutate).toHaveBeenCalledWith({
			subtaskId: "s1",
			data: { completed: true },
		});
		// s2 still open -> task is not auto-completed.
		expect(updateMutate).not.toHaveBeenCalled();
	});

	it("shows a completion screen when the board is complete", () => {
		const onSwitch = vi.fn();
		const tasks = [
			makeTask({ id: "t1", status: "done" }),
			makeTask({ id: "goal", status: "done", is_goal_node: true }),
		];
		render(
			<StepperView
				board={makeBoard(tasks, [], { is_completed: true })}
				onSwitchToAdvanced={onSwitch}
			/>,
		);
		expect(screen.getByText("All done!")).toBeInTheDocument();
		fireEvent.click(screen.getByText("View full DAG"));
		expect(onSwitch).toHaveBeenCalled();
		fireEvent.click(screen.getByText("Back to dashboard"));
		expect(navigateMock).toHaveBeenCalledWith({ to: "/" });
	});

	it("shows an empty-board fallback when there are no tasks", () => {
		render(<StepperView board={makeBoard([])} onSwitchToAdvanced={noop} />);
		expect(screen.getByText("No tasks yet")).toBeInTheDocument();
	});

	it("starts on a deep-linked task anywhere in the sequence", () => {
		render(<StepperView board={chainBoard()} focusTaskId="t4" onSwitchToAdvanced={noop} />);
		expect(screen.getByTestId("step-task")).toHaveTextContent("T4");
	});
});
