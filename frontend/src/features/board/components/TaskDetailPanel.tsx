import { ArrowRight, Lock, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { TaskResponse } from "@/features/board/types";
import { SubtaskChecklist } from "./SubtaskChecklist";
import { TaskAiActions } from "./TaskAiActions";
import { TaskArtifacts } from "./TaskArtifacts";
import { TaskChat } from "./TaskChat";

interface TaskDetailPanelProps {
	task: TaskResponse;
	allTasks: TaskResponse[];
	boardId: string;
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
	onClose,
	onUpdateTask,
	onDeleteTask,
	onStatusToggle,
	onToggleSubtask,
	onAddSubtask,
	onDeleteSubtask,
}: TaskDetailPanelProps) {
	const [title, setTitle] = useState(task.title);
	const [description, setDescription] = useState(task.description);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
	const [chatPrompt, setChatPrompt] = useState<string | null>(null);
	const scrollContainerRef = useRef<HTMLDivElement>(null);
	const chatSectionRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		setTitle(task.title);
		setDescription(task.description);
	}, [task.title, task.description]);

	useEffect(() => {
		const handler = (e: KeyboardEvent) => {
			if (e.key === "Escape") onClose();
		};
		window.addEventListener("keydown", handler);
		return () => window.removeEventListener("keydown", handler);
	}, [onClose]);

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

	const dependencyTasks = task.dependency_ids
		.map((id) => allTasks.find((t) => t.id === id))
		.filter(Boolean) as TaskResponse[];

	const dependentTasks = task.dependent_ids
		.map((id) => allTasks.find((t) => t.id === id))
		.filter(Boolean) as TaskResponse[];

	const statusLabel: Record<string, string> = {
		not_started: "Not Started",
		in_progress: "In Progress",
		done: "Done",
	};

	const statusColor: Record<string, string> = {
		not_started: "bg-gray-200 text-gray-700",
		in_progress: "bg-blue-100 text-blue-700",
		done: "bg-green-100 text-green-700",
	};

	const unmetDeps = dependencyTasks.filter((t) => t.status !== "done");

	const handleActionClick = useCallback((prompt: string) => {
		setChatPrompt(prompt);
		// Scroll to chat section after a tick
		setTimeout(() => {
			chatSectionRef.current?.scrollIntoView({ behavior: "smooth" });
		}, 100);
	}, []);

	return (
		<div className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col border-l bg-background shadow-xl">
			<div className="flex items-center justify-between border-b p-4">
				<h2 className="text-lg font-semibold">Task Details</h2>
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
			<div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4">
				{/* Status */}
				<div>
					<Label>Status</Label>
					<div className="mt-1 flex items-center gap-2">
						<button
							type="button"
							onClick={onStatusToggle}
							disabled={task.is_locked}
							className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
								statusColor[task.status] ?? statusColor.not_started
							} ${task.is_locked ? "opacity-50 cursor-not-allowed" : "cursor-pointer hover:opacity-80"}`}
							title={
								task.is_locked
									? `Complete prerequisites first: ${unmetDeps.map((t) => t.title).join(", ")}`
									: "Click to change status"
							}
						>
							{task.is_locked && <Lock className="inline h-3 w-3 mr-1" />}
							{statusLabel[task.status] ?? task.status}
						</button>
						{task.is_locked && (
							<span className="text-xs text-muted-foreground">
								Blocked by {unmetDeps.length} task{unmetDeps.length !== 1 ? "s" : ""}
							</span>
						)}
					</div>
				</div>

				{/* Title */}
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

				{/* Description */}
				<div>
					<Label htmlFor="task-desc">Description</Label>
					<textarea
						id="task-desc"
						value={description}
						onChange={(e) => setDescription(e.target.value)}
						onBlur={handleDescriptionBlur}
						rows={3}
						className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
					/>
				</div>

				{/* Metadata */}
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

				{/* Dependencies */}
				{dependencyTasks.length > 0 && (
					<div>
						<Label>Dependencies (prerequisites)</Label>
						<div className="mt-1 space-y-1">
							{dependencyTasks.map((dep) => (
								<div
									key={dep.id}
									className="flex items-center gap-2 text-sm rounded px-2 py-1 bg-muted/50"
								>
									<span
										className={`h-2 w-2 rounded-full ${
											dep.status === "done" ? "bg-green-500" : "bg-gray-400"
										}`}
									/>
									<span
										className={dep.status === "done" ? "text-muted-foreground line-through" : ""}
									>
										{dep.title}
									</span>
								</div>
							))}
						</div>
					</div>
				)}

				{/* Unlocks */}
				{dependentTasks.length > 0 && (
					<div>
						<Label>Unlocks</Label>
						<div className="mt-1 space-y-1">
							{dependentTasks.map((dep) => (
								<div
									key={dep.id}
									className="flex items-center gap-2 text-sm rounded px-2 py-1 bg-muted/50"
								>
									<ArrowRight className="h-3 w-3 text-muted-foreground" />
									<span>{dep.title}</span>
								</div>
							))}
						</div>
					</div>
				)}

				{/* Subtasks */}
				<SubtaskChecklist
					subtasks={task.subtasks ?? []}
					onToggle={onToggleSubtask}
					onAdd={onAddSubtask}
					onDelete={onDeleteSubtask}
				/>

				{/* AI Actions */}
				<TaskAiActions taskId={task.id} onActionClick={handleActionClick} />

				{/* Artifacts */}
				<TaskArtifacts taskId={task.id} />

				{/* Chat */}
				<div ref={chatSectionRef}>
					<TaskChat taskId={task.id} boardId={boardId} initialPrompt={chatPrompt} />
				</div>
			</div>

			{/* Delete confirmation */}
			{showDeleteConfirm && (
				<div className="absolute inset-0 z-50 flex items-center justify-center bg-black/50">
					<div className="mx-4 max-w-sm rounded-lg bg-background p-6 shadow-xl">
						<h3 className="text-lg font-semibold mb-2">Delete Task</h3>
						{dependentTasks.length > 0 ? (
							<p className="text-sm text-muted-foreground mb-4">
								This task is a prerequisite for {dependentTasks.length} other task
								{dependentTasks.length !== 1 ? "s" : ""}. Deleting it will unblock them.
							</p>
						) : (
							<p className="text-sm text-muted-foreground mb-4">
								Are you sure you want to delete this task?
							</p>
						)}
						<div className="flex justify-end gap-2">
							<Button variant="outline" onClick={() => setShowDeleteConfirm(false)}>
								Cancel
							</Button>
							<Button variant="destructive" onClick={onDeleteTask}>
								Delete
							</Button>
						</div>
					</div>
				</div>
			)}
		</div>
	);
}
