import { useNavigate } from "@tanstack/react-router";
import { ExternalLink, Layers, Lock } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { TaskResponse } from "@/features/board/types";
import { SubtaskChecklist } from "./SubtaskChecklist";
import { TaskArtifacts } from "./TaskArtifacts";
import { TaskChat } from "./TaskChat";

export interface TaskDetailContentProps {
	task: TaskResponse;
	allTasks: TaskResponse[];
	boardId: string;
	isSubBoard?: boolean;
	onUpdateTask: (data: {
		title?: string;
		description?: string;
		status?: string;
		due_date?: string | null;
		priority?: string | null;
		estimated_minutes?: number | null;
	}) => void;
	onStatusToggle: () => void;
	onToggleSubtask: (subtaskId: string, completed: boolean) => void;
	onAddSubtask: (title: string) => void;
	onDeleteSubtask: (subtaskId: string) => void;
	/** Called after navigating away (e.g. opening a sub-board). The panel uses this to close. */
	onNavigateAway?: () => void;
}

const statusLabelKey: Record<string, string> = {
	not_started: "taskDetailContent.statusNotStarted",
	in_progress: "taskDetailContent.statusInProgress",
	done: "taskDetailContent.statusDone",
};

const statusColor: Record<string, string> = {
	not_started: "bg-gray-200 text-gray-700",
	in_progress: "bg-blue-100 text-blue-700",
	done: "bg-green-100 text-green-700",
};

/**
 * The shared inner task-detail experience (status, title, description, metadata,
 * subtasks or sub-board, artifacts, chat). Rendered both inside the slide-out
 * TaskDetailPanel (Advanced mode) and full-screen in the Simple stepper.
 */
export function TaskDetailContent({
	task,
	allTasks,
	boardId,
	isSubBoard = false,
	onUpdateTask,
	onStatusToggle,
	onToggleSubtask,
	onAddSubtask,
	onDeleteSubtask,
	onNavigateAway,
}: TaskDetailContentProps) {
	const { t } = useTranslation("board");
	const navigate = useNavigate();
	const [title, setTitle] = useState(task.title);
	const [description, setDescription] = useState(task.description);
	const [showExpandConfirm, setShowExpandConfirm] = useState(false);
	const [chatPrompt, setChatPrompt] = useState<string | null>(null);
	const chatSectionRef = useRef<HTMLDivElement>(null);

	const hasSubBoard = !!task.sub_board_id;
	const canExpand = !hasSubBoard && !isSubBoard;

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

	const dependencyTasks = task.dependency_ids
		.map((id) => allTasks.find((t) => t.id === id))
		.filter(Boolean) as TaskResponse[];

	const unmetDeps = dependencyTasks.filter((t) => t.status !== "done");

	const handleActionClick = useCallback((prompt: string) => {
		setChatPrompt(prompt);
		setTimeout(() => {
			chatSectionRef.current?.scrollIntoView({ behavior: "smooth" });
		}, 100);
	}, []);

	function navigateToExpansionPage() {
		navigate({
			to: "/boards/$boardId/expand/$taskId",
			params: { boardId, taskId: task.id },
		});
		onNavigateAway?.();
	}

	return (
		<>
			{/* Status */}
			<div>
				<Label>{t("taskDetailContent.status")}</Label>
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
								? t("taskDetailContent.completePrerequisitesFirst", {
										deps: unmetDeps.map((d) => d.title).join(", "),
									})
								: t("taskDetailContent.clickToChangeStatus")
						}
					>
						{task.is_locked && <Lock className="inline h-3 w-3 mr-1" />}
						{statusLabelKey[task.status] ? t(statusLabelKey[task.status]) : task.status}
					</button>
					{task.is_locked && (
						<span className="text-xs text-muted-foreground">
							{t("taskDetailContent.blockedBy", { count: unmetDeps.length })}
						</span>
					)}
				</div>
			</div>

			{/* Title */}
			<div>
				<Label htmlFor="task-title">{t("taskDetailContent.title")}</Label>
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
				<Label htmlFor="task-desc">{t("taskDetailContent.description")}</Label>
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
					<Label htmlFor="task-priority">{t("taskDetailContent.priority")}</Label>
					<select
						id="task-priority"
						value={task.priority ?? ""}
						onChange={(e) => onUpdateTask({ priority: e.target.value || null })}
						className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
					>
						<option value="">{t("taskDetailContent.priorityNone")}</option>
						<option value="low">{t("taskDetailContent.priorityLow")}</option>
						<option value="medium">{t("taskDetailContent.priorityMedium")}</option>
						<option value="high">{t("taskDetailContent.priorityHigh")}</option>
					</select>
				</div>
				<div>
					<Label htmlFor="task-estimate">{t("taskDetailContent.estimate")}</Label>
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
				<Label htmlFor="task-due">{t("taskDetailContent.dueDate")}</Label>
				<Input
					id="task-due"
					type="date"
					value={task.due_date ?? ""}
					onChange={(e) => onUpdateTask({ due_date: e.target.value || null })}
					className="mt-1"
				/>
			</div>

			{/* Subtasks or Sub-Board section */}
			{hasSubBoard ? (
				<div>
					<Label>{t("taskDetailContent.subBoard")}</Label>
					<div className="mt-2 rounded-lg border border-violet-200 bg-violet-50/50 dark:border-violet-800 dark:bg-violet-950/20 p-3">
						<div className="flex items-center gap-2 mb-2">
							<Layers className="h-4 w-4 text-violet-600" />
							<span className="font-medium text-sm">
								{task.sub_board_progress
									? t("taskDetailContent.tasksCompleted", {
											completed: task.sub_board_progress.completed_task_count,
											total: task.sub_board_progress.task_count,
										})
									: t("taskDetailContent.subBoardFallback")}
							</span>
						</div>
						<Button
							size="sm"
							variant="outline"
							className="w-full border-violet-300 text-violet-700 hover:bg-violet-100"
							onClick={() => {
								if (task.sub_board_id) {
									navigate({ to: "/boards/$boardId", params: { boardId: task.sub_board_id } });
									onNavigateAway?.();
								}
							}}
						>
							<ExternalLink className="h-3.5 w-3.5 mr-1.5" />
							{t("taskDetailContent.openSubBoard")}
						</Button>
					</div>
				</div>
			) : (
				<>
					<SubtaskChecklist
						subtasks={task.subtasks ?? []}
						onToggle={onToggleSubtask}
						onAdd={onAddSubtask}
						onDelete={onDeleteSubtask}
						onActionClick={handleActionClick}
					/>
					{canExpand && (
						<div className="mt-2">
							<Button
								variant="outline"
								size="sm"
								className="w-full text-violet-700 border-violet-300 hover:bg-violet-50"
								onClick={() => {
									if (task.subtasks && task.subtasks.length > 0) {
										setShowExpandConfirm(true);
									} else {
										navigateToExpansionPage();
									}
								}}
							>
								<Layers className="h-3.5 w-3.5 mr-1.5" />
								{t("taskDetailContent.expandToBoard")}
							</Button>
						</div>
					)}
				</>
			)}

			{/* Artifacts */}
			<TaskArtifacts taskId={task.id} />

			{/* Chat */}
			<div ref={chatSectionRef}>
				<TaskChat taskId={task.id} boardId={boardId} initialPrompt={chatPrompt} />
			</div>

			{/* Expand to Board confirmation (when subtasks exist) */}
			{showExpandConfirm && (
				<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
					<div className="mx-4 max-w-sm rounded-lg bg-background p-6 shadow-xl">
						<h3 className="text-lg font-semibold mb-2">{t("taskDetailContent.expandToBoard")}</h3>
						<p className="text-sm text-muted-foreground mb-4">
							{t("taskDetailContentExpand.intro", { count: task.subtasks?.length ?? 0 })}
							<span className="font-medium text-foreground">
								{t("taskDetailContentExpand.replaceAllSubtasks")}
							</span>
							{t("taskDetailContentExpand.outro")}
						</p>
						<div className="flex justify-end gap-2">
							<Button variant="outline" onClick={() => setShowExpandConfirm(false)}>
								{t("taskDetailContent.cancel")}
							</Button>
							<Button
								className="bg-violet-600 hover:bg-violet-700 text-white"
								onClick={() => {
									setShowExpandConfirm(false);
									navigateToExpansionPage();
								}}
							>
								{t("taskDetailContent.continue")}
							</Button>
						</div>
					</div>
				</div>
			)}
		</>
	);
}
