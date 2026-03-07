import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

// Mock navigation
vi.mock("@tanstack/react-router", () => ({
	useNavigate: () => vi.fn(),
}));

// Mock hooks
vi.mock("../hooks/use-categories", () => ({
	useCategoriesData: () => [
		{ id: "cat-1", name: "Travel", slug: "travel", template_count: 0 },
	],
}));

vi.mock("../hooks/use-template-generation", () => ({
	useExtractContent: () => ({ mutateAsync: vi.fn(), isPending: false }),
	useGenerateTemplate: () => ({ mutateAsync: vi.fn(), isPending: false }),
	useSaveGeneratedTemplate: () => ({
		mutateAsync: vi.fn(),
		isPending: false,
	}),
}));

import { GenerateTemplateDialog } from "../components/GenerateTemplateDialog";

function wrapper({ children }: { children: React.ReactNode }) {
	const qc = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("GenerateTemplateDialog", () => {
	it("renders nothing when closed", () => {
		const { container } = render(
			<GenerateTemplateDialog open={false} onClose={vi.fn()} />,
			{ wrapper },
		);
		expect(container.firstChild).toBeNull();
	});

	it("renders input step when open", () => {
		render(
			<GenerateTemplateDialog open={true} onClose={vi.fn()} />,
			{ wrapper },
		);
		expect(screen.getByText("Generate Template")).toBeInTheDocument();
		expect(screen.getByText("Generate")).toBeInTheDocument();
	});

	it("shows three input tabs", () => {
		render(
			<GenerateTemplateDialog open={true} onClose={vi.fn()} />,
			{ wrapper },
		);
		expect(screen.getByText("text")).toBeInTheDocument();
		expect(screen.getByText("document")).toBeInTheDocument();
		expect(screen.getByText("url")).toBeInTheDocument();
	});

	it("disables Generate button when text is too short", () => {
		render(
			<GenerateTemplateDialog open={true} onClose={vi.fn()} />,
			{ wrapper },
		);
		const generateButton = screen.getByText("Generate");
		expect(generateButton).toBeDisabled();
	});

	it("switches tabs on click", async () => {
		const user = userEvent.setup();
		render(
			<GenerateTemplateDialog open={true} onClose={vi.fn()} />,
			{ wrapper },
		);
		await user.click(screen.getByText("url"));
		expect(screen.getByPlaceholderText(/example\.com/)).toBeInTheDocument();
	});
});
