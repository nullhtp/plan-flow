import { SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { type KeyboardEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ColumnResponse } from "@/features/board/types";
import { AddTaskButton } from "./AddTaskButton";
import { TaskCard } from "./TaskCard";

interface BoardColumnProps {
	column: ColumnResponse;
	onAddTask: (title: string) => void;
	onTaskClick: (taskId: string) => void;
	onUpdateTitle: (title: string) => void;
	onDelete: () => void;
	isDragOverlay?: boolean;
}

export function BoardColumn({
	column,
	onAddTask,
	onTaskClick,
	onUpdateTitle,
	onDelete,
	isDragOverlay,
}: BoardColumnProps) {
	const [isEditingTitle, setIsEditingTitle] = useState(false);
	const [editTitle, setEditTitle] = useState(column.title);
	const [showMenu, setShowMenu] = useState(false);

	const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
		id: column.id,
		data: { type: "column" },
	});

	const style = {
		transform: CSS.Transform.toString(transform),
		transition,
		opacity: isDragging ? 0.5 : 1,
	};

	const taskIds = column.tasks.map((t) => t.id);

	const handleTitleSubmit = () => {
		const trimmed = editTitle.trim();
		if (trimmed && trimmed !== column.title) {
			onUpdateTitle(trimmed);
		}
		setIsEditingTitle(false);
	};

	const handleTitleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
		if (e.key === "Enter") handleTitleSubmit();
		if (e.key === "Escape") {
			setEditTitle(column.title);
			setIsEditingTitle(false);
		}
	};

	return (
		<div
			ref={isDragOverlay ? undefined : setNodeRef}
			style={isDragOverlay ? undefined : style}
			className={`flex w-72 shrink-0 flex-col rounded-lg bg-muted/50 ${isDragOverlay ? "shadow-xl rotate-2" : ""}`}
		>
			{/* Column Header */}
			<div className="flex items-center gap-1 p-3 pb-2">
				<button
					type="button"
					className="shrink-0 cursor-grab touch-none"
					{...attributes}
					{...listeners}
				>
					<GripVertical className="h-4 w-4 text-muted-foreground" />
				</button>
				{isEditingTitle ? (
					<Input
						autoFocus
						value={editTitle}
						onChange={(e) => setEditTitle(e.target.value)}
						onKeyDown={handleTitleKeyDown}
						onBlur={handleTitleSubmit}
						className="h-7 text-sm font-semibold"
					/>
				) : (
					<h3
						className="flex-1 cursor-pointer truncate text-sm font-semibold"
						onDoubleClick={() => setIsEditingTitle(true)}
					>
						{column.title}
					</h3>
				)}
				<span className="shrink-0 text-xs text-muted-foreground">{column.tasks.length}</span>
				<div className="relative">
					<Button
						variant="ghost"
						size="sm"
						className="h-6 w-6 p-0"
						onClick={() => setShowMenu(!showMenu)}
					>
						<MoreHorizontal className="h-4 w-4" />
					</Button>
					{showMenu && (
						<div className="absolute right-0 top-full z-10 mt-1 w-36 rounded-md border bg-card py-1 shadow-lg">
							<button
								type="button"
								className="flex w-full items-center gap-2 px-3 py-1.5 text-sm hover:bg-muted"
								onClick={() => {
									setIsEditingTitle(true);
									setShowMenu(false);
								}}
							>
								<Pencil className="h-3 w-3" /> Rename
							</button>
							<button
								type="button"
								className="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-destructive hover:bg-muted"
								onClick={() => {
									onDelete();
									setShowMenu(false);
								}}
							>
								<Trash2 className="h-3 w-3" /> Delete
							</button>
						</div>
					)}
				</div>
			</div>

			{/* Task List */}
			<div className="flex flex-1 flex-col gap-2 overflow-y-auto px-2 pb-0">
				<SortableContext items={taskIds} strategy={verticalListSortingStrategy}>
					{column.tasks.map((task) => (
						<TaskCard key={task.id} task={task} onClick={() => onTaskClick(task.id)} />
					))}
				</SortableContext>
			</div>

			{/* Add Task */}
			<AddTaskButton onAdd={onAddTask} />
		</div>
	);
}
