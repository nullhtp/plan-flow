import { createRouter } from "@tanstack/react-router";
import { rootRoute } from "./__root";
import { authenticatedRoute } from "./_authenticated";
import { boardDetailRoute } from "./boards.$boardId";
import { boardExpandTaskRoute } from "./boards.$boardId.expand.$taskId";
import { goalDetailRoute } from "./goals.$goalId";
import { goalsNewRoute } from "./goals.new";
import { indexRoute } from "./index";
import { loginRoute } from "./login";
import { registerRoute } from "./register";

const routeTree = rootRoute.addChildren([
	loginRoute,
	registerRoute,
	authenticatedRoute.addChildren([
		indexRoute,
		goalsNewRoute,
		goalDetailRoute,
		boardDetailRoute,
		boardExpandTaskRoute,
	]),
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
	interface Register {
		router: typeof router;
	}
}
