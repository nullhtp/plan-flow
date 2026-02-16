import {
	closestCorners,
	DndContext,
	type DragEndEvent,
	type DragOverEvent,
	DragOverlay,
	type DragStartEvent,
	KeyboardSensor,
	PointerSensor,
	useSensor,
	useSensors,
} from "@dnd-kit/core";
import { horizontalListSortingStrategy, SortableContext } from "@dnd-kit/sortable";
import { generateKeyBetween } from "fractional-indexing";
import { useCallback, useMemo, useState } from "react";
import { useColumnMutations } from "../hooks/use-column-mutations";
import { useMoveColumn } from "../hooks/use-move-column";
import { useMoveTask } from "../hooks/use-move-task";
import { useSubtaskMutations } from "../hooks/use-subtask-mutations";
import { useTaskDetailPanel } from "../hooks/use-task-detail-panel";
import { useTaskMutations } from "../hooks/use-task-mutations";
import type { BoardResponse, ColumnResponse } from "../types";
import { AddColumnButton } from "./AddColumnButton";
import { BoardColumn } from "./BoardColumn";
import { DeleteColumnDialog } from "./DeleteColumnDialog";
import { TaskCard } from "./TaskCard";
import { TaskDetailPanel } from "./TaskDetailPanel";

interface BoardViewProps {
	board: BoardResponse;
}

export function BoardView({ board }: BoardViewProps) {
	const { createColumn, updateColumn, deleteColumn } = useColumnMutations(board.id);
	const { createTask, updateTask, deleteTask } = useTaskMutations(board.id);
	const { createSubtask, updateSubtask, deleteSubtask } = useSubtaskMutations(board.id);
	const moveTask = useMoveTask(board.id);
	const moveColumn = useMoveColumn(board.id);
	const { selectedTaskId, openTask, closeTask } = useTaskDetailPanel();

	const [activeId, setActiveId] = useState<string | null>(null);
	const [activeType, setActiveType] = useState<"column" | "task" | null>(null);
	const [deleteColumnTarget, setDeleteColumnTarget] = useState<ColumnResponse | null>(null);

	const sensors = useSensors(
		useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
		useSensor(KeyboardSensor),
	);

	const columns = board.columns;
	const columnIds = useMemo(() => columns.map((c) => c.id), [columns]);

	// Find the selected task across all columns
	const selectedTask = useMemo(() => {
		if (!selectedTaskId) return null;
		for (const col of columns) {
			const task = col.tasks.find((t) => t.id === selectedTaskId);
			if (task) return { task, columnId: col.id };
		}
		return null;
	}, [selectedTaskId, columns]);

	// Find which column a task belongs to
	const findColumnForTask = useCallback(
		(taskId: string): ColumnResponse | undefined => {
			return columns.find((col) => col.tasks.some((t) => t.id === taskId));
		},
		[columns],
	);

	// DnD handlers
	const handleDragStart = (event: DragStartEvent) => {
		const { active } = event;
		const data = active.data.current;
		setActiveId(active.id as string);
		setActiveType(data?.type ?? null);
	};

	const handleDragEnd = (event: DragEndEvent) => {
		const { active, over } = event;
		setActiveId(null);
		setActiveType(null);

		if (!over || active.id === over.id) return;

		const activeData = active.data.current;

		if (activeData?.type === "column") {
			// Column reorder
			const oldIndex = columns.findIndex((c) => c.id === active.id);
			const newIndex = columns.findIndex((c) => c.id === over.id);
			if (oldIndex === -1 || newIndex === -1 || oldIndex === newIndex) return;

			const sorted = [...columns].sort((a, b) => a.position.localeCompare(b.position));
			const before =
				newIndex > 0 ? sorted[newIndex > oldIndex ? newIndex : newIndex - 1]?.position : null;
			const after =
				newIndex < sorted.length - 1
					? sorted[newIndex > oldIndex ? newIndex + 1 : newIndex]?.position
					: null;

			let newPosition: string;
			try {
				newPosition = generateKeyBetween(
					newIndex === 0 && newIndex < oldIndex ? null : (before ?? null),
					newIndex === sorted.length - 1 && newIndex > oldIndex ? null : (after ?? null),
				);
			} catch {
				newPosition = generateKeyBetween(before ?? null, after ?? null);
			}

			moveColumn.mutate({ columnId: active.id as string, data: { position: newPosition } });
		} else if (activeData?.type === "task") {
			// Task reorder or move
			const sourceCol = findColumnForTask(active.id as string);
			if (!sourceCol) return;

			// Determine target column and position
			const overData = over.data.current;
			let targetColId: string;
			let overIndex: number;

			if (overData?.type === "column") {
				// Dropped on a column header — move to end of that column
				targetColId = over.id as string;
				const targetCol = columns.find((c) => c.id === targetColId);
				overIndex = targetCol?.tasks.length ?? 0;
			} else {
				// Dropped on another task
				const targetCol = findColumnForTask(over.id as string);
				if (!targetCol) return;
				targetColId = targetCol.id;
				overIndex = targetCol.tasks.findIndex((t) => t.id === over.id);
			}

			const targetCol = columns.find((c) => c.id === targetColId);
			if (!targetCol) return;

			const targetTasks = targetCol.tasks.filter((t) => t.id !== active.id);
			const before = overIndex > 0 ? targetTasks[overIndex - 1]?.position : null;
			const after = overIndex < targetTasks.length ? targetTasks[overIndex]?.position : null;

			let newPosition: string;
			try {
				newPosition = generateKeyBetween(before ?? null, after ?? null);
			} catch {
				newPosition = generateKeyBetween(null, null);
			}

			const updates: Record<string, unknown> = { position: newPosition };
			if (targetColId !== sourceCol.id) {
				updates.column_id = targetColId;
			}

			moveTask.mutate({ taskId: active.id as string, data: updates });
		}
	};

	const handleDragOver = (_event: DragOverEvent) => {
		// Could be used for visual feedback during drag
	};

	// Active drag overlay
	const activeColumn = activeType === "column" ? columns.find((c) => c.id === activeId) : null;
	const activeTask =
		activeType === "task" ? columns.flatMap((c) => c.tasks).find((t) => t.id === activeId) : null;

	return (
		<div className="flex h-full flex-col">
			<DndContext
				sensors={sensors}
				collisionDetection={closestCorners}
				onDragStart={handleDragStart}
				onDragEnd={handleDragEnd}
				onDragOver={handleDragOver}
			>
				<div className="flex flex-1 gap-4 overflow-x-auto p-4">
					<SortableContext items={columnIds} strategy={horizontalListSortingStrategy}>
						{columns.map((column) => (
							<BoardColumn
								key={column.id}
								column={column}
								onAddTask={(title) =>
									createTask.mutate({
										columnId: column.id,
										data: { title },
									})
								}
								onTaskClick={openTask}
								onUpdateTitle={(title) =>
									updateColumn.mutate({
										columnId: column.id,
										data: { title },
									})
								}
								onDelete={() => setDeleteColumnTarget(column)}
							/>
						))}
					</SortableContext>
					<AddColumnButton
						onAdd={(title) => createColumn.mutate({ boardId: board.id, data: { title } })}
						isPending={createColumn.isPending}
					/>
				</div>

				<DragOverlay>
					{activeColumn && (
						<BoardColumn
							column={activeColumn}
							onAddTask={() => {}}
							onTaskClick={() => {}}
							onUpdateTitle={() => {}}
							onDelete={() => {}}
							isDragOverlay
						/>
					)}
					{activeTask && <TaskCard task={activeTask} onClick={() => {}} isDragOverlay />}
				</DragOverlay>
			</DndContext>

			{/* Task Detail Panel */}
			{selectedTask && (
				<TaskDetailPanel
					task={selectedTask.task}
					columns={columns}
					currentColumnId={selectedTask.columnId}
					onClose={closeTask}
					onUpdateTask={(data) => updateTask.mutate({ taskId: selectedTask.task.id, data })}
					onDeleteTask={() => {
						deleteTask.mutate({ taskId: selectedTask.task.id });
						closeTask();
					}}
					onToggleSubtask={(subtaskId, completed) =>
						updateSubtask.mutate({ subtaskId, data: { completed } })
					}
					onAddSubtask={(title) =>
						createSubtask.mutate({ taskId: selectedTask.task.id, data: { title } })
					}
					onDeleteSubtask={(subtaskId) => deleteSubtask.mutate({ subtaskId })}
				/>
			)}

			{/* Delete Column Dialog */}
			{deleteColumnTarget && (
				<DeleteColumnDialog
					column={deleteColumnTarget}
					otherColumns={columns.filter((c) => c.id !== deleteColumnTarget.id)}
					onConfirm={(targetColumnId) => {
						deleteColumn.mutate({
							columnId: deleteColumnTarget.id,
							params: targetColumnId ? { target_column_id: targetColumnId } : undefined,
						});
						setDeleteColumnTarget(null);
					}}
					onCancel={() => setDeleteColumnTarget(null)}
				/>
			)}
		</div>
	);
}
