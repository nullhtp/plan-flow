import { createRoute, Navigate, Outlet, useLocation } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/features/auth/hooks/use-auth";
import { rootRoute } from "./__root";

export const authenticatedRoute = createRoute({
	id: "_authenticated",
	getParentRoute: () => rootRoute,
	component: AuthenticatedLayout,
});

function AuthenticatedLayout() {
	const { t } = useTranslation("common");
	const { isAuthenticated, isLoading } = useAuth();
	const location = useLocation();

	if (isLoading) {
		return (
			<div className="flex min-h-screen items-center justify-center">
				<p className="text-muted-foreground">{t("loading")}</p>
			</div>
		);
	}

	if (!isAuthenticated) {
		// Only set returnTo for actual protected pages, not for /login or /register
		const returnTo =
			location.pathname === "/login" || location.pathname === "/register" ? "/" : location.pathname;
		return <Navigate to="/login" search={{ returnTo }} />;
	}

	return <Outlet />;
}
