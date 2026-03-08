import type { Edge, Node } from "@xyflow/react";
import dagre from "dagre";
import type { BoardResponse, EdgeResponse, TaskResponse } from "../types";

const NODE_WIDTH = 280;
const NODE_HEIGHT = 100;
const GOAL_NODE_WIDTH = 320;
const GOAL_NODE_HEIGHT = 120;

export interface TaskNodeData {
	task: TaskResponse;
	allTasks: TaskResponse[];
	has_sub_board: boolean;
	[key: string]: unknown;
}

/**
 * Computes dagre layout for the given tasks and edges.
 *
 * @param tasks - Tasks to lay out (may be a filtered subset)
 * @param edges - Edges to lay out (may be a filtered subset)
 * @param allTasks - All tasks on the board (unfiltered), passed into node data
 *                   so the TaskDetailPanel can show full dependency info
 */
export function getLayoutedElements(
	tasks: TaskResponse[],
	edges: EdgeResponse[],
	allTasks: TaskResponse[],
): {
	nodes: Node<TaskNodeData>[];
	edges: Edge[];
} {
	const g = new dagre.graphlib.Graph();
	g.setDefaultEdgeLabel(() => ({}));
	g.setGraph({
		rankdir: "TB",
		nodesep: 40,
		ranksep: 60,
		marginx: 20,
		marginy: 20,
	});

	// Add nodes
	for (const task of tasks) {
		const width = task.is_goal_node ? GOAL_NODE_WIDTH : NODE_WIDTH;
		const height = task.is_goal_node ? GOAL_NODE_HEIGHT : NODE_HEIGHT;
		g.setNode(task.id, { width, height });
	}

	// Add edges
	for (const edge of edges) {
		g.setEdge(edge.source, edge.target);
	}

	dagre.layout(g);

	const nodes: Node<TaskNodeData>[] = tasks.map((task) => {
		const nodeWithPosition = g.node(task.id);
		const width = task.is_goal_node ? GOAL_NODE_WIDTH : NODE_WIDTH;
		const height = task.is_goal_node ? GOAL_NODE_HEIGHT : NODE_HEIGHT;

		return {
			id: task.id,
			type: task.is_goal_node ? "goalNode" : "taskNode",
			position: {
				x: nodeWithPosition.x - width / 2,
				y: nodeWithPosition.y - height / 2,
			},
			data: {
				task,
				allTasks,
				has_sub_board: !!task.sub_board_id,
			},
		};
	});

	const layoutEdges: Edge[] = edges.map((edge) => {
		const targetTask = tasks.find((t) => t.id === edge.target);
		const isLocked = targetTask?.is_locked ?? false;

		return {
			id: `${edge.source}-${edge.target}`,
			source: edge.source,
			target: edge.target,
			type: "default",
			animated: false,
			style: {
				stroke: isLocked ? "#d1d5db" : "#818cf8",
				strokeWidth: isLocked ? 1.5 : 3,
			},
			markerEnd: {
				type: "arrowclosed" as const,
				color: isLocked ? "#d1d5db" : "#818cf8",
			},
		};
	});

	return { nodes, edges: layoutEdges };
}

/**
 * Convenience wrapper that takes a full BoardResponse (backward-compatible).
 */
export function getLayoutedElementsFromBoard(board: BoardResponse) {
	return getLayoutedElements(board.tasks, board.edges, board.tasks);
}
