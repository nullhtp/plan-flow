import { useNavigate } from "@tanstack/react-router";
import { Check, ExternalLink, Layers, Lock, Sparkles } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import type { TaskResponse } from "@/features/board/types";
import { TaskArtifacts } from "./TaskArtifacts";
import { TaskChat } from "./TaskChat";

interface StepCardProps {
	task: TaskResponse;
	allTasks: TaskResponse[];
	boardId: string;
	/** Sets the task's status. Marking `done` advances the stepper (handled by the parent). */
	onSetStatus: (status: string) => void;
	onToggleSubtask: (subtaskId: string, completed: boolean) => void;
}

/**
 * Minimal Simple-mode step screen: read-only title and description, a read-only
 * subtask checklist (completion toggle only — no add/delete/rename), AI chat, and
 * status buttons. Completing the task advances to the next step.
 */
export function StepCard({ task, allTasks, boardId, onSetStatus, onToggleSubtask }: StepCardProps) {
	const navigate = useNavigate();
	const [chatPrompt, setChatPrompt] = useState<string | null>(null);
	const chatRef = useRef<HTMLDivElement>(null);

	const hasSubBoard = !!task.sub_board_id;
	const subtasks = task.subtasks ?? [];

	const unmetDeps = task.dependency_ids
		.map((id) => allTasks.find((t) => t.id === id))
		.filter((t): t is TaskResponse => !!t && t.status !== "done");

	const handleAction = useCallback((prompt: string) => {
		setChatPrompt(prompt);
		setTimeout(() => chatRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
	}, []);

	return (
		<div className="space-y-6">
			{/* Status buttons */}
			<div>
				{task.is_locked ? (
					<div className="flex items-center gap-2 text-sm text-muted-foreground">
						<Lock className="h-4 w-4" />
						<span>
							Locked — complete first: {unmetDeps.map((t) => t.title).join(", ") || "prerequisites"}
						</span>
					</div>
				) : task.status === "not_started" ? (
					<Button onClick={() => onSetStatus("in_progress")}>Start task</Button>
				) : task.status === "in_progress" ? (
					<div className="flex flex-wrap gap-2">
						<Button onClick={() => onSetStatus("done")}>
							<Check className="mr-1.5 h-4 w-4" />
							Mark as done
						</Button>
						<Button variant="outline" onClick={() => onSetStatus("not_started")}>
							Reset
						</Button>
					</div>
				) : (
					<div className="flex flex-wrap items-center gap-3">
						<span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-700 dark:bg-green-900/40 dark:text-green-300">
							<Check className="h-4 w-4" />
							Completed
						</span>
						<Button variant="outline" size="sm" onClick={() => onSetStatus("in_progress")}>
							Reopen
						</Button>
					</div>
				)}
			</div>

			{/* Title (read-only) */}
			<h2 className="text-xl font-semibold leading-snug">{task.title}</h2>

			{/* Description (read-only) */}
			{task.description ? (
				<p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
					{task.description}
				</p>
			) : (
				<p className="text-sm italic text-muted-foreground">No description.</p>
			)}

			{/* Subtasks (toggle only) or Sub-Board CTA */}
			{hasSubBoard ? (
				<div className="rounded-lg border border-violet-200 bg-violet-50/50 p-3 dark:border-violet-800 dark:bg-violet-950/20">
					<div className="mb-2 flex items-center gap-2">
						<Layers className="h-4 w-4 text-violet-600" />
						<span className="text-sm font-medium">
							{task.sub_board_progress
								? `${task.sub_board_progress.completed_task_count}/${task.sub_board_progress.task_count} tasks completed`
								: "Sub-board"}
						</span>
					</div>
					<Button
						size="sm"
						variant="outline"
						className="w-full border-violet-300 text-violet-700 hover:bg-violet-100"
						onClick={() => {
							if (task.sub_board_id) {
								navigate({ to: "/boards/$boardId", params: { boardId: task.sub_board_id } });
							}
						}}
					>
						<ExternalLink className="mr-1.5 h-3.5 w-3.5" />
						Open Sub-Board
					</Button>
				</div>
			) : subtasks.length > 0 ? (
				<div className="space-y-2">
					<h3 className="text-sm font-medium">Subtasks</h3>
					<div className="space-y-1">
						{subtasks.map((st) => (
							<div key={st.id} className="space-y-1">
								<label className="flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 hover:bg-muted">
									<input
										type="checkbox"
										checked={st.completed}
										onChange={() => onToggleSubtask(st.id, !st.completed)}
										className="h-4 w-4 rounded border-muted-foreground/50"
									/>
									<span
										className={`flex-1 text-sm ${st.completed ? "text-muted-foreground line-through" : ""}`}
									>
										{st.title}
									</span>
								</label>
								{st.action_prompt && !st.completed && (
									<Button
										variant="outline"
										size="sm"
										className="ml-7 h-7 gap-1.5 border-violet-300 bg-violet-50 px-3 text-xs font-medium text-violet-700 hover:bg-violet-100 dark:border-violet-700 dark:bg-violet-950 dark:text-violet-300"
										title={st.action_label ?? "Ask AI"}
										onClick={() =>
											handleAction(`Help me with subtask: ${st.title} -- ${st.action_prompt}`)
										}
									>
										<Sparkles className="h-3 w-3" />
										{st.action_label ?? "Ask AI"}
									</Button>
								)}
							</div>
						))}
					</div>
				</div>
			) : null}

			{/* Artifacts */}
			<TaskArtifacts taskId={task.id} />

			{/* AI chat */}
			<div ref={chatRef}>
				<TaskChat taskId={task.id} boardId={boardId} initialPrompt={chatPrompt} />
			</div>
		</div>
	);
}
