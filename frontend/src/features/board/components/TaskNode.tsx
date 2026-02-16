import { Handle, Position } from "@xyflow/react";
import { Calendar, CheckCircle2, Circle, Clock, Lock, PlayCircle } from "lucide-react";
import type { TaskNodeData } from "../utils/dagre-layout";

const priorityColors: Record<string, string> = {
	high: "border-red-500 bg-red-50 dark:bg-red-950/20",
	medium: "border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20",
	low: "border-blue-500 bg-blue-50 dark:bg-blue-950/20",
};

const priorityDots: Record<string, string> = {
	high: "bg-red-500",
	medium: "bg-yellow-500",
	low: "bg-blue-500",
};

const statusIcons = {
	not_started: <Circle className="h-4 w-4 text-gray-400" />,
	in_progress: <PlayCircle className="h-4 w-4 text-blue-500" />,
	done: <CheckCircle2 className="h-4 w-4 text-green-500" />,
};

interface TaskNodeProps {
	data: TaskNodeData;
}

export function TaskNode({ data }: TaskNodeProps) {
	const { task, allTasks } = data;
	const isLocked = task.is_locked;
	const subtaskCount = task.subtasks?.length ?? 0;
	const completedSubtasks = task.subtasks?.filter((s) => s.completed).length ?? 0;

	// Get names of incomplete prerequisites for tooltip
	const blockedByNames = isLocked
		? task.dependency_ids
				.map((id) => allTasks.find((t) => t.id === id))
				.filter((t) => t && t.status !== "done")
				.map((t) => t?.title)
		: [];

	const borderClass = task.priority
		? (priorityColors[task.priority] ?? "border-border bg-card")
		: "border-border bg-card";

	return (
		<div
			className={`relative rounded-lg border-2 px-4 py-3 shadow-sm transition-all ${borderClass} ${
				isLocked ? "opacity-50 grayscale" : ""
			} ${task.status === "done" ? "border-green-500/50" : ""}`}
			style={{ width: 280 }}
			title={isLocked ? `Blocked by: ${blockedByNames.join(", ")}` : undefined}
		>
			<Handle type="target" position={Position.Top} className="!bg-indigo-400 !w-2 !h-2" />

			<div className="flex items-start gap-2">
				<div className="mt-0.5 shrink-0">
					{isLocked ? (
						<Lock className="h-4 w-4 text-gray-400" />
					) : (
						(statusIcons[task.status as keyof typeof statusIcons] ?? statusIcons.not_started)
					)}
				</div>
				<div className="min-w-0 flex-1">
					<p
						className={`text-sm font-medium leading-tight ${
							task.status === "done" ? "line-through text-muted-foreground" : ""
						}`}
					>
						{task.title}
					</p>
					<div className="mt-1.5 flex flex-wrap items-center gap-2">
						{task.priority && (
							<span
								className={`inline-block h-2 w-2 rounded-full ${priorityDots[task.priority] ?? "bg-gray-400"}`}
								title={task.priority}
							/>
						)}
						{task.due_date && (
							<span className="flex items-center gap-1 text-xs text-muted-foreground">
								<Calendar className="h-3 w-3" />
								{task.due_date}
							</span>
						)}
						{task.estimated_minutes && (
							<span className="flex items-center gap-1 text-xs text-muted-foreground">
								<Clock className="h-3 w-3" />
								{task.estimated_minutes}m
							</span>
						)}
						{subtaskCount > 0 && (
							<span className="text-xs text-muted-foreground">
								{completedSubtasks}/{subtaskCount}
							</span>
						)}
					</div>
				</div>
			</div>

			<Handle type="source" position={Position.Bottom} className="!bg-indigo-400 !w-2 !h-2" />
		</div>
	);
}
