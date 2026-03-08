import { Controls, MiniMap, type NodeMouseHandler, ReactFlow } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useNavigate } from "@tanstack/react-router";
import { useCallback, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { useSubtaskMutations } from "../hooks/use-subtask-mutations";
import { useTaskDetailPanel } from "../hooks/use-task-detail-panel";
import { useTaskMutations } from "../hooks/use-task-mutations";
import type { BoardResponse, TaskResponse } from "../types";
import { filterBoardForFocusView } from "../utils/board-filters";
import { getLayoutedElements } from "../utils/dagre-layout";
import { Celebration } from "./Celebration";
import { GoalNode } from "./GoalNode";
import { TaskDetailPanel } from "./TaskDetailPanel";
import { TaskNode } from "./TaskNode";

const nodeTypes = {
	taskNode: TaskNode,
	goalNode: GoalNode,
};

export type BoardViewMode = "focus" | "full";

interface DagViewProps {
	board: BoardResponse;
	viewMode: BoardViewMode;
}

export function DagView({ board, viewMode }: DagViewProps) {
	const { updateTask, deleteTask } = useTaskMutations(board.id);
	const { createSubtask, updateSubtask, deleteSubtask } = useSubtaskMutations(board.id);
	const { selectedTaskId, openTask, closeTask } = useTaskDetailPanel();
	const [showCelebration, setShowCelebration] = useState(false);
	const prevIsCompleted = useRef(board.is_completed);
	const navigate = useNavigate();

	// Check if board just became completed
	if (board.is_completed && !prevIsCompleted.current) {
		setShowCelebration(true);
	}
	prevIsCompleted.current = board.is_completed;

	const { nodes, edges } = useMemo(() => {
		if (viewMode === "focus") {
			const filtered = filterBoardForFocusView(board.tasks, board.edges);
			return getLayoutedElements(filtered.tasks, filtered.edges, board.tasks);
		}
		return getLayoutedElements(board.tasks, board.edges, board.tasks);
	}, [board, viewMode]);

	const selectedTask = useMemo(() => {
		if (!selectedTaskId) return null;
		return board.tasks.find((t) => t.id === selectedTaskId) ?? null;
	}, [selectedTaskId, board.tasks]);

	const onNodeClick: NodeMouseHandler = useCallback(
		(_event, node) => {
			// If the task has a sub-board, navigate to it instead of opening the detail panel
			const task = board.tasks.find((t) => t.id === node.id);
			if (task?.sub_board_id) {
				navigate({ to: "/boards/$boardId", params: { boardId: task.sub_board_id } });
				return;
			}
			openTask(node.id);
		},
		[openTask, board.tasks, navigate],
	);

	const handleStatusToggle = useCallback(
		(task: TaskResponse) => {
			if (task.is_locked) {
				toast.info("Complete prerequisites first");
				return;
			}

			let newStatus: string;
			if (task.status === "not_started") {
				newStatus = "in_progress";
			} else if (task.status === "in_progress") {
				newStatus = "done";
			} else {
				// done -> not_started (allow undo)
				newStatus = "not_started";
			}

			updateTask.mutate({ taskId: task.id, data: { status: newStatus } });
		},
		[updateTask],
	);

	return (
		<div className="h-full w-full relative">
			<ReactFlow
				nodes={nodes}
				edges={edges}
				nodeTypes={nodeTypes}
				onNodeClick={onNodeClick}
				fitView
				fitViewOptions={{ padding: 0.2 }}
				nodesDraggable={false}
				nodesConnectable={false}
				elementsSelectable={true}
				minZoom={0.3}
				maxZoom={1.5}
				proOptions={{ hideAttribution: true }}
			>
				<Controls showInteractive={false} />
				<MiniMap
					nodeStrokeWidth={3}
					nodeColor="#818cf8"
					nodeStrokeColor="#6366f1"
					maskColor="rgba(0, 0, 0, 0.08)"
					pannable
					zoomable
					className="!bottom-4 !right-4 !rounded-xl !shadow-md !border !border-border"
				/>
			</ReactFlow>

			{/* Task Detail Panel */}
			{selectedTask && (
				<TaskDetailPanel
					task={selectedTask}
					allTasks={board.tasks}
					boardId={board.id}
					isSubBoard={!!board.parent_task_id}
					onClose={closeTask}
					onUpdateTask={(data) => updateTask.mutate({ taskId: selectedTask.id, data })}
					onDeleteTask={() => {
						deleteTask.mutate({ taskId: selectedTask.id });
						closeTask();
					}}
					onStatusToggle={() => handleStatusToggle(selectedTask)}
					onToggleSubtask={(subtaskId, completed) =>
						updateSubtask.mutate({ subtaskId, data: { completed } })
					}
					onAddSubtask={(title) =>
						createSubtask.mutate({ taskId: selectedTask.id, data: { title } })
					}
					onDeleteSubtask={(subtaskId) => deleteSubtask.mutate({ subtaskId })}
				/>
			)}

			{/* Goal completion celebration */}
			<Celebration show={showCelebration} />
		</div>
	);
}
