import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const navigateMock = vi.fn();
const isSimpleModeMock = vi.fn();

vi.mock("@tanstack/react-router", () => ({
	useNavigate: () => navigateMock,
}));
vi.mock("@/shared/hooks/use-simple-mode", () => ({
	useSimpleMode: () => ({ isSimpleMode: isSimpleModeMock(), isLoading: false }),
}));
vi.mock("../hooks/use-categories", () => ({ useCategoriesData: () => [] }));
vi.mock("../hooks/use-templates", () => ({
	useTemplates: () => ({
		data: {
			items: [
				{
					id: "t1",
					title: "SaaS Launch",
					description: "A plan",
					category: null,
					task_count: 5,
					creator: { id: "u1", email: "a@b.com" },
				},
			],
			total: 1,
			page: 1,
			total_pages: 1,
		},
		isLoading: false,
	}),
}));
vi.mock("../hooks/use-template-mutations", () => ({
	useCreateBoardFromTemplate: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

import { TemplatesGallery } from "../components/TemplatesGallery";

describe("TemplatesGallery Simple mode", () => {
	it("shows authoring and opens the editor when Simple mode is off", () => {
		isSimpleModeMock.mockReturnValue(false);
		render(<TemplatesGallery />);
		expect(screen.getByText("Create Template")).toBeInTheDocument();

		fireEvent.click(screen.getByText("SaaS Launch"));
		expect(navigateMock).toHaveBeenCalledWith({
			to: "/templates/$templateId",
			params: { templateId: "t1" },
		});
	});

	it("hides authoring and opens the create-board dialog when Simple mode is on", () => {
		isSimpleModeMock.mockReturnValue(true);
		navigateMock.mockClear();
		render(<TemplatesGallery />);
		expect(screen.queryByText("Create Template")).not.toBeInTheDocument();

		fireEvent.click(screen.getByText("SaaS Launch"));
		// Opens the "Use Template" create-board dialog instead of the editor.
		expect(screen.getByText("Use Template")).toBeInTheDocument();
		expect(navigateMock).not.toHaveBeenCalled();
	});
});
