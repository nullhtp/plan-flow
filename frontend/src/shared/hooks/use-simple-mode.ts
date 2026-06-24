import type { UserSettingsResponse } from "@/api/generated/model";
import { useGetSettingsApiSettingsGet } from "@/api/generated/settings/settings";

export interface UseSimpleModeResult {
	/** Whether the simplified, guided interface is active. Defaults to `true`. */
	isSimpleMode: boolean;
	/** True while the settings query is still resolving. */
	isLoading: boolean;
}

/**
 * Single source of truth for the global Simple mode preference (server-persisted
 * on `UserSettings.simple_mode`). Every screen derives its simplified-vs-full
 * rendering from this hook.
 *
 * While the settings query is loading — or if the value is somehow absent — this
 * defaults to `true` so the app never flashes advanced UI (e.g. the board DAG)
 * before the preference resolves.
 */
export function useSimpleMode(): UseSimpleModeResult {
	const settingsQuery = useGetSettingsApiSettingsGet();
	const settings = settingsQuery.data?.data as UserSettingsResponse | undefined;
	const isSimpleMode = settings?.simple_mode ?? true;
	return { isSimpleMode, isLoading: settingsQuery.isLoading };
}
