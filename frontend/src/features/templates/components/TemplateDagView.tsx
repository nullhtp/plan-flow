import {
	type Connection,
	Controls,
	type Edge,
	type EdgeMouseHandler,
	MiniMap,
	type Node,
	type NodeMouseHandler,
	ReactFlow,
	type ReactFlowInstance,
	useEdgesState,
	useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "dagre";
import { AlertTriangle } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { StreamedTemplateTask } from "../hooks/use-template-generation-stream";
import { TemplateGoalNode } from "./TemplateGoalNode";
import { TemplateTaskNode } from "./TemplateTaskNode";

// ── DAG validation (client-side) ──

interface DagValidation {
	valid: boolean;
	warnings: string[];
}

function validateTemplateDag(
	tasks: StreamedTemplateTask[],
	edges: Array<{ source: string; target: string }>,
): DagValidation {
	const warnings: string[] = [];
	const taskIds = new Set(tasks.map((t) => t.id));

	// Check goal node
	const goalNodes = tasks.filter((t) => t.is_goal_node);
	if (goalNodes.length === 0) {
		warnings.push("No goal node found. One task should be marked as the goal.");
	} else if (goalNodes.length > 1) {
		warnings.push(`Multiple goal nodes found (${goalNodes.length}). Only one is allowed.`);
	}

	// Check goal node has no outgoing edges (nothing depends on it)
	if (goalNodes.length === 1) {
		const goalId = goalNodes[0].id;
		const goalHasOutgoing = edges.some((e) => e.source === goalId);
		if (goalHasOutgoing) {
			warnings.push("Goal node should be the final task — nothing should depend on it.");
		}
	}

	// Cycle detection using Kahn's algorithm
	const adj = new Map<string, string[]>();
	const inDegree = new Map<string, number>();
	for (const t of tasks) {
		adj.set(t.id, []);
		inDegree.set(t.id, 0);
	}
	for (const e of edges) {
		if (!taskIds.has(e.source) || !taskIds.has(e.target)) continue;
		adj.get(e.source)!.push(e.target);
		inDegree.set(e.target, (inDegree.get(e.target) ?? 0) + 1);
	}

	// Self-edges
	for (const e of edges) {
		if (e.source === e.target) {
			warnings.push(
				`Self-dependency detected on task "${tasks.find((t) => t.id === e.source)?.title ?? e.source}".`,
			);
		}
	}

	const queue: string[] = [];
	for (const [id, deg] of inDegree) {
		if (deg === 0) queue.push(id);
	}
	let visited = 0;
	while (queue.length > 0) {
		const node = queue.shift()!;
		visited++;
		for (const neighbor of adj.get(node) ?? []) {
			const newDeg = (inDegree.get(neighbor) ?? 1) - 1;
			inDegree.set(neighbor, newDeg);
			if (newDeg === 0) queue.push(neighbor);
		}
	}
	if (visited < tasks.length) {
		warnings.push("Cycle detected in task dependencies. Remove circular edges.");
	}

	// Check for disconnected tasks (no edges at all)
	const connectedIds = new Set<string>();
	for (const e of edges) {
		connectedIds.add(e.source);
		connectedIds.add(e.target);
	}
	const disconnected = tasks.filter((t) => !connectedIds.has(t.id) && tasks.length > 1);
	if (disconnected.length > 0) {
		const names = disconnected.map((t) => `"${t.title}"`).join(", ");
		warnings.push(`Disconnected tasks: ${names}. Connect them with edges.`);
	}

	return { valid: warnings.length === 0, warnings };
}

// ── Layout ──

export interface TemplateTaskNodeData {
	task: StreamedTemplateTask;
	[key: string]: unknown;
}

const NODE_WIDTH = 280;
const NODE_HEIGHT = 100;
const GOAL_NODE_WIDTH = 320;
const GOAL_NODE_HEIGHT = 120;

function layoutTemplateDag(
	tasks: StreamedTemplateTask[],
	taskEdges: Array<{ source: string; target: string }>,
): { nodes: Node<TemplateTaskNodeData>[]; edges: Edge[] } {
	const g = new dagre.graphlib.Graph();
	g.setDefaultEdgeLabel(() => ({}));
	g.setGraph({
		rankdir: "TB",
		nodesep: 40,
		ranksep: 60,
		marginx: 20,
		marginy: 20,
	});

	for (const task of tasks) {
		const width = task.is_goal_node ? GOAL_NODE_WIDTH : NODE_WIDTH;
		const height = task.is_goal_node ? GOAL_NODE_HEIGHT : NODE_HEIGHT;
		g.setNode(task.id, { width, height });
	}

	const taskIds = new Set(tasks.map((t) => t.id));
	for (const edge of taskEdges) {
		if (taskIds.has(edge.source) && taskIds.has(edge.target)) {
			g.setEdge(edge.source, edge.target);
		}
	}

	dagre.layout(g);

	const nodes: Node<TemplateTaskNodeData>[] = tasks.map((task) => {
		const nodeWithPosition = g.node(task.id);
		const width = task.is_goal_node ? GOAL_NODE_WIDTH : NODE_WIDTH;
		const height = task.is_goal_node ? GOAL_NODE_HEIGHT : NODE_HEIGHT;

		return {
			id: task.id,
			type: task.is_goal_node ? "templateGoalNode" : "templateTaskNode",
			position: {
				x: nodeWithPosition.x - width / 2,
				y: nodeWithPosition.y - height / 2,
			},
			data: { task },
		};
	});

	const edges: Edge[] = taskEdges
		.filter((e) => taskIds.has(e.source) && taskIds.has(e.target))
		.map((edge) => ({
			id: `${edge.source}-${edge.target}`,
			source: edge.source,
			target: edge.target,
			type: "default",
			animated: false,
			style: {
				stroke: "#818cf8",
				strokeWidth: 2,
			},
			markerEnd: {
				type: "arrowclosed" as const,
				color: "#818cf8",
			},
		}));

	return { nodes, edges };
}

// ── Node types ──

const nodeTypes = {
	templateTaskNode: TemplateTaskNode,
	templateGoalNode: TemplateGoalNode,
};

// ── Component ──

interface TemplateDagViewProps {
	tasks: StreamedTemplateTask[];
	edges: Array<{ source: string; target: string }>;
	selectedTaskId: string | null;
	onSelectTask: (taskId: string | null) => void;
	onEdgesChange: (edges: Array<{ source: string; target: string }>) => void;
}

export function TemplateDagView({
	tasks,
	edges: taskEdges,
	selectedTaskId,
	onSelectTask,
	onEdgesChange,
}: TemplateDagViewProps) {
	const rfInstanceRef = useRef<ReactFlowInstance | null>(null);
	const [layoutKey, setLayoutKey] = useState(0);

	// Compute layout from tasks/edges
	const layout = useMemo(() => layoutTemplateDag(tasks, taskEdges), [tasks, taskEdges]);

	const [rfNodes, setRfNodes] = useNodesState(layout.nodes);
	const [rfEdges, setRfEdges] = useEdgesState(layout.edges);

	// Sync layout when tasks/edges change externally
	const prevLayoutRef = useRef(layout);
	useEffect(() => {
		if (prevLayoutRef.current !== layout) {
			prevLayoutRef.current = layout;
			setRfNodes(layout.nodes);
			setRfEdges(layout.edges);
			setLayoutKey((k) => k + 1);
		}
	}, [layout, setRfNodes, setRfEdges]);

	// Fit view when layout changes
	useEffect(() => {
		if (rfInstanceRef.current && layoutKey > 0) {
			setTimeout(() => {
				rfInstanceRef.current?.fitView({ padding: 0.2 });
			}, 50);
		}
	}, [layoutKey]);

	// Handle node click
	const onNodeClick: NodeMouseHandler = useCallback(
		(_event, node) => {
			onSelectTask(node.id);
		},
		[onSelectTask],
	);

	// Handle pane click to deselect
	const onPaneClick = useCallback(() => {
		onSelectTask(null);
	}, [onSelectTask]);

	// Handle new connection (edge creation)
	const onConnect = useCallback(
		(connection: Connection) => {
			if (!connection.source || !connection.target) return;
			// Don't allow self-connections
			if (connection.source === connection.target) return;
			// Don't allow duplicate edges
			if (taskEdges.some((e) => e.source === connection.source && e.target === connection.target))
				return;

			const newEdges = [...taskEdges, { source: connection.source, target: connection.target }];
			onEdgesChange(newEdges);
		},
		[taskEdges, onEdgesChange],
	);

	// Handle edge click (delete edge)
	const onEdgeClick: EdgeMouseHandler = useCallback(
		(_event, edge) => {
			const filtered = taskEdges.filter(
				(e) => !(e.source === edge.source && e.target === edge.target),
			);
			onEdgesChange(filtered);
		},
		[taskEdges, onEdgesChange],
	);

	// Highlight selected node
	const styledNodes = useMemo(
		() =>
			rfNodes.map((node) => ({
				...node,
				selected: node.id === selectedTaskId,
			})),
		[rfNodes, selectedTaskId],
	);

	// DAG validation
	const validation = useMemo(() => validateTemplateDag(tasks, taskEdges), [tasks, taskEdges]);

	return (
		<div className="relative h-full w-full">
			<ReactFlow
				key={layoutKey}
				nodes={styledNodes}
				edges={rfEdges}
				nodeTypes={nodeTypes}
				onNodeClick={onNodeClick}
				onPaneClick={onPaneClick}
				onConnect={onConnect}
				onEdgeClick={onEdgeClick}
				onInit={(instance: ReactFlowInstance) => {
					rfInstanceRef.current = instance;
				}}
				fitView
				fitViewOptions={{ padding: 0.2 }}
				nodesDraggable={true}
				nodesConnectable={true}
				elementsSelectable={true}
				minZoom={0.3}
				maxZoom={1.5}
				proOptions={{ hideAttribution: true }}
				deleteKeyCode="Delete"
				defaultEdgeOptions={{
					style: { stroke: "#818cf8", strokeWidth: 2 },
					markerEnd: { type: "arrowclosed" as const, color: "#818cf8" },
				}}
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

			{/* DAG validation warnings */}
			{!validation.valid && (
				<div className="absolute top-3 left-3 z-10 max-w-xs rounded-lg border border-amber-300 bg-amber-50 p-3 shadow-md dark:border-amber-700 dark:bg-amber-950/90">
					<div className="flex items-start gap-2">
						<AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
						<div className="space-y-1">
							{validation.warnings.map((w) => (
								<p key={w} className="text-xs text-amber-800 dark:text-amber-300">
									{w}
								</p>
							))}
						</div>
					</div>
				</div>
			)}

			{/* Edge deletion hint */}
			<div className="absolute bottom-3 left-3 z-10">
				<p className="text-[10px] text-muted-foreground/60">
					Click an edge to delete it. Drag from handle to handle to connect tasks.
				</p>
			</div>
		</div>
	);
}
