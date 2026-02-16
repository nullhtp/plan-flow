import { createRoute, useNavigate } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { useAuth, useLogout } from "@/features/auth/hooks/use-auth";
import { BoardCard } from "@/features/board/components/BoardCard";
import { useBoardListData } from "@/features/board/hooks/use-board-list";
import { authenticatedRoute } from "./_authenticated";

export const indexRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/",
	component: IndexPage,
});

function IndexPage() {
	const { user } = useAuth();
	const logout = useLogout();
	const navigate = useNavigate();
	const boards = useBoardListData();

	return (
		<div className="flex min-h-screen flex-col">
			{/* Header */}
			<header className="flex items-center justify-between border-b px-6 py-4">
				<h1 className="text-2xl font-bold">PlanFlow</h1>
				<div className="flex items-center gap-3">
					{user && <span className="text-sm text-muted-foreground">{user.email}</span>}
					<Button onClick={() => navigate({ to: "/goals/new" })}>New Goal</Button>
					<Button variant="outline" onClick={() => logout.mutate()} disabled={logout.isPending}>
						{logout.isPending ? "Logging out..." : "Log out"}
					</Button>
				</div>
			</header>

			{/* Board List */}
			<main className="flex-1 p-6">
				{boards.length > 0 ? (
					<div>
						<h2 className="mb-4 text-lg font-semibold">Your Boards</h2>
						<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
							{boards.map((board) => (
								<BoardCard key={board.id} board={board} />
							))}
						</div>
					</div>
				) : (
					<div className="flex flex-col items-center justify-center gap-4 py-20">
						<p className="text-muted-foreground">No boards yet. Create a goal to get started.</p>
						<Button onClick={() => navigate({ to: "/goals/new" })}>New Goal</Button>
					</div>
				)}
			</main>
		</div>
	);
}
