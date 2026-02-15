import { createRoute, Navigate, Outlet, useLocation } from "@tanstack/react-router";
import { useAuth } from "@/features/auth/hooks/use-auth";
import { rootRoute } from "./__root";

export const authenticatedRoute = createRoute({
	id: "_authenticated",
	getParentRoute: () => rootRoute,
	component: AuthenticatedLayout,
});

function AuthenticatedLayout() {
	const { isAuthenticated, isLoading } = useAuth();
	const location = useLocation();

	if (isLoading) {
		return (
			<div className="flex min-h-screen items-center justify-center">
				<p className="text-muted-foreground">Loading...</p>
			</div>
		);
	}

	if (!isAuthenticated) {
		return <Navigate to="/login" search={{ returnTo: location.pathname }} />;
	}

	return <Outlet />;
}
