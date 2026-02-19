import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MemoryBadges } from "../components/MemoryBadges";

// Mock the generated API functions
vi.mock("@/api/generated/memories/memories", () => ({
	getGetMemoryByIdApiMemoriesMemoryIdGetQueryKey: (id: string) => [`/api/memories/${id}`],
	getMemoryByIdApiMemoriesMemoryIdGet: vi.fn(),
}));

// Mock TanStack Router navigation
vi.mock("@tanstack/react-router", () => ({
	useNavigate: () => vi.fn(),
}));

function createWrapper() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	return ({ children }: { children: React.ReactNode }) => (
		<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
	);
}

describe("MemoryBadges", () => {
	it("renders nothing when memoryIds is empty", () => {
		const { container } = render(<MemoryBadges memoryIds={[]} />, {
			wrapper: createWrapper(),
		});
		expect(container.firstChild).toBeNull();
	});

	it("renders badge buttons for each memory ID", () => {
		render(<MemoryBadges memoryIds={["mem-1", "mem-2", "mem-3"]} />, {
			wrapper: createWrapper(),
		});

		const buttons = screen.getAllByRole("button");
		expect(buttons).toHaveLength(3);
	});

	it("renders Memory placeholder text before resolution", () => {
		render(<MemoryBadges memoryIds={["mem-1"]} />, {
			wrapper: createWrapper(),
		});

		expect(screen.getByText("Memory")).toBeDefined();
	});
});
