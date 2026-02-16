import { DndContext } from "@dnd-kit/core";
import { SortableContext } from "@dnd-kit/sortable";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TaskCard } from "../components/TaskCard";
import type { TaskResponse } from "../types";

function renderTaskCard(task: TaskResponse) {
	return render(
		<DndContext>
			<SortableContext items={[task.id]}>
				<TaskCard task={task} onClick={vi.fn()} />
			</SortableContext>
		</DndContext>,
	);
}

const baseTask: TaskResponse = {
	id: "task-1",
	title: "Test Task",
	description: "A test task",
	position: "a0",
	due_date: null,
	priority: null,
	estimated_minutes: null,
	subtasks: [],
	created_at: "2026-01-01T00:00:00Z",
};

describe("TaskCard", () => {
	it("renders task title", () => {
		renderTaskCard(baseTask);
		expect(screen.getByText("Test Task")).toBeInTheDocument();
	});

	it("renders priority indicator when set", () => {
		renderTaskCard({ ...baseTask, priority: "high" });
		const indicator = screen.getByTitle("high");
		expect(indicator).toBeInTheDocument();
	});

	it("renders due date when set", () => {
		renderTaskCard({ ...baseTask, due_date: "2026-03-15" });
		expect(screen.getByText("2026-03-15")).toBeInTheDocument();
	});

	it("renders time estimate when set", () => {
		renderTaskCard({ ...baseTask, estimated_minutes: 60 });
		expect(screen.getByText("60m")).toBeInTheDocument();
	});

	it("renders subtask progress when subtasks exist", () => {
		renderTaskCard({
			...baseTask,
			subtasks: [
				{ id: "s1", title: "Sub 1", completed: true, position: "a0", created_at: "" },
				{ id: "s2", title: "Sub 2", completed: false, position: "a1", created_at: "" },
			],
		});
		expect(screen.getByText("1/2")).toBeInTheDocument();
	});

	it("does not render metadata when not set", () => {
		renderTaskCard(baseTask);
		expect(screen.queryByText(/\d+m/)).not.toBeInTheDocument();
		expect(screen.queryByText(/\d+\/\d+/)).not.toBeInTheDocument();
	});
});
