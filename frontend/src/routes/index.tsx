import { createRoute } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { useAuth, useLogout } from "@/features/auth/hooks/use-auth";
import { authenticatedRoute } from "./_authenticated";

export const indexRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/",
	component: IndexPage,
});

function IndexPage() {
	const { user } = useAuth();
	const logout = useLogout();

	return (
		<div className="flex min-h-screen flex-col items-center justify-center gap-4">
			<h1 className="text-4xl font-bold">PlanFlow</h1>
			{user && <p className="text-muted-foreground">Logged in as {user.email}</p>}
			<Button variant="outline" onClick={() => logout.mutate()} disabled={logout.isPending}>
				{logout.isPending ? "Logging out..." : "Log out"}
			</Button>
		</div>
	);
}
