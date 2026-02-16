import { useNavigate } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { BoardListResponse } from "@/features/board/types";

interface BoardCardProps {
	board: BoardListResponse;
}

export function BoardCard({ board }: BoardCardProps) {
	const navigate = useNavigate();

	const progress =
		board.task_count > 0 ? Math.round((board.completed_task_count / board.task_count) * 100) : 0;

	return (
		<Card
			className="cursor-pointer transition-shadow hover:shadow-md"
			onClick={() => navigate({ to: "/boards/$boardId", params: { boardId: board.id } })}
			role="button"
			tabIndex={0}
			onKeyDown={(e) => {
				if (e.key === "Enter") navigate({ to: "/boards/$boardId", params: { boardId: board.id } });
			}}
		>
			<CardHeader className="pb-2">
				<CardTitle className="text-base">{board.title}</CardTitle>
				{board.goal_title && <p className="text-xs text-muted-foreground">{board.goal_title}</p>}
			</CardHeader>
			<CardContent>
				<div className="flex items-center justify-between text-sm text-muted-foreground">
					<span>{board.column_count} columns</span>
					<span>
						{board.completed_task_count}/{board.task_count} tasks
					</span>
				</div>
				<div className="mt-2 h-1.5 w-full rounded-full bg-muted">
					<div
						className="h-full rounded-full bg-primary transition-all"
						style={{ width: `${progress}%` }}
					/>
				</div>
			</CardContent>
		</Card>
	);
}
