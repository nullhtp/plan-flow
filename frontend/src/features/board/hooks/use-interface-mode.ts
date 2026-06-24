import { useCallback, useState } from "react";

export type InterfaceMode = "simple" | "advanced";

/**
 * localStorage key for the global board interface preference. The choice applies
 * to every board and persists across sessions (see board-ui spec: Interface Mode
 * Selection).
 */
export const INTERFACE_MODE_STORAGE_KEY = "planflow:board-interface-mode";

function readStoredMode(): InterfaceMode {
	if (typeof window === "undefined") return "simple";
	try {
		return window.localStorage.getItem(INTERFACE_MODE_STORAGE_KEY) === "advanced"
			? "advanced"
			: "simple";
	} catch {
		// Storage may be unavailable (private mode, blocked cookies, etc.)
		return "simple";
	}
}

/**
 * Reads and persists the user's global board interface preference. Defaults to
 * "simple" (the guided stepper) when no preference is stored.
 */
export function useInterfaceMode() {
	const [mode, setModeState] = useState<InterfaceMode>(readStoredMode);

	const setMode = useCallback((next: InterfaceMode) => {
		setModeState(next);
		try {
			window.localStorage.setItem(INTERFACE_MODE_STORAGE_KEY, next);
		} catch {
			// Ignore storage write failures; the in-memory state still updates.
		}
	}, []);

	return { mode, setMode };
}
