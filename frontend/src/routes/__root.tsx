import { createRootRoute, Outlet } from "@tanstack/react-router";
import { Toaster } from "sonner";

export const rootRoute = createRootRoute({
	component: RootLayout,
});

function RootLayout() {
	return (
		<>
			<Outlet />
			<Toaster position="bottom-right" />
		</>
	);
}
