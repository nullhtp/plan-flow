import { createRoute, useNavigate } from "@tanstack/react-router";
import { Brain, Eye, ListChecks, Network, Save, Share2 } from "lucide-react";
import { type KeyboardEvent, useEffect, useState } from "react";
import { useUpdateBoardEndpointApiBoardsBoardIdPatch } from "@/api/generated/boards/boards";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { BoardMetaInfo } from "@/features/board/components/BoardMetaInfo";
import { BoardSkeleton } from "@/features/board/components/BoardSkeleton";
import { BreadcrumbNav } from "@/features/board/components/BreadcrumbNav";
import type { BoardViewMode } from "@/features/board/components/DagView";
import { DagView } from "@/features/board/components/DagView";
import { SharePanel } from "@/features/board/components/SharePanel";
import { StepperView } from "@/features/board/components/StepperView";
import { useBoard } from "@/features/board/hooks/use-board";
import { type InterfaceMode, useInterfaceMode } from "@/features/board/hooks/use-interface-mode";
import type { BoardResponse } from "@/features/board/types";
import { isTaskHiddenInFocus } from "@/features/board/utils/board-filters";
import { ErrorDisplay } from "@/features/goals/components/error-display";
import { BoardMemorySidebar } from "@/features/memory/components/BoardMemorySidebar";
import { useCreateTemplate } from "@/features/templates/hooks/use-template-mutations";
import { useSimpleMode } from "@/shared/hooks/use-simple-mode";
import { authenticatedRoute } from "./_authenticated";

type BoardSearchParams = {
	task?: string;
	view?: BoardViewMode;
};

export const boardDetailRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/boards/$boardId",
	component: BoardDetailPage,
	validateSearch: (search: Record<string, unknown>): BoardSearchParams => ({
		task: typeof search.task === "string" ? search.task : undefined,
		view: search.view === "full" ? "full" : undefined,
	}),
});

function BoardDetailPage() {
	const { boardId } = boardDetailRoute.useParams();
	const search = boardDetailRoute.useSearch();
	const navigate = useNavigate();
	const boardQuery = useBoard(boardId);
	const updateBoard = useUpdateBoardEndpointApiBoardsBoardIdPatch();

	const [isEditingTitle, setIsEditingTitle] = useState(false);
	const [editTitle, setEditTitle] = useState("");
	const [showMemorySidebar, setShowMemorySidebar] = useState(false);
	const [showSharePanel, setShowSharePanel] = useState(false);
	const createTemplate = useCreateTemplate();

	// Global Simple mode is the master switch. When on, every board renders the
	// guided stepper and the per-session board toggles are hidden. When off, the
	// per-session preference (localStorage) governs and defaults to Advanced.
	const { isSimpleMode } = useSimpleMode();
	const { mode: sessionMode, setMode } = useInterfaceMode();
	const mode: InterfaceMode = isSimpleMode ? "simple" : sessionMode;

	// View mode: default is "focus" when view param is absent (only used in Advanced)
	const viewMode: BoardViewMode = search.view === "full" ? "full" : "focus";

	const board = boardQuery.data?.data as BoardResponse | undefined;

	// Edge case: if selected task is hidden in focus mode, auto-switch to full
	useEffect(() => {
		if (mode !== "advanced" || !board || viewMode !== "focus" || !search.task) return;
		const selectedTask = board.tasks.find((t) => t.id === search.task);
		if (selectedTask && isTaskHiddenInFocus(selectedTask)) {
			navigate({
				to: "/boards/$boardId",
				params: { boardId },
				search: { ...search, view: "full" },
				replace: true,
			});
		}
	}, [board, mode, viewMode, search, boardId, navigate]);

	const setViewMode = (mode: BoardViewMode) => {
		navigate({
			to: "/boards/$boardId",
			params: { boardId },
			search: { ...search, view: mode === "full" ? "full" : undefined },
		});
	};

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

	const boardData = boardQuery.data.data as BoardResponse;

	const handleTitleSubmit = () => {
		const trimmed = editTitle.trim();
		if (trimmed && trimmed !== boardData.title) {
			updateBoard.mutate({ boardId, data: { title: trimmed } });
		}
		setIsEditingTitle(false);
	};

	const handleTitleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
		if (e.key === "Enter") handleTitleSubmit();
		if (e.key === "Escape") {
			setEditTitle(boardData.title);
			setIsEditingTitle(false);
		}
	};

	return (
		<div className="flex h-screen flex-col">
			{/* Board Header with Breadcrumb */}
			<div className="flex items-center gap-3 border-b px-4 py-3">
				<div className="flex min-w-0 flex-1 flex-col gap-1">
					<BreadcrumbNav boardTitle={boardData.title} parentBoard={boardData.parent_board} />
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
									setEditTitle(boardData.title);
									setIsEditingTitle(true);
								}}
							>
								{boardData.title}
							</h1>
						)}
					</div>
					{boardData.user_meta && <BoardMetaInfo userMeta={boardData.user_meta} />}
				</div>
				{/* Interface Mode Toggle: Simple (stepper) vs Advanced (DAG).
					Only shown when global Simple mode is off; otherwise the stepper
					is forced and this per-session control is hidden. */}
				{!isSimpleMode && (
					<div className="flex shrink-0 rounded-lg border p-0.5">
						<button
							type="button"
							onClick={() => setMode("simple")}
							className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
								mode === "simple"
									? "bg-primary text-primary-foreground shadow-sm"
									: "text-muted-foreground hover:text-foreground"
							}`}
							title="Guided one-task-at-a-time view"
						>
							<ListChecks className="h-3.5 w-3.5" />
							<span className="hidden sm:inline">Simple</span>
						</button>
						<button
							type="button"
							onClick={() => setMode("advanced")}
							className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
								mode === "advanced"
									? "bg-primary text-primary-foreground shadow-sm"
									: "text-muted-foreground hover:text-foreground"
							}`}
							title="Full task graph"
						>
							<Network className="h-3.5 w-3.5" />
							<span className="hidden sm:inline">Advanced</span>
						</button>
					</div>
				)}

				{/* DAG View Mode Toggle (Advanced only) */}
				{mode === "advanced" && (
					<div className="flex shrink-0 rounded-lg border p-0.5">
						<button
							type="button"
							onClick={() => setViewMode("focus")}
							className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
								viewMode === "focus"
									? "bg-primary text-primary-foreground shadow-sm"
									: "text-muted-foreground hover:text-foreground"
							}`}
							title="Show actionable tasks only"
						>
							<Eye className="h-3.5 w-3.5" />
							<span className="hidden sm:inline">Focus</span>
						</button>
						<button
							type="button"
							onClick={() => setViewMode("full")}
							className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
								viewMode === "full"
									? "bg-primary text-primary-foreground shadow-sm"
									: "text-muted-foreground hover:text-foreground"
							}`}
							title="Show all tasks"
						>
							<Network className="h-3.5 w-3.5" />
							<span className="hidden sm:inline">Full DAG</span>
						</button>
					</div>
				)}
				{/* Power actions (Share, Save as Template, Memories) are hidden in Simple mode. */}
				{!isSimpleMode && boardData.role === "owner" && !boardData.parent_task_id && (
					<Button
						variant={showSharePanel ? "default" : "outline"}
						size="sm"
						className="gap-1.5 shrink-0"
						onClick={() => setShowSharePanel((v) => !v)}
						title="Share board"
					>
						<Share2 className="h-4 w-4" />
						<span className="hidden sm:inline">Share</span>
					</Button>
				)}
				{boardData.role === "collaborator" && (
					<span className="shrink-0 rounded-full bg-blue-100 px-2.5 py-1 text-xs font-medium text-blue-700">
						Shared with you
					</span>
				)}
				{!isSimpleMode && (
					<>
						<Button
							variant="outline"
							size="sm"
							className="gap-1.5 shrink-0"
							onClick={() => {
								createTemplate.mutate(
									{
										board_id: boardData.id,
										title: boardData.title,
										visibility: "private",
									},
									{
										onSuccess: (template) => {
											navigate({
												to: "/templates/$templateId",
												params: { templateId: template.id },
											});
										},
									},
								);
							}}
							title="Save as template"
							disabled={
								!boardData.tasks || boardData.tasks.length === 0 || createTemplate.isPending
							}
						>
							<Save className="h-4 w-4" />
							<span className="hidden sm:inline">
								{createTemplate.isPending ? "Saving..." : "Save as Template"}
							</span>
						</Button>
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
					</>
				)}
			</div>

			{/* Board body: Simple stepper or Advanced DAG */}
			<div className="flex-1 overflow-hidden">
				{mode === "simple" ? (
					<StepperView
						board={boardData}
						focusTaskId={search.task}
						onSwitchToAdvanced={isSimpleMode ? undefined : () => setMode("advanced")}
					/>
				) : (
					<DagView board={boardData} viewMode={viewMode} />
				)}
			</div>

			{/* Memory Sidebar */}
			{showMemorySidebar && (
				<BoardMemorySidebar boardId={boardData.id} onClose={() => setShowMemorySidebar(false)} />
			)}

			{/* Share Panel */}
			{showSharePanel && (
				<SharePanel boardId={boardData.id} onClose={() => setShowSharePanel(false)} />
			)}
		</div>
	);
}
