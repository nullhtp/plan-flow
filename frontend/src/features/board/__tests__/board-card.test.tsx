import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@tanstack/react-router", () => ({
	useNavigate: () => vi.fn(),
}));

import type { BoardListResponse } from "@/features/board/types";
import { BoardCard } from "../components/BoardCard";

const board = {
	id: "b1",
	title: "Move to Lisbon",
	goal_title: "Relocate abroad",
	role: "owner",
	task_count: 4,
	completed_task_count: 1,
} as unknown as BoardListResponse;

describe("BoardCard", () => {
	it("shows goal subtitle, task counts and progress bar in the full variant", () => {
		const { container } = render(<BoardCard board={board} />);
		expect(screen.getByText("Relocate abroad")).toBeInTheDocument();
		expect(screen.getByText("1/4 tasks")).toBeInTheDocument();
		expect(screen.getByText("25% complete")).toBeInTheDocument();
		// Progress bar track element is present.
		expect(container.querySelector(".bg-muted")).not.toBeNull();
	});

	it("hides subtitle, counts and progress bar in the simple variant", () => {
		const { container } = render(<BoardCard board={board} simple />);
		expect(screen.getByText("Move to Lisbon")).toBeInTheDocument();
		expect(screen.getByText("25% done")).toBeInTheDocument();
		expect(screen.queryByText("Relocate abroad")).not.toBeInTheDocument();
		expect(screen.queryByText("1/4 tasks")).not.toBeInTheDocument();
		expect(container.querySelector(".bg-muted")).toBeNull();
	});
});
