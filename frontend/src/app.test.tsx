import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./app";

describe("App", () => {
	it("renders the login page when unauthenticated", async () => {
		render(<App />);
		await waitFor(() => {
			expect(screen.getByRole("button", { name: "Log in" })).toBeInTheDocument();
		});
	});
});
