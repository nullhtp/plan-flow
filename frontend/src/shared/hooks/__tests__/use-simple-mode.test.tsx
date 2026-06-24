import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/api/generated/settings/settings", () => ({
	useGetSettingsApiSettingsGet: vi.fn(),
}));

import { useGetSettingsApiSettingsGet } from "@/api/generated/settings/settings";
import { useSimpleMode } from "../use-simple-mode";

const mockedUseGetSettings = vi.mocked(useGetSettingsApiSettingsGet);

describe("useSimpleMode", () => {
	it("defaults to simple while the settings query is loading", () => {
		mockedUseGetSettings.mockReturnValue({
			data: undefined,
			isLoading: true,
		} as ReturnType<typeof useGetSettingsApiSettingsGet>);

		const { result } = renderHook(() => useSimpleMode());
		expect(result.current.isSimpleMode).toBe(true);
		expect(result.current.isLoading).toBe(true);
	});

	it("returns false when the stored setting is false", () => {
		mockedUseGetSettings.mockReturnValue({
			data: {
				data: { memory_enabled: true, simple_mode: false },
				status: 200,
				headers: new Headers(),
			},
			isLoading: false,
		} as ReturnType<typeof useGetSettingsApiSettingsGet>);

		const { result } = renderHook(() => useSimpleMode());
		expect(result.current.isSimpleMode).toBe(false);
	});

	it("returns true when the stored setting is true", () => {
		mockedUseGetSettings.mockReturnValue({
			data: {
				data: { memory_enabled: true, simple_mode: true },
				status: 200,
				headers: new Headers(),
			},
			isLoading: false,
		} as ReturnType<typeof useGetSettingsApiSettingsGet>);

		const { result } = renderHook(() => useSimpleMode());
		expect(result.current.isSimpleMode).toBe(true);
	});
});
