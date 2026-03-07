import { createRouter } from "@tanstack/react-router";
import { rootRoute } from "./__root";
import { authenticatedRoute } from "./_authenticated";
import { boardDetailRoute } from "./boards.$boardId";
import { boardExpandTaskRoute } from "./boards.$boardId.expand.$taskId";
import { goalDetailRoute } from "./goals.$goalId";
import { goalsNewRoute } from "./goals.new";
import { indexRoute } from "./index";
import { joinRoute } from "./join";
import { loginRoute } from "./login";
import { registerRoute } from "./register";
import { settingsRoute } from "./settings";
import { templateDetailRoute } from "./templates.$templateId";
import { templatesRoute } from "./templates";

const routeTree = rootRoute.addChildren([
	loginRoute,
	registerRoute,
	authenticatedRoute.addChildren([
		indexRoute,
		joinRoute,
		goalsNewRoute,
		goalDetailRoute,
		boardDetailRoute,
		boardExpandTaskRoute,
		settingsRoute,
		templatesRoute,
		templateDetailRoute,
	]),
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
	interface Register {
		router: typeof router;
	}
}
