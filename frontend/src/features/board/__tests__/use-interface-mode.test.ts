import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { INTERFACE_MODE_STORAGE_KEY, useInterfaceMode } from "../hooks/use-interface-mode";

afterEach(() => {
	window.localStorage.clear();
});

describe("useInterfaceMode", () => {
	it("defaults to advanced when nothing is stored", () => {
		const { result } = renderHook(() => useInterfaceMode());
		expect(result.current.mode).toBe("advanced");
	});

	it("reads a previously stored simple preference", () => {
		window.localStorage.setItem(INTERFACE_MODE_STORAGE_KEY, "simple");
		const { result } = renderHook(() => useInterfaceMode());
		expect(result.current.mode).toBe("simple");
	});

	it("persists the choice to localStorage", () => {
		const { result } = renderHook(() => useInterfaceMode());
		act(() => result.current.setMode("simple"));
		expect(result.current.mode).toBe("simple");
		expect(window.localStorage.getItem(INTERFACE_MODE_STORAGE_KEY)).toBe("simple");
	});

	it("treats unknown stored values as advanced", () => {
		window.localStorage.setItem(INTERFACE_MODE_STORAGE_KEY, "garbage");
		const { result } = renderHook(() => useInterfaceMode());
		expect(result.current.mode).toBe("advanced");
	});
});
