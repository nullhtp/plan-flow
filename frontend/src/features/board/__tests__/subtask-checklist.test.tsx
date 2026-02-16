import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SubtaskChecklist } from "../components/SubtaskChecklist";
import type { SubtaskResponse } from "../types";

const mockSubtasks: SubtaskResponse[] = [
	{ id: "s1", title: "Research", completed: false, position: "a0", created_at: "" },
	{ id: "s2", title: "Design", completed: true, position: "a1", created_at: "" },
	{ id: "s3", title: "Implement", completed: false, position: "a2", created_at: "" },
];

describe("SubtaskChecklist", () => {
	it("renders all subtasks", () => {
		render(
			<SubtaskChecklist
				subtasks={mockSubtasks}
				onToggle={vi.fn()}
				onAdd={vi.fn()}
				onDelete={vi.fn()}
			/>,
		);
		expect(screen.getByText("Research")).toBeInTheDocument();
		expect(screen.getByText("Design")).toBeInTheDocument();
		expect(screen.getByText("Implement")).toBeInTheDocument();
	});

	it("renders checkboxes with correct state", () => {
		render(
			<SubtaskChecklist
				subtasks={mockSubtasks}
				onToggle={vi.fn()}
				onAdd={vi.fn()}
				onDelete={vi.fn()}
			/>,
		);
		const checkboxes = screen.getAllByRole("checkbox");
		expect(checkboxes[0]).not.toBeChecked();
		expect(checkboxes[1]).toBeChecked();
		expect(checkboxes[2]).not.toBeChecked();
	});

	it("calls onToggle when checkbox is clicked", () => {
		const onToggle = vi.fn();
		render(
			<SubtaskChecklist
				subtasks={mockSubtasks}
				onToggle={onToggle}
				onAdd={vi.fn()}
				onDelete={vi.fn()}
			/>,
		);
		const checkboxes = screen.getAllByRole("checkbox");
		fireEvent.click(checkboxes[0]);
		expect(onToggle).toHaveBeenCalledWith("s1", true);
	});

	it("renders add subtask input", () => {
		render(
			<SubtaskChecklist subtasks={[]} onToggle={vi.fn()} onAdd={vi.fn()} onDelete={vi.fn()} />,
		);
		expect(screen.getByPlaceholderText("Add subtask...")).toBeInTheDocument();
	});

	it("calls onAdd when Enter is pressed in input", () => {
		const onAdd = vi.fn();
		render(<SubtaskChecklist subtasks={[]} onToggle={vi.fn()} onAdd={onAdd} onDelete={vi.fn()} />);
		const input = screen.getByPlaceholderText("Add subtask...");
		fireEvent.change(input, { target: { value: "New subtask" } });
		fireEvent.keyDown(input, { key: "Enter" });
		expect(onAdd).toHaveBeenCalledWith("New subtask");
	});
});
