import type { Edge, Node } from "@xyflow/react";
import dagre from "dagre";
import type { BoardResponse, TaskResponse } from "../types";

const NODE_WIDTH = 280;
const NODE_HEIGHT = 100;
const GOAL_NODE_WIDTH = 320;
const GOAL_NODE_HEIGHT = 120;

export interface TaskNodeData {
	task: TaskResponse;
	allTasks: TaskResponse[];
	[key: string]: unknown;
}

export function getLayoutedElements(board: BoardResponse): {
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
	for (const task of board.tasks) {
		const width = task.is_goal_node ? GOAL_NODE_WIDTH : NODE_WIDTH;
		const height = task.is_goal_node ? GOAL_NODE_HEIGHT : NODE_HEIGHT;
		g.setNode(task.id, { width, height });
	}

	// Add edges
	for (const edge of board.edges) {
		g.setEdge(edge.source, edge.target);
	}

	dagre.layout(g);

	const nodes: Node<TaskNodeData>[] = board.tasks.map((task) => {
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
				allTasks: board.tasks,
			},
		};
	});

	const edges: Edge[] = board.edges.map((edge) => {
		const targetTask = board.tasks.find((t) => t.id === edge.target);
		const isLocked = targetTask?.is_locked ?? false;

		return {
			id: `${edge.source}-${edge.target}`,
			source: edge.source,
			target: edge.target,
			type: "default",
			animated: false,
			style: {
				stroke: isLocked ? "#9ca3af" : "#6366f1",
				strokeWidth: 2,
				opacity: isLocked ? 0.4 : 0.8,
			},
			markerEnd: {
				type: "arrowclosed" as const,
				color: isLocked ? "#9ca3af" : "#6366f1",
			},
		};
	});

	return { nodes, edges };
}
