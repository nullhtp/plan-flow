import { useCallback, useState } from "react";

export type InterfaceMode = "simple" | "advanced";

/**
 * localStorage key for the per-session board interface preference. This control
 * is only consulted while the global Simple mode setting is OFF (see board-ui
 * spec: Interface Mode Selection); it lets a power user preview the stepper for a
 * board without changing their global setting.
 */
export const INTERFACE_MODE_STORAGE_KEY = "planflow:board-interface-mode";

function readStoredMode(): InterfaceMode {
	if (typeof window === "undefined") return "advanced";
	try {
		return window.localStorage.getItem(INTERFACE_MODE_STORAGE_KEY) === "simple"
			? "simple"
			: "advanced";
	} catch {
		// Storage may be unavailable (private mode, blocked cookies, etc.)
		return "advanced";
	}
}

/**
 * Reads and persists the per-session board interface preference used only while
 * global Simple mode is OFF. Defaults to "advanced" (the DAG) when no preference
 * is stored.
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
