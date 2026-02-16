import { createRoute, useNavigate } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import { type KeyboardEvent, useState } from "react";
import { useUpdateBoardEndpointApiBoardsBoardIdPatch } from "@/api/generated/boards/boards";
import type { BoardResponse } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { BoardSkeleton } from "@/features/board/components/BoardSkeleton";
import { BoardView } from "@/features/board/components/BoardView";
import { useBoard } from "@/features/board/hooks/use-board";
import { ErrorDisplay } from "@/features/goals/components/error-display";
import { authenticatedRoute } from "./_authenticated";

type BoardSearchParams = {
	task?: string;
};

export const boardDetailRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/boards/$boardId",
	component: BoardDetailPage,
	validateSearch: (search: Record<string, unknown>): BoardSearchParams => ({
		task: typeof search.task === "string" ? search.task : undefined,
	}),
});

function BoardDetailPage() {
	const { boardId } = boardDetailRoute.useParams();
	const boardQuery = useBoard(boardId);
	const navigate = useNavigate();
	const updateBoard = useUpdateBoardEndpointApiBoardsBoardIdPatch();

	const [isEditingTitle, setIsEditingTitle] = useState(false);
	const [editTitle, setEditTitle] = useState("");

	if (boardQuery.isLoading) {
		return (
			<div className="flex h-screen">
				<BoardSkeleton />
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

	const handleTitleSubmit = () => {
		const trimmed = editTitle.trim();
		if (trimmed && trimmed !== board.title) {
			updateBoard.mutate({ boardId, data: { title: trimmed } });
		}
		setIsEditingTitle(false);
	};

	const handleTitleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
		if (e.key === "Enter") handleTitleSubmit();
		if (e.key === "Escape") {
			setEditTitle(board.title);
			setIsEditingTitle(false);
		}
	};

	return (
		<div className="flex h-screen flex-col">
			{/* Board Header */}
			<div className="flex items-center gap-3 border-b px-4 py-3">
				<Button variant="ghost" size="sm" onClick={() => navigate({ to: "/" })}>
					<ArrowLeft className="h-4 w-4" />
				</Button>
				{isEditingTitle ? (
					<Input
						autoFocus
						value={editTitle}
						onChange={(e) => setEditTitle(e.target.value)}
						onKeyDown={handleTitleKeyDown}
						onBlur={handleTitleSubmit}
						className="h-8 max-w-md text-lg font-semibold"
					/>
				) : (
					<h1
						className="cursor-pointer text-lg font-semibold"
						onDoubleClick={() => {
							setEditTitle(board.title);
							setIsEditingTitle(true);
						}}
					>
						{board.title}
					</h1>
				)}
			</div>

			{/* Board Content */}
			<div className="flex-1 overflow-hidden">
				<BoardView board={board} />
			</div>
		</div>
	);
}
