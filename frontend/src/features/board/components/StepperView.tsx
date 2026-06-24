import { useNavigate } from "@tanstack/react-router";
import { ChevronLeft, ChevronRight, Network } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useSubtaskMutations } from "../hooks/use-subtask-mutations";
import { useTaskMutations } from "../hooks/use-task-mutations";
import type { BoardResponse, TaskResponse } from "../types";
import { getDefaultStepId, getStepSequence } from "../utils/stepper-order";
import { Celebration } from "./Celebration";
import { StepCard } from "./StepCard";

interface StepperViewProps {
	board: BoardResponse;
	/** Deep-linked task (from `?task=`) to land on. */
	focusTaskId?: string;
	/**
	 * Switch the board to Advanced (DAG) mode. Only provided when the user can
	 * reach Advanced from the board (i.e. global Simple mode is off); omitted when
	 * Simple mode owns the board, in which case the "View full DAG" CTA is hidden.
	 */
	onSwitchToAdvanced?: () => void;
}

export function StepperView({ board, focusTaskId, onSwitchToAdvanced }: StepperViewProps) {
	const { t } = useTranslation("board");
	const navigate = useNavigate();
	const { updateTask } = useTaskMutations(board.id);
	const { updateSubtask } = useSubtaskMutations(board.id);

	// Every task flattened into a single linear sequence (parallel paths serialized).
	const steps = useMemo(
		() => getStepSequence(board.tasks, board.edges),
		[board.tasks, board.edges],
	);

	const [currentTaskId, setCurrentTaskId] = useState<string | null>(() => {
		if (focusTaskId && steps.some((t) => t.id === focusTaskId)) return focusTaskId;
		return getDefaultStepId(steps);
	});
	const lastIndexRef = useRef(0);

	// Keep the current step valid as the sequence changes (e.g. a task is deleted).
	useEffect(() => {
		if (steps.length === 0) {
			if (currentTaskId !== null) setCurrentTaskId(null);
			return;
		}
		const idx = steps.findIndex((t) => t.id === currentTaskId);
		if (idx >= 0) {
			lastIndexRef.current = idx;
		} else {
			// Current task left the sequence (deleted) — keep the same slot.
			const nextIdx = Math.min(lastIndexRef.current, steps.length - 1);
			lastIndexRef.current = nextIdx;
			setCurrentTaskId(steps[nextIdx].id);
		}
	}, [steps, currentTaskId]);

	// Goal-completion celebration (mirrors DagView's transition detection).
	const [showCelebration, setShowCelebration] = useState(false);
	const prevIsCompleted = useRef(board.is_completed);
	if (board.is_completed && !prevIsCompleted.current) {
		setShowCelebration(true);
	}
	prevIsCompleted.current = board.is_completed;

	const currentIndex = currentTaskId ? steps.findIndex((t) => t.id === currentTaskId) : -1;
	const currentTask: TaskResponse | null = currentIndex >= 0 ? steps[currentIndex] : null;

	const totalTasks = board.tasks.length;
	const doneTasks = board.tasks.filter((t) => t.status === "done").length;
	const completionPct = totalTasks > 0 ? Math.round((doneTasks / totalTasks) * 100) : 0;

	const setTaskStatus = (task: TaskResponse, newStatus: string) => {
		if (task.is_locked) {
			toast.info(t("stepperView.completePrerequisitesFirst"));
			return;
		}
		updateTask.mutate({ taskId: task.id, data: { status: newStatus } });
		// Completing a task advances to the next step in the sequence.
		if (newStatus === "done") {
			const idx = steps.findIndex((t) => t.id === task.id);
			if (idx >= 0 && idx < steps.length - 1) {
				setCurrentTaskId(steps[idx + 1].id);
			}
		}
	};

	const handleToggleSubtask = (task: TaskResponse, subtaskId: string, completed: boolean) => {
		updateSubtask.mutate({ subtaskId, data: { completed } });
		if (!completed) return;
		// Checking the final subtask completes the task and opens the next step.
		const subs = task.subtasks ?? [];
		const allCompleted = subs.length > 0 && subs.every((s) => s.id === subtaskId || s.completed);
		if (allCompleted && task.status === "in_progress" && !task.is_locked) {
			setTaskStatus(task, "done");
		}
	};

	// The Next control unlocks only once the current step's task is done, so the
	// user must complete each task before advancing. Previous stays available so
	// completed steps can be revisited.
	const isLastStep = currentIndex >= steps.length - 1;
	const canGoNext = currentIndex >= 0 && !isLastStep && currentTask?.status === "done";

	const goPrev = () => {
		if (currentIndex > 0) setCurrentTaskId(steps[currentIndex - 1].id);
	};
	const goNext = () => {
		if (canGoNext) setCurrentTaskId(steps[currentIndex + 1].id);
	};

	// Empty board: nothing to step through.
	if (steps.length === 0) {
		return (
			<div className="relative flex h-full flex-col items-center justify-center p-6 text-center">
				<div className="max-w-md space-y-4">
					<h2 className="text-xl font-semibold">{t("stepperView.noTasksYet")}</h2>
					<p className="text-muted-foreground">
						{t("stepperView.noTasksDescription")}
						{onSwitchToAdvanced ? t("stepperView.noTasksDescriptionWithDag") : ""}
					</p>
					{onSwitchToAdvanced ? (
						<Button onClick={onSwitchToAdvanced}>
							<Network className="mr-1.5 h-4 w-4" />
							{t("stepperView.viewFullDag")}
						</Button>
					) : (
						<Button onClick={() => navigate({ to: "/" })}>
							{t("stepperView.backToDashboard")}
						</Button>
					)}
				</div>
			</div>
		);
	}

	// Board complete: celebrate and offer next actions.
	if (board.is_completed) {
		return (
			<div className="relative flex h-full flex-col items-center justify-center p-6 text-center">
				<div className="max-w-md space-y-4">
					<p className="text-5xl">🏆</p>
					<h2 className="text-2xl font-bold">{t("stepperView.allDone")}</h2>
					<p className="text-muted-foreground">{t("stepperView.allDoneDescription")}</p>
					<div className="flex justify-center gap-2">
						<Button variant="outline" onClick={() => navigate({ to: "/" })}>
							{t("stepperView.backToDashboard")}
						</Button>
						{onSwitchToAdvanced && (
							<Button onClick={onSwitchToAdvanced}>
								<Network className="mr-1.5 h-4 w-4" />
								{t("stepperView.viewFullDag")}
							</Button>
						)}
					</div>
				</div>
				<Celebration show={showCelebration} />
			</div>
		);
	}

	if (!currentTask) return null;

	return (
		<div className="relative flex h-full flex-col">
			{/* Progress + navigation bar */}
			<div className="flex flex-col gap-2 border-b px-4 py-3">
				<div className="flex items-center gap-3">
					<div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
						<div
							className="h-full rounded-full bg-primary transition-all duration-300"
							style={{ width: `${completionPct}%` }}
						/>
					</div>
					<span className="shrink-0 text-xs font-medium text-muted-foreground">
						{t("stepperView.done", { done: doneTasks, total: totalTasks })}
					</span>
				</div>
				<div className="flex items-center justify-between gap-2">
					<div className="flex flex-col">
						<span className="text-sm font-medium">
							{t("stepperView.step", { current: currentIndex + 1, total: steps.length })}
						</span>
						{!canGoNext && !isLastStep && (
							<span className="text-xs text-muted-foreground">
								{t("stepperView.completeToContinue")}
							</span>
						)}
					</div>
					<div className="flex items-center gap-1">
						<Button
							variant="outline"
							size="sm"
							onClick={goPrev}
							disabled={currentIndex <= 0}
							title={t("stepperView.previousTask")}
						>
							<ChevronLeft className="h-4 w-4" />
							<span className="hidden sm:inline">{t("stepperView.previous")}</span>
						</Button>
						<Button
							variant="outline"
							size="sm"
							onClick={goNext}
							disabled={!canGoNext}
							title={canGoNext ? t("stepperView.nextTask") : t("stepperView.completeToContinue")}
						>
							<span className="hidden sm:inline">{t("stepperView.next")}</span>
							<ChevronRight className="h-4 w-4" />
						</Button>
					</div>
				</div>
			</div>

			{/* Current step content */}
			<div className="flex-1 overflow-y-auto">
				<div className="mx-auto w-full max-w-2xl space-y-4 p-4">
					<StepCard
						key={currentTask.id}
						task={currentTask}
						allTasks={board.tasks}
						boardId={board.id}
						onSetStatus={(status) => setTaskStatus(currentTask, status)}
						onToggleSubtask={(subtaskId, completed) =>
							handleToggleSubtask(currentTask, subtaskId, completed)
						}
					/>
				</div>
			</div>

			<Celebration show={showCelebration} />
		</div>
	);
}
