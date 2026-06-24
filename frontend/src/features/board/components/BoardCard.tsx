import { useNavigate } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { BoardListResponse } from "@/features/board/types";

interface BoardCardProps {
	board: BoardListResponse;
	/** Simplified variant: title + plain "% done" only (no goal subtitle, no progress bar). */
	simple?: boolean;
}

export function BoardCard({ board, simple = false }: BoardCardProps) {
	const { t } = useTranslation("board");
	const navigate = useNavigate();

	const progress =
		board.task_count > 0 ? Math.round((board.completed_task_count / board.task_count) * 100) : 0;

	const open = () => navigate({ to: "/boards/$boardId", params: { boardId: board.id } });

	return (
		<Card
			className="cursor-pointer transition-shadow hover:shadow-md"
			onClick={open}
			role="button"
			tabIndex={0}
			onKeyDown={(e) => {
				if (e.key === "Enter") open();
			}}
		>
			<CardHeader className="pb-2">
				<div className="flex items-center justify-between gap-2">
					<CardTitle className="min-w-0 truncate text-base">{board.title}</CardTitle>
					{board.role === "collaborator" && (
						<span className="shrink-0 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
							{t("boardCard.shared")}
						</span>
					)}
				</div>
				{!simple && board.goal_title && (
					<p className="text-xs text-muted-foreground">{board.goal_title}</p>
				)}
			</CardHeader>
			<CardContent>
				{simple ? (
					<span className="text-sm text-muted-foreground">{t("boardCard.done", { progress })}</span>
				) : (
					<>
						<div className="flex items-center justify-between text-sm text-muted-foreground">
							<span>{t("boardCard.complete", { progress })}</span>
							<span>
								{t("boardCard.tasks", {
									completed: board.completed_task_count,
									total: board.task_count,
								})}
							</span>
						</div>
						<div className="mt-2 h-1.5 w-full rounded-full bg-muted">
							<div
								className="h-full rounded-full bg-primary transition-all"
								style={{ width: `${progress}%` }}
							/>
						</div>
					</>
				)}
			</CardContent>
		</Card>
	);
}
