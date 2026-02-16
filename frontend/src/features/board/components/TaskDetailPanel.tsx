import { Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { ColumnResponse, TaskResponse } from "@/features/board/types";
import { SubtaskChecklist } from "./SubtaskChecklist";

interface TaskDetailPanelProps {
	task: TaskResponse;
	columns: ColumnResponse[];
	currentColumnId: string;
	onClose: () => void;
	onUpdateTask: (data: {
		title?: string;
		description?: string;
		due_date?: string | null;
		priority?: string | null;
		estimated_minutes?: number | null;
		column_id?: string;
	}) => void;
	onDeleteTask: () => void;
	onToggleSubtask: (subtaskId: string, completed: boolean) => void;
	onAddSubtask: (title: string) => void;
	onDeleteSubtask: (subtaskId: string) => void;
}

export function TaskDetailPanel({
	task,
	columns,
	currentColumnId,
	onClose,
	onUpdateTask,
	onDeleteTask,
	onToggleSubtask,
	onAddSubtask,
	onDeleteSubtask,
}: TaskDetailPanelProps) {
	const [title, setTitle] = useState(task.title);
	const [description, setDescription] = useState(task.description);

	useEffect(() => {
		setTitle(task.title);
		setDescription(task.description);
	}, [task.title, task.description]);

	const handleTitleBlur = () => {
		if (title.trim() && title !== task.title) {
			onUpdateTask({ title: title.trim() });
		}
	};

	const handleDescriptionBlur = () => {
		if (description !== task.description) {
			onUpdateTask({ description });
		}
	};

	return (
		<div className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col border-l bg-background shadow-xl">
			<div className="flex items-center justify-between border-b p-4">
				<h2 className="text-lg font-semibold">Task Details</h2>
				<div className="flex items-center gap-1">
					<Button variant="ghost" size="sm" onClick={onDeleteTask} className="text-destructive">
						<Trash2 className="h-4 w-4" />
					</Button>
					<Button variant="ghost" size="sm" onClick={onClose}>
						<X className="h-4 w-4" />
					</Button>
				</div>
			</div>
			<div className="flex-1 overflow-y-auto p-4 space-y-4">
				<div>
					<Label htmlFor="task-title">Title</Label>
					<Input
						id="task-title"
						value={title}
						onChange={(e) => setTitle(e.target.value)}
						onBlur={handleTitleBlur}
						className="mt-1"
					/>
				</div>
				<div>
					<Label htmlFor="task-desc">Description</Label>
					<textarea
						id="task-desc"
						value={description}
						onChange={(e) => setDescription(e.target.value)}
						onBlur={handleDescriptionBlur}
						rows={4}
						className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
					/>
				</div>
				<div>
					<Label htmlFor="task-column">Column</Label>
					<select
						id="task-column"
						value={currentColumnId}
						onChange={(e) => onUpdateTask({ column_id: e.target.value })}
						className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
					>
						{columns.map((col) => (
							<option key={col.id} value={col.id}>
								{col.title}
							</option>
						))}
					</select>
				</div>
				<div className="grid grid-cols-2 gap-4">
					<div>
						<Label htmlFor="task-priority">Priority</Label>
						<select
							id="task-priority"
							value={task.priority ?? ""}
							onChange={(e) => onUpdateTask({ priority: e.target.value || null })}
							className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
						>
							<option value="">None</option>
							<option value="low">Low</option>
							<option value="medium">Medium</option>
							<option value="high">High</option>
						</select>
					</div>
					<div>
						<Label htmlFor="task-estimate">Estimate (min)</Label>
						<Input
							id="task-estimate"
							type="number"
							min={1}
							value={task.estimated_minutes ?? ""}
							onChange={(e) =>
								onUpdateTask({ estimated_minutes: e.target.value ? Number(e.target.value) : null })
							}
							className="mt-1"
						/>
					</div>
				</div>
				<div>
					<Label htmlFor="task-due">Due Date</Label>
					<Input
						id="task-due"
						type="date"
						value={task.due_date ?? ""}
						onChange={(e) => onUpdateTask({ due_date: e.target.value || null })}
						className="mt-1"
					/>
				</div>
				<SubtaskChecklist
					subtasks={task.subtasks ?? []}
					onToggle={onToggleSubtask}
					onAdd={onAddSubtask}
					onDelete={onDeleteSubtask}
				/>
			</div>
		</div>
	);
}
