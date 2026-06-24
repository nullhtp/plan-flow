import {
	BarChart3,
	Eye,
	FileCheck,
	FileText,
	GitCompare,
	ListChecks,
	type LucideIcon,
	Plus,
	Search,
	Sparkles,
	Trash2,
} from "lucide-react";
import { type KeyboardEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { SubtaskResponse } from "@/features/board/types";

const ACTION_ICON_MAP: Record<string, LucideIcon> = {
	generate: FileText,
	research: Search,
	plan: ListChecks,
	analyze: BarChart3,
	summarize: FileCheck,
	review: Eye,
	compare: GitCompare,
	create: Plus,
};

interface SubtaskChecklistProps {
	subtasks: SubtaskResponse[];
	onToggle: (subtaskId: string, completed: boolean) => void;
	onAdd: (title: string) => void;
	onDelete: (subtaskId: string) => void;
	onActionClick?: (prompt: string) => void;
}

export function SubtaskChecklist({
	subtasks,
	onToggle,
	onAdd,
	onDelete,
	onActionClick,
}: SubtaskChecklistProps) {
	const { t } = useTranslation("board");
	const [newTitle, setNewTitle] = useState("");

	const handleAdd = () => {
		const trimmed = newTitle.trim();
		if (trimmed) {
			onAdd(trimmed);
			setNewTitle("");
		}
	};

	const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
		if (e.key === "Enter") handleAdd();
	};

	return (
		<div className="space-y-2">
			<h4 className="text-sm font-medium">{t("subtaskChecklist.subtasks")}</h4>
			<div className="space-y-1">
				{subtasks.map((subtask) => {
					const hasAction = subtask.action_prompt != null;
					const IconComponent = hasAction
						? (ACTION_ICON_MAP[subtask.action_icon ?? ""] ?? Sparkles)
						: null;

					return (
						<div key={subtask.id} className="group space-y-1">
							<div className="flex items-center gap-2 rounded px-1 py-0.5 hover:bg-muted">
								<input
									type="checkbox"
									checked={subtask.completed}
									onChange={() => onToggle(subtask.id, !subtask.completed)}
									className="h-4 w-4 rounded border-muted-foreground/50"
								/>
								<span
									className={`flex-1 text-sm ${subtask.completed ? "text-muted-foreground line-through" : ""}`}
								>
									{subtask.title}
								</span>
								<Button
									variant="ghost"
									size="sm"
									className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
									onClick={() => onDelete(subtask.id)}
								>
									<Trash2 className="h-3 w-3" />
								</Button>
							</div>
							{hasAction && IconComponent && onActionClick && !subtask.completed && (
								<Button
									variant="outline"
									size="sm"
									className="ml-7 h-7 gap-1.5 border-violet-300 bg-violet-50 px-3 text-xs font-medium text-violet-700 shadow-sm hover:bg-violet-100 hover:text-violet-800 dark:border-violet-700 dark:bg-violet-950 dark:text-violet-300 dark:hover:bg-violet-900"
									title={subtask.action_label ?? t("subtaskChecklist.aiAction")}
									onClick={() => {
										const prompt = t("subtaskChecklist.subtaskActionPrompt", {
											title: subtask.title,
											prompt: subtask.action_prompt,
										});
										onActionClick(prompt);
									}}
								>
									<Sparkles className="h-3 w-3" />
									{subtask.action_label}
								</Button>
							)}
						</div>
					);
				})}
			</div>
			<div className="flex items-center gap-2">
				<Input
					placeholder={t("subtaskChecklist.addSubtask")}
					value={newTitle}
					onChange={(e) => setNewTitle(e.target.value)}
					onKeyDown={handleKeyDown}
					className="h-8 text-sm"
				/>
				<Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={handleAdd}>
					<Plus className="h-4 w-4" />
				</Button>
			</div>
		</div>
	);
}
