import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const mockNavigate = vi.fn();
vi.mock("@tanstack/react-router", () => ({
	useNavigate: () => mockNavigate,
}));

import { BreadcrumbNav } from "../components/BreadcrumbNav";

describe("BreadcrumbNav", () => {
	it("renders 2 segments for a root board (Home > Board Title)", () => {
		render(<BreadcrumbNav boardTitle="My Board" />);
		expect(screen.getByText("Home")).toBeInTheDocument();
		expect(screen.getByText("My Board")).toBeInTheDocument();
	});

	it("renders 3 segments for a sub-board (Home > Parent > Current)", () => {
		render(
			<BreadcrumbNav
				boardTitle="Sub Board"
				parentBoard={{ id: "parent-123", title: "Parent Board" }}
			/>,
		);
		expect(screen.getByText("Home")).toBeInTheDocument();
		expect(screen.getByText("Parent Board")).toBeInTheDocument();
		expect(screen.getByText("Sub Board")).toBeInTheDocument();
	});

	it("does not render parent segment when parentBoard is null", () => {
		render(<BreadcrumbNav boardTitle="Root Board" parentBoard={null} />);
		expect(screen.getByText("Home")).toBeInTheDocument();
		expect(screen.getByText("Root Board")).toBeInTheDocument();
		// Only 2 segments: Home and current board
		const nav = screen.getByRole("navigation");
		const buttons = nav.querySelectorAll("button");
		expect(buttons).toHaveLength(1); // Only Home is a button
	});

	it("truncates long titles with ellipsis", () => {
		const longTitle = "A".repeat(50);
		render(<BreadcrumbNav boardTitle={longTitle} />);
		// Default max length is 40, so it should be truncated
		const truncated = `${"A".repeat(40)}...`;
		expect(screen.getByText(truncated)).toBeInTheDocument();
	});

	it("does not truncate titles at or under 40 characters", () => {
		const shortTitle = "A".repeat(40);
		render(<BreadcrumbNav boardTitle={shortTitle} />);
		expect(screen.getByText(shortTitle)).toBeInTheDocument();
	});

	it("truncates long parent board titles", () => {
		const longParentTitle = "B".repeat(50);
		render(
			<BreadcrumbNav boardTitle="Current" parentBoard={{ id: "p-1", title: longParentTitle }} />,
		);
		const truncated = `${"B".repeat(40)}...`;
		expect(screen.getByText(truncated)).toBeInTheDocument();
		// Full title should be in the title attribute for tooltip
		const parentButton = screen.getByTitle(longParentTitle);
		expect(parentButton).toBeInTheDocument();
	});
});
