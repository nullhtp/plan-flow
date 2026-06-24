import { Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import type { TaskResponse } from "@/features/board/types";
import { TaskDetailContent } from "./TaskDetailContent";

interface TaskDetailPanelProps {
	task: TaskResponse;
	allTasks: TaskResponse[];
	boardId: string;
	isSubBoard?: boolean;
	onClose: () => void;
	onUpdateTask: (data: {
		title?: string;
		description?: string;
		status?: string;
		due_date?: string | null;
		priority?: string | null;
		estimated_minutes?: number | null;
	}) => void;
	onDeleteTask: () => void;
	onStatusToggle: () => void;
	onToggleSubtask: (subtaskId: string, completed: boolean) => void;
	onAddSubtask: (title: string) => void;
	onDeleteSubtask: (subtaskId: string) => void;
}

export function TaskDetailPanel({
	task,
	allTasks,
	boardId,
	isSubBoard = false,
	onClose,
	onUpdateTask,
	onDeleteTask,
	onStatusToggle,
	onToggleSubtask,
	onAddSubtask,
	onDeleteSubtask,
}: TaskDetailPanelProps) {
	const { t } = useTranslation("board");
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

	useEffect(() => {
		const handler = (e: KeyboardEvent) => {
			if (e.key === "Escape") onClose();
		};
		window.addEventListener("keydown", handler);
		return () => window.removeEventListener("keydown", handler);
	}, [onClose]);

	const dependentTasks = task.dependent_ids
		.map((id) => allTasks.find((t) => t.id === id))
		.filter(Boolean) as TaskResponse[];

	return (
		<div className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col border-l bg-background shadow-xl">
			<div className="flex items-center justify-between border-b p-4">
				<h2 className="text-lg font-semibold">{t("taskDetailPanel.taskDetails")}</h2>
				<div className="flex items-center gap-1">
					<Button
						variant="ghost"
						size="sm"
						onClick={() => setShowDeleteConfirm(true)}
						className="text-destructive"
					>
						<Trash2 className="h-4 w-4" />
					</Button>
					<Button variant="ghost" size="sm" onClick={onClose}>
						<X className="h-4 w-4" />
					</Button>
				</div>
			</div>
			<div className="flex-1 overflow-y-auto p-4 space-y-4">
				<TaskDetailContent
					task={task}
					allTasks={allTasks}
					boardId={boardId}
					isSubBoard={isSubBoard}
					onUpdateTask={onUpdateTask}
					onStatusToggle={onStatusToggle}
					onToggleSubtask={onToggleSubtask}
					onAddSubtask={onAddSubtask}
					onDeleteSubtask={onDeleteSubtask}
					onNavigateAway={onClose}
				/>
			</div>

			{/* Delete confirmation */}
			{showDeleteConfirm && (
				<div className="absolute inset-0 z-50 flex items-center justify-center bg-black/50">
					<div className="mx-4 max-w-sm rounded-lg bg-background p-6 shadow-xl">
						<h3 className="text-lg font-semibold mb-2">{t("taskDetailPanel.deleteTask")}</h3>
						{dependentTasks.length > 0 ? (
							<p className="text-sm text-muted-foreground mb-4">
								{t("taskDetailPanel.prerequisiteFor", { count: dependentTasks.length })}
							</p>
						) : (
							<p className="text-sm text-muted-foreground mb-4">
								{t("taskDetailPanel.confirmDelete")}
							</p>
						)}
						<div className="flex justify-end gap-2">
							<Button variant="outline" onClick={() => setShowDeleteConfirm(false)}>
								{t("taskDetailPanel.cancel")}
							</Button>
							<Button variant="destructive" onClick={onDeleteTask}>
								{t("taskDetailPanel.delete")}
							</Button>
						</div>
					</div>
				</div>
			)}
		</div>
	);
}
