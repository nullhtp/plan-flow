import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./app";

describe("App", () => {
	it("renders the application", async () => {
		render(<App />);
		await waitFor(() => {
			expect(screen.getByText("PlanFlow")).toBeInTheDocument();
		});
	});
});
