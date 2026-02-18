import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SubtaskChecklist } from "../components/SubtaskChecklist";
import type { SubtaskResponse } from "../types";

const mockSubtasks: SubtaskResponse[] = [
	{
		id: "s1",
		title: "Research",
		completed: false,
		position: "a0",
		action_label: "Research this",
		action_icon: "research",
		action_prompt: "Find information about this topic",
		created_at: "",
	},
	{
		id: "s2",
		title: "Design",
		completed: true,
		position: "a1",
		action_label: null,
		action_icon: null,
		action_prompt: null,
		created_at: "",
	},
	{
		id: "s3",
		title: "Implement",
		completed: false,
		position: "a2",
		action_label: null,
		action_icon: null,
		action_prompt: null,
		created_at: "",
	},
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

	it("renders action button for subtask with action_prompt", () => {
		const onActionClick = vi.fn();
		render(
			<SubtaskChecklist
				subtasks={mockSubtasks}
				onToggle={vi.fn()}
				onAdd={vi.fn()}
				onDelete={vi.fn()}
				onActionClick={onActionClick}
			/>,
		);
		// The first subtask has an action — look for a button with the action label as title
		const actionButton = screen.getByTitle("Research this");
		expect(actionButton).toBeInTheDocument();
	});

	it("calls onActionClick with subtask context when action button is clicked", () => {
		const onActionClick = vi.fn();
		render(
			<SubtaskChecklist
				subtasks={mockSubtasks}
				onToggle={vi.fn()}
				onAdd={vi.fn()}
				onDelete={vi.fn()}
				onActionClick={onActionClick}
			/>,
		);
		const actionButton = screen.getByTitle("Research this");
		fireEvent.click(actionButton);
		expect(onActionClick).toHaveBeenCalledWith(
			"Help me with subtask: Research -- Find information about this topic",
		);
	});

	it("does not render action button for subtask without action_prompt", () => {
		render(
			<SubtaskChecklist
				subtasks={mockSubtasks}
				onToggle={vi.fn()}
				onAdd={vi.fn()}
				onDelete={vi.fn()}
				onActionClick={vi.fn()}
			/>,
		);
		// Only 1 action button (for "Research"), not 3
		const actionButtons = screen.getAllByTitle(/./);
		const aiButtons = actionButtons.filter((btn) => btn.getAttribute("title") === "Research this");
		expect(aiButtons).toHaveLength(1);
	});
});
