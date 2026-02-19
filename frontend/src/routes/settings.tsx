import { createRoute } from "@tanstack/react-router";
import { SettingsPage } from "@/features/settings/components/SettingsPage";
import { authenticatedRoute } from "./_authenticated";

export const settingsRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/settings",
	component: SettingsPage,
});
