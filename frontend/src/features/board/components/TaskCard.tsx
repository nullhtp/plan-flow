import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Calendar, Clock, GripVertical } from "lucide-react";
import type { TaskResponse } from "@/features/board/types";

interface TaskCardProps {
	task: TaskResponse;
	onClick: () => void;
	isDragOverlay?: boolean;
}

export function TaskCard({ task, onClick, isDragOverlay }: TaskCardProps) {
	const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
		id: task.id,
		data: { type: "task", columnId: task.id },
	});

	const style = {
		transform: CSS.Transform.toString(transform),
		transition,
		opacity: isDragging ? 0.5 : 1,
	};

	const subtaskCount = task.subtasks?.length ?? 0;
	const completedSubtasks = task.subtasks?.filter((s) => s.completed).length ?? 0;

	const priorityColors: Record<string, string> = {
		high: "bg-red-500",
		medium: "bg-yellow-500",
		low: "bg-blue-500",
	};

	return (
		<button
			type="button"
			ref={isDragOverlay ? undefined : setNodeRef}
			style={isDragOverlay ? undefined : style}
			className={`group w-full cursor-pointer rounded-md border bg-card p-3 text-left shadow-sm transition-shadow hover:shadow-md ${isDragOverlay ? "shadow-lg rotate-2" : ""}`}
			onClick={onClick}
		>
			<div className="flex items-start gap-2">
				<span
					className="mt-0.5 shrink-0 cursor-grab opacity-0 group-hover:opacity-100 touch-none"
					{...attributes}
					{...listeners}
				>
					<GripVertical className="h-4 w-4 text-muted-foreground" />
				</span>
				<div className="min-w-0 flex-1">
					<p className="text-sm font-medium leading-tight">{task.title}</p>
					<div className="mt-2 flex flex-wrap items-center gap-2">
						{task.priority && (
							<span
								className={`inline-block h-2 w-2 rounded-full ${priorityColors[task.priority] ?? "bg-gray-400"}`}
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
		</button>
	);
}
