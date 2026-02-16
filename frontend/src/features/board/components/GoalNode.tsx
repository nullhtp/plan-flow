import { Handle, Position } from "@xyflow/react";
import { CheckCircle2, Lock, Trophy } from "lucide-react";
import type { TaskNodeData } from "../utils/dagre-layout";

interface GoalNodeProps {
	data: TaskNodeData;
}

export function GoalNode({ data }: GoalNodeProps) {
	const { task, allTasks } = data;
	const isLocked = task.is_locked;
	const isDone = task.status === "done";

	// Count total tasks and completed tasks (excluding goal node)
	const totalTasks = allTasks.length;
	const completedTasks = allTasks.filter((t) => t.status === "done").length;

	return (
		<div
			className={`relative rounded-3xl border-3 px-5 py-4 shadow-md cursor-pointer transition-all duration-300 ease-in-out ${
				isDone
					? "border-green-500 bg-green-50 dark:bg-green-950/30"
					: isLocked
						? "border-amber-400/50 bg-amber-50/50 opacity-70 dark:bg-amber-950/10"
						: "border-amber-400 bg-amber-50 dark:bg-amber-950/20"
			}`}
			style={{ width: 320 }}
		>
			{/* Hidden handle — required by React Flow internally */}
			<Handle type="target" position={Position.Top} className="!opacity-0 !w-0 !h-0" />

			<div className="flex items-start gap-3">
				<div className="mt-0.5 shrink-0">
					{isDone ? (
						<Trophy className="h-6 w-6 text-green-500" />
					) : isLocked ? (
						<Lock className="h-6 w-6 text-amber-400/60" />
					) : (
						<CheckCircle2 className="h-6 w-6 text-amber-500" />
					)}
				</div>
				<div className="min-w-0 flex-1">
					<p className="text-base font-bold leading-tight">{task.title}</p>
					<div className="mt-2 flex items-center gap-2">
						<div className="flex-1 h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
							<div
								className="h-full rounded-full bg-amber-500 transition-all duration-500"
								style={{
									width: `${totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0}%`,
								}}
							/>
						</div>
						<span className="text-xs font-medium text-muted-foreground whitespace-nowrap">
							{completedTasks}/{totalTasks} tasks
						</span>
					</div>
				</div>
			</div>

			{/* Goal node has no source handle — nothing depends on it */}
		</div>
	);
}
