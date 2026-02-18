import { useNavigate } from "@tanstack/react-router";
import { ChevronRight, Home } from "lucide-react";

interface BreadcrumbNavProps {
	boardTitle: string;
	parentBoard?: { id: string; title: string } | null;
}

function truncateTitle(title: string, maxLength = 40): string {
	if (title.length <= maxLength) return title;
	return `${title.slice(0, maxLength)}...`;
}

export function BreadcrumbNav({ boardTitle, parentBoard }: BreadcrumbNavProps) {
	const navigate = useNavigate();

	return (
		<nav className="flex items-center gap-1.5 text-sm text-muted-foreground">
			{/* Home */}
			<button
				type="button"
				onClick={() => navigate({ to: "/" })}
				className="flex items-center gap-1 rounded px-1.5 py-0.5 hover:bg-muted hover:text-foreground transition-colors"
			>
				<Home className="h-3.5 w-3.5" />
				<span>Home</span>
			</button>

			<ChevronRight className="h-3.5 w-3.5 flex-shrink-0" />

			{/* Parent board (only for sub-boards) */}
			{parentBoard && (
				<>
					<button
						type="button"
						onClick={() =>
							navigate({ to: "/boards/$boardId", params: { boardId: parentBoard.id } })
						}
						className="rounded px-1.5 py-0.5 hover:bg-muted hover:text-foreground transition-colors truncate max-w-[200px]"
						title={parentBoard.title}
					>
						{truncateTitle(parentBoard.title)}
					</button>
					<ChevronRight className="h-3.5 w-3.5 flex-shrink-0" />
				</>
			)}

			{/* Current board (not clickable) */}
			<span className="text-foreground font-medium truncate max-w-[200px]" title={boardTitle}>
				{truncateTitle(boardTitle)}
			</span>
		</nav>
	);
}
