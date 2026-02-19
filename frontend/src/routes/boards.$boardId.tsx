import { createRoute } from "@tanstack/react-router";
import { Brain } from "lucide-react";
import { type KeyboardEvent, useState } from "react";
import { useUpdateBoardEndpointApiBoardsBoardIdPatch } from "@/api/generated/boards/boards";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { BoardMetaInfo } from "@/features/board/components/BoardMetaInfo";
import { BoardSkeleton } from "@/features/board/components/BoardSkeleton";
import { BreadcrumbNav } from "@/features/board/components/BreadcrumbNav";
import { DagView } from "@/features/board/components/DagView";
import { useBoard } from "@/features/board/hooks/use-board";
import type { BoardResponse } from "@/features/board/types";
import { ErrorDisplay } from "@/features/goals/components/error-display";
import { BoardMemorySidebar } from "@/features/memory/components/BoardMemorySidebar";
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
	const updateBoard = useUpdateBoardEndpointApiBoardsBoardIdPatch();

	const [isEditingTitle, setIsEditingTitle] = useState(false);
	const [editTitle, setEditTitle] = useState("");
	const [showMemorySidebar, setShowMemorySidebar] = useState(false);

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
			{/* Board Header with Breadcrumb */}
			<div className="flex items-center gap-3 border-b px-4 py-3">
				<div className="flex min-w-0 flex-1 flex-col gap-1">
					<BreadcrumbNav boardTitle={board.title} parentBoard={board.parent_board} />
					<div className="flex items-center gap-2">
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
					{board.user_meta && <BoardMetaInfo userMeta={board.user_meta} />}
				</div>
				<Button
					variant={showMemorySidebar ? "default" : "outline"}
					size="sm"
					className="gap-1.5 shrink-0"
					onClick={() => setShowMemorySidebar((v) => !v)}
					title="Board memories"
				>
					<Brain className="h-4 w-4" />
					<span className="hidden sm:inline">Memories</span>
				</Button>
			</div>

			{/* DAG Graph View */}
			<div className="flex-1 overflow-hidden">
				<DagView board={board} />
			</div>

			{/* Memory Sidebar */}
			{showMemorySidebar && (
				<BoardMemorySidebar boardId={board.id} onClose={() => setShowMemorySidebar(false)} />
			)}
		</div>
	);
}
