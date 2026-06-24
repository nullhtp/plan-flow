import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@tanstack/react-router", () => ({
	useNavigate: () => vi.fn(),
}));

const patchMutate = vi.fn();

vi.mock("@/api/generated/settings/settings", () => ({
	getGetSettingsApiSettingsGetQueryKey: () => ["/api/settings"],
	useGetSettingsApiSettingsGet: vi.fn(),
	usePatchSettingsApiSettingsPatch: () => ({ mutate: patchMutate, isPending: false }),
}));

vi.mock("@/api/generated/memories/memories", () => ({
	getGetMemoriesApiMemoriesGetQueryKey: () => ["/api/memories"],
	getGetStatsApiMemoriesStatsGetQueryKey: () => ["/api/memories/stats"],
	useGetMemoriesApiMemoriesGet: () => ({ data: { data: { items: [], total: 0 } } }),
	useGetStatsApiMemoriesStatsGet: () => ({
		data: { data: { total: 3, by_category: { fact: 3 } } },
	}),
	usePatchMemoryApiMemoriesMemoryIdPatch: () => ({ mutate: vi.fn(), isPending: false }),
	useDeleteMemoryByIdApiMemoriesMemoryIdDelete: () => ({ mutate: vi.fn(), isPending: false }),
	useBulkDeleteApiMemoriesDelete: () => ({ mutate: vi.fn(), isPending: false }),
}));

import { useGetSettingsApiSettingsGet } from "@/api/generated/settings/settings";
import { SettingsPage } from "../components/SettingsPage";

const mockedUseGetSettings = vi.mocked(useGetSettingsApiSettingsGet);

function setSettings(simpleMode: boolean) {
	mockedUseGetSettings.mockReturnValue({
		data: {
			data: { memory_enabled: true, simple_mode: simpleMode },
			status: 200,
			headers: new Headers(),
		},
		isLoading: false,
	} as ReturnType<typeof useGetSettingsApiSettingsGet>);
}

function renderPage() {
	const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
	return render(
		<QueryClientProvider client={queryClient}>
			<SettingsPage />
		</QueryClientProvider>,
	);
}

describe("SettingsPage Simple mode", () => {
	it("hides memory management when Simple mode is on", () => {
		setSettings(true);
		renderPage();
		expect(screen.getByText("Simple mode")).toBeInTheDocument();
		expect(screen.getByText("AI Memory")).toBeInTheDocument();
		// Memory management UI is hidden.
		expect(screen.queryByText("Memory Statistics")).not.toBeInTheDocument();
		expect(screen.queryByPlaceholderText("Search memories...")).not.toBeInTheDocument();
		expect(screen.queryByText("Clear All Memories")).not.toBeInTheDocument();
	});

	it("shows full memory management when Simple mode is off", () => {
		setSettings(false);
		renderPage();
		expect(screen.getByText("Memory Statistics")).toBeInTheDocument();
		expect(screen.getByPlaceholderText("Search memories...")).toBeInTheDocument();
		expect(screen.getByText("Clear All Memories")).toBeInTheDocument();
	});

	it("toggling the Simple mode switch patches the setting", () => {
		setSettings(true);
		renderPage();
		// The Simple mode card's toggle button reads "Enabled" when on.
		const buttons = screen.getAllByRole("button", { name: "Enabled" });
		fireEvent.click(buttons[0]);
		expect(patchMutate).toHaveBeenCalledWith({ data: { simple_mode: false } }, expect.anything());
	});
});
