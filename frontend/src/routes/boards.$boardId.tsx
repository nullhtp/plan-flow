import { createRoute } from "@tanstack/react-router";
import type { BoardResponse } from "@/api/generated/model";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorDisplay } from "@/features/goals/components/error-display";
import { LoadingState } from "@/features/goals/components/loading-state";
import { useBoard } from "@/features/goals/hooks/use-goals";
import { authenticatedRoute } from "./_authenticated";

export const boardDetailRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/boards/$boardId",
	component: BoardDetailPage,
});

function BoardDetailPage() {
	const { boardId } = boardDetailRoute.useParams();
	const boardQuery = useBoard(boardId);

	if (boardQuery.isLoading) {
		return (
			<div className="flex min-h-screen items-center justify-center p-4">
				<LoadingState message="Loading board..." />
			</div>
		);
	}

	if (boardQuery.isError || !boardQuery.data) {
		return (
			<div className="flex min-h-screen items-center justify-center p-4">
				<ErrorDisplay
					message="Could not load this board."
					onRetry={() => boardQuery.refetch()}
					isRetrying={boardQuery.isRefetching}
				/>
			</div>
		);
	}

	const board = boardQuery.data.data as BoardResponse;

	return (
		<div className="flex min-h-screen items-center justify-center p-4">
			<Card className="w-full max-w-2xl">
				<CardHeader>
					<CardTitle className="text-2xl">{board.title}</CardTitle>
					<p className="text-sm text-muted-foreground">
						{board.columns.length} columns,{" "}
						{board.columns.reduce((sum, col) => sum + col.tasks.length, 0)} tasks
					</p>
				</CardHeader>
				<CardContent>
					<p className="text-center text-sm text-muted-foreground">
						Board view coming soon. Your board has been generated successfully.
					</p>
				</CardContent>
			</Card>
		</div>
	);
}
