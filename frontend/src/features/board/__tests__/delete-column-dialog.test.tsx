import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DeleteColumnDialog } from "../components/DeleteColumnDialog";
import type { ColumnResponse } from "../types";

const column: ColumnResponse = {
	id: "col-1",
	title: "To Do",
	description: "",
	position: "a0",
	tasks: [
		{
			id: "t1",
			title: "Task 1",
			description: "",
			position: "a0",
			due_date: null,
			priority: null,
			estimated_minutes: null,
			subtasks: [],
			created_at: "",
		},
		{
			id: "t2",
			title: "Task 2",
			description: "",
			position: "a1",
			due_date: null,
			priority: null,
			estimated_minutes: null,
			subtasks: [],
			created_at: "",
		},
	],
	created_at: "",
};

const otherColumns: ColumnResponse[] = [
	{
		id: "col-2",
		title: "In Progress",
		description: "",
		position: "a1",
		tasks: [
			{
				id: "t3",
				title: "Task 3",
				description: "",
				position: "a0",
				due_date: null,
				priority: null,
				estimated_minutes: null,
				subtasks: [],
				created_at: "",
			},
		],
		created_at: "",
	},
	{
		id: "col-3",
		title: "Done",
		description: "",
		position: "a2",
		tasks: [],
		created_at: "",
	},
];

describe("DeleteColumnDialog", () => {
	it("shows task count and target column picker when column has tasks", () => {
		render(
			<DeleteColumnDialog
				column={column}
				otherColumns={otherColumns}
				onConfirm={vi.fn()}
				onCancel={vi.fn()}
			/>,
		);
		expect(screen.getByText(/2 tasks/)).toBeInTheDocument();
		expect(screen.getByText(/In Progress/)).toBeInTheDocument();
	});

	it("shows simple message when column is empty", () => {
		const emptyColumn = { ...column, tasks: [] };
		render(
			<DeleteColumnDialog
				column={emptyColumn}
				otherColumns={otherColumns}
				onConfirm={vi.fn()}
				onCancel={vi.fn()}
			/>,
		);
		expect(screen.getByText(/empty and will be permanently deleted/)).toBeInTheDocument();
	});

	it("calls onConfirm with target column id when column has tasks", () => {
		const onConfirm = vi.fn();
		render(
			<DeleteColumnDialog
				column={column}
				otherColumns={otherColumns}
				onConfirm={onConfirm}
				onCancel={vi.fn()}
			/>,
		);
		fireEvent.click(screen.getByText("Delete"));
		expect(onConfirm).toHaveBeenCalledWith("col-2"); // first other column
	});

	it("calls onConfirm with null when column is empty", () => {
		const onConfirm = vi.fn();
		const emptyColumn = { ...column, tasks: [] };
		render(
			<DeleteColumnDialog
				column={emptyColumn}
				otherColumns={otherColumns}
				onConfirm={onConfirm}
				onCancel={vi.fn()}
			/>,
		);
		fireEvent.click(screen.getByText("Delete"));
		expect(onConfirm).toHaveBeenCalledWith(null);
	});

	it("calls onCancel when Cancel is clicked", () => {
		const onCancel = vi.fn();
		render(
			<DeleteColumnDialog
				column={column}
				otherColumns={otherColumns}
				onConfirm={vi.fn()}
				onCancel={onCancel}
			/>,
		);
		fireEvent.click(screen.getByText("Cancel"));
		expect(onCancel).toHaveBeenCalled();
	});
});
