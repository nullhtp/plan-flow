import { Handle, Position } from "@xyflow/react";
import { Calendar, CheckCircle2, Circle, Clock, Lock, PlayCircle } from "lucide-react";
import type { TaskNodeData } from "../utils/dagre-layout";

const priorityDots: Record<string, string> = {
	high: "bg-rose-400",
	medium: "bg-amber-400",
	low: "bg-sky-400",
};

const statusIcons = {
	not_started: <Circle className="h-4 w-4 text-gray-400" />,
	in_progress: <PlayCircle className="h-4 w-4 text-blue-500" />,
	done: <CheckCircle2 className="h-4 w-4 text-emerald-500" />,
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

	// Status-based coloring: done = green, in_progress = blue, not_started = gray
	const statusClass =
		task.status === "done"
			? "border-emerald-400 bg-emerald-50/80 dark:bg-emerald-950/20"
			: task.status === "in_progress"
				? "border-blue-400 bg-blue-50/80 dark:bg-blue-950/20"
				: "border-gray-300 bg-gray-50/80 dark:bg-gray-900/20";

	return (
		<div
			className={`relative rounded-3xl border-2 px-4 py-3 shadow-md cursor-pointer transition-all duration-300 ease-in-out ${statusClass} ${
				isLocked ? "opacity-60" : ""
			}`}
			style={{ width: 280 }}
			title={isLocked ? `Blocked by: ${blockedByNames.join(", ")}` : undefined}
		>
			{/* Hidden handles — required by React Flow internally */}
			<Handle type="target" position={Position.Top} className="!opacity-0 !w-0 !h-0" />

			<div className="flex items-start gap-2.5">
				<div className="mt-0.5 shrink-0">
					{isLocked ? (
						<Lock className="h-4 w-4 text-gray-400" />
					) : (
						(statusIcons[task.status as keyof typeof statusIcons] ?? statusIcons.not_started)
					)}
				</div>
				<div className="min-w-0 flex-1">
					<p
						className={`text-sm font-semibold leading-snug tracking-tight ${
							task.status === "done" ? "line-through text-muted-foreground" : ""
						}`}
					>
						{task.title}
					</p>
					<div className="mt-2 flex flex-wrap items-center gap-2.5">
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

			<Handle type="source" position={Position.Bottom} className="!opacity-0 !w-0 !h-0" />
		</div>
	);
}
