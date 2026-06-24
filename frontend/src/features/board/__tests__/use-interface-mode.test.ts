import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { INTERFACE_MODE_STORAGE_KEY, useInterfaceMode } from "../hooks/use-interface-mode";

afterEach(() => {
	window.localStorage.clear();
});

describe("useInterfaceMode", () => {
	it("defaults to simple when nothing is stored", () => {
		const { result } = renderHook(() => useInterfaceMode());
		expect(result.current.mode).toBe("simple");
	});

	it("reads a previously stored advanced preference", () => {
		window.localStorage.setItem(INTERFACE_MODE_STORAGE_KEY, "advanced");
		const { result } = renderHook(() => useInterfaceMode());
		expect(result.current.mode).toBe("advanced");
	});

	it("persists the choice to localStorage", () => {
		const { result } = renderHook(() => useInterfaceMode());
		act(() => result.current.setMode("advanced"));
		expect(result.current.mode).toBe("advanced");
		expect(window.localStorage.getItem(INTERFACE_MODE_STORAGE_KEY)).toBe("advanced");
	});

	it("treats unknown stored values as simple", () => {
		window.localStorage.setItem(INTERFACE_MODE_STORAGE_KEY, "garbage");
		const { result } = renderHook(() => useInterfaceMode());
		expect(result.current.mode).toBe("simple");
	});
});
