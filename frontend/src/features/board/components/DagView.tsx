import { Background, Controls, MiniMap, type NodeMouseHandler, ReactFlow } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { useSubtaskMutations } from "../hooks/use-subtask-mutations";
import { useTaskDetailPanel } from "../hooks/use-task-detail-panel";
import { useTaskMutations } from "../hooks/use-task-mutations";
import type { BoardResponse, TaskResponse } from "../types";
import { getLayoutedElements } from "../utils/dagre-layout";
import { Celebration } from "./Celebration";
import { GoalNode } from "./GoalNode";
import { TaskDetailPanel } from "./TaskDetailPanel";
import { TaskNode } from "./TaskNode";

const nodeTypes = {
	taskNode: TaskNode,
	goalNode: GoalNode,
};

interface DagViewProps {
	board: BoardResponse;
}

export function DagView({ board }: DagViewProps) {
	const { updateTask, deleteTask } = useTaskMutations(board.id);
	const { createSubtask, updateSubtask, deleteSubtask } = useSubtaskMutations(board.id);
	const { selectedTaskId, openTask, closeTask } = useTaskDetailPanel();
	const [showCelebration, setShowCelebration] = useState(false);
	const prevIsCompleted = useRef(board.is_completed);

	// Check if board just became completed
	if (board.is_completed && !prevIsCompleted.current) {
		setShowCelebration(true);
	}
	prevIsCompleted.current = board.is_completed;

	const { nodes, edges } = useMemo(() => getLayoutedElements(board), [board]);

	const selectedTask = useMemo(() => {
		if (!selectedTaskId) return null;
		return board.tasks.find((t) => t.id === selectedTaskId) ?? null;
	}, [selectedTaskId, board.tasks]);

	const onNodeClick: NodeMouseHandler = useCallback(
		(_event, node) => {
			openTask(node.id);
		},
		[openTask],
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
				<Background />
				<Controls showInteractive={false} />
				<MiniMap nodeStrokeWidth={3} pannable zoomable className="!bottom-4 !right-4" />
			</ReactFlow>

			{/* Task Detail Panel */}
			{selectedTask && (
				<TaskDetailPanel
					task={selectedTask}
					allTasks={board.tasks}
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
