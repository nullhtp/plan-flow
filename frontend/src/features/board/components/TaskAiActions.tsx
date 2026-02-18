import {
	BarChart3,
	Eye,
	FileCheck,
	FileText,
	GitCompare,
	ListChecks,
	type LucideIcon,
	Plus,
	RefreshCw,
	Search,
	Sparkles,
} from "lucide-react";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useActionSuggestions } from "../hooks/use-action-suggestions";

const ICON_MAP: Record<string, LucideIcon> = {
	generate: FileText,
	research: Search,
	plan: ListChecks,
	analyze: BarChart3,
	summarize: FileCheck,
	review: Eye,
	compare: GitCompare,
	create: Plus,
};

interface TaskAiActionsProps {
	taskId: string;
	onActionClick: (prompt: string) => void;
}

export function TaskAiActions({ taskId, onActionClick }: TaskAiActionsProps) {
	const { actions, isLoading, error, fetchSuggestions } = useActionSuggestions(taskId);

	useEffect(() => {
		fetchSuggestions();
	}, [fetchSuggestions]);

	return (
		<div>
			<div className="flex items-center justify-between">
				<Label className="flex items-center gap-1.5">
					<Sparkles className="h-3.5 w-3.5" />
					AI Actions
				</Label>
				<Button
					variant="ghost"
					size="sm"
					onClick={fetchSuggestions}
					disabled={isLoading}
					className="h-6 px-1.5"
				>
					<RefreshCw className={`h-3 w-3 ${isLoading ? "animate-spin" : ""}`} />
				</Button>
			</div>

			{isLoading && actions.length === 0 && (
				<div className="mt-2 grid grid-cols-2 gap-2">
					{[1, 2, 3, 4].map((i) => (
						<div key={i} className="h-10 animate-pulse rounded-md bg-muted" />
					))}
				</div>
			)}

			{error && !isLoading && <p className="mt-2 text-xs text-muted-foreground">{error}</p>}

			{actions.length > 0 && (
				<div className="mt-2 grid grid-cols-2 gap-2">
					{actions.map((action) => {
						const Icon = ICON_MAP[action.icon] ?? Sparkles;
						return (
							<Button
								key={action.label}
								variant="outline"
								size="sm"
								className="h-auto justify-start gap-2 whitespace-normal py-2 text-left text-xs"
								onClick={() => onActionClick(action.prompt)}
							>
								<Icon className="h-3.5 w-3.5 shrink-0" />
								<span>{action.label}</span>
							</Button>
						);
					})}
				</div>
			)}
		</div>
	);
}
