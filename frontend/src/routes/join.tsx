import { createRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useJoinBoard } from "@/features/board/hooks/use-share";
import { authenticatedRoute } from "./_authenticated";

type JoinSearchParams = {
	token?: string;
};

export const joinRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/join",
	component: JoinPage,
	validateSearch: (search: Record<string, unknown>): JoinSearchParams => ({
		token: typeof search.token === "string" ? search.token : undefined,
	}),
});

function JoinPage() {
	const { token } = joinRoute.useSearch();
	const navigate = useNavigate();
	const joinBoard = useJoinBoard();

	useEffect(() => {
		if (!token) return;
		joinBoard.mutate(token, {
			onSuccess: (data) => {
				navigate({ to: "/boards/$boardId", params: { boardId: data.board_id } });
			},
		});
	}, [token, joinBoard.mutate, navigate]);

	if (!token) {
		return (
			<div className="flex min-h-screen items-center justify-center">
				<p className="text-muted-foreground">Invalid share link — no token provided.</p>
			</div>
		);
	}

	if (joinBoard.isPending) {
		return (
			<div className="flex min-h-screen items-center justify-center">
				<p className="text-muted-foreground">Joining board...</p>
			</div>
		);
	}

	if (joinBoard.isError) {
		return (
			<div className="flex min-h-screen flex-col items-center justify-center gap-3">
				<p className="text-destructive">
					Failed to join board. The link may be invalid or expired.
				</p>
				<button type="button" className="text-sm underline" onClick={() => navigate({ to: "/" })}>
					Go to dashboard
				</button>
			</div>
		);
	}

	return null;
}
