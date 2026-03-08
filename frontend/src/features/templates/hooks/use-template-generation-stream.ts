import { useCallback, useEffect, useRef, useState } from "react";
import { fetchSSE } from "@/api/sse";

/**
 * Template generation stream hook.
 *
 * Unlike useBoardGenerationStream, this hook captures the full task/edge data
 * from SSE events so the preview step can render an editable DAG.
 */

export type TemplateStreamPhase =
	| "idle"
	| "connecting"
	| "researching"
	| "skeleton"
	| "enriching"
	| "complete"
	| "error";

export interface StreamLogEntry {
	id: string;
	message: string;
	type: "info" | "success" | "error";
	timestamp: number;
}

export interface StreamedTemplateTask {
	id: string;
	title: string;
	depends_on: string[];
	is_goal_node: boolean;
	description: string;
	priority: string | null;
	estimated_minutes: number | null;
	subtasks: { title: string }[];
}

export interface StreamedEdge {
	source: string;
	target: string;
}

export interface ResearchProgress {
	queriesCompleted: number;
	totalQueries: number;
	currentQuery: string | null;
	totalResults: number;
	urlsFetched: number;
}

interface StreamState {
	phase: TemplateStreamPhase;
	boardTitle: string | null;
	log: StreamLogEntry[];
	enrichedCount: number;
	totalCount: number;
	error: string | null;
	researchProgress: ResearchProgress | null;
	tasks: StreamedTemplateTask[];
	edges: StreamedEdge[];
}

const initialState: StreamState = {
	phase: "idle",
	boardTitle: null,
	log: [],
	enrichedCount: 0,
	totalCount: 0,
	error: null,
	researchProgress: null,
	tasks: [],
	edges: [],
};

let logIdCounter = 0;
function nextLogId(): string {
	return `tlog-${++logIdCounter}`;
}

function addLog(
	prev: StreamState,
	message: string,
	type: StreamLogEntry["type"] = "info",
): StreamLogEntry[] {
	return [{ id: nextLogId(), message, type, timestamp: Date.now() }, ...prev.log];
}

// ── SSE event payload types ──

interface ResearchStartedData {
	query_count: number;
}

interface ResearchProgressData {
	query: string;
	results_count: number;
	queries_completed: number;
}

interface ResearchCompleteData {
	total_results: number;
	total_queries: number;
	urls_fetched: number;
}

interface SkeletonReadyData {
	board_title: string;
	tasks: Array<{
		id: string;
		title: string;
		depends_on: string[];
		is_goal_node: boolean;
	}>;
	edges: Array<{ source: string; target: string }>;
}

interface TaskEnrichedData {
	task_id: string;
	title?: string;
	description: string;
	priority: string | null;
	estimated_minutes: number | null;
	subtasks: Array<{ title: string }>;
}

interface GenerationErrorData {
	error: string;
	message?: string;
}

interface UseTemplateGenerationStreamOptions {
	sseUrl: string;
	sseBody: unknown;
}

export function useTemplateGenerationStream({
	sseUrl,
	sseBody,
}: UseTemplateGenerationStreamOptions) {
	const [state, setState] = useState<StreamState>(initialState);
	const abortRef = useRef<AbortController | null>(null);
	// Skeleton task map for merging enrichment data
	const skeletonTaskMapRef = useRef<Map<string, StreamedTemplateTask>>(new Map());

	useEffect(() => {
		return () => {
			abortRef.current?.abort();
		};
	}, []);

	const start = useCallback(() => {
		abortRef.current?.abort();
		const controller = new AbortController();
		abortRef.current = controller;
		skeletonTaskMapRef.current = new Map();

		setState({
			...initialState,
			phase: "connecting",
			log: [
				{
					id: nextLogId(),
					message: "Connecting to generation service...",
					type: "info",
					timestamp: Date.now(),
				},
			],
		});

		fetchSSE({
			url: sseUrl,
			body: sseBody,
			signal: controller.signal,
			onEvent: (event) => {
				switch (event.event) {
					case "research_started": {
						const data = event.data as ResearchStartedData;
						setState((prev) => ({
							...prev,
							phase: "researching",
							researchProgress: {
								queriesCompleted: 0,
								totalQueries: data.query_count,
								currentQuery: null,
								totalResults: 0,
								urlsFetched: 0,
							},
							log: addLog(prev, `Researching (${data.query_count} searches)...`, "info"),
						}));
						break;
					}
					case "research_progress": {
						const data = event.data as ResearchProgressData;
						setState((prev) => ({
							...prev,
							researchProgress: prev.researchProgress
								? {
										...prev.researchProgress,
										queriesCompleted: data.queries_completed,
										currentQuery: data.query,
										totalResults: prev.researchProgress.totalResults + data.results_count,
									}
								: null,
							log: addLog(prev, `Searching: ${data.query}`, "info"),
						}));
						break;
					}
					case "research_complete": {
						const data = event.data as ResearchCompleteData;
						setState((prev) => ({
							...prev,
							phase: "skeleton",
							researchProgress: prev.researchProgress
								? {
										...prev.researchProgress,
										queriesCompleted: data.total_queries,
										totalResults: data.total_results,
										urlsFetched: data.urls_fetched,
										currentQuery: null,
									}
								: null,
							log: addLog(prev, `Research complete: ${data.total_results} results`, "success"),
						}));
						break;
					}
					case "skeleton_ready": {
						const data = event.data as SkeletonReadyData;
						// Build initial task objects from skeleton
						const tasks: StreamedTemplateTask[] = data.tasks.map((t) => ({
							id: t.id,
							title: t.title,
							depends_on: t.depends_on,
							is_goal_node: t.is_goal_node,
							description: "",
							priority: null,
							estimated_minutes: null,
							subtasks: [],
						}));
						// Store in ref for enrichment merging
						for (const task of tasks) {
							skeletonTaskMapRef.current.set(task.id, task);
						}
						setState((prev) => ({
							...prev,
							phase: "enriching",
							boardTitle: data.board_title,
							totalCount: data.tasks.length,
							enrichedCount: 0,
							tasks,
							edges: data.edges,
							log: [
								{
									id: nextLogId(),
									message: `Created ${data.tasks.length} tasks — adding details...`,
									type: "success",
									timestamp: Date.now(),
								},
								{
									id: nextLogId(),
									message: `Template structure ready: ${data.board_title}`,
									type: "success",
									timestamp: Date.now(),
								},
								...prev.log,
							],
						}));
						break;
					}
					case "task_enriched": {
						const data = event.data as TaskEnrichedData;
						// Merge enrichment data into the skeleton task
						const existing = skeletonTaskMapRef.current.get(data.task_id);
						if (existing) {
							existing.description = data.description;
							existing.priority = data.priority;
							existing.estimated_minutes = data.estimated_minutes;
							existing.subtasks = data.subtasks;
						}
						const title = existing?.title || data.title || "task";
						setState((prev) => ({
							...prev,
							enrichedCount: prev.enrichedCount + 1,
							// Update tasks array with enriched data
							tasks: prev.tasks.map((t) =>
								t.id === data.task_id
									? {
											...t,
											description: data.description,
											priority: data.priority,
											estimated_minutes: data.estimated_minutes,
											subtasks: data.subtasks,
										}
									: t,
							),
							log: addLog(prev, `Enriched: ${title}`, "success"),
						}));
						break;
					}
					case "generation_complete": {
						setState((prev) => ({
							...prev,
							phase: "complete",
							log: addLog(prev, "Template generation complete!", "success"),
						}));
						break;
					}
					case "generation_error": {
						const data = event.data as GenerationErrorData;
						const msg = data.message || data.error;
						setState((prev) => ({
							...prev,
							phase: "error",
							error: msg,
							log: addLog(prev, msg, "error"),
						}));
						break;
					}
				}
			},
			onError: (error) => {
				if (controller.signal.aborted) return;
				const msg = error.message || "Connection failed";
				setState((prev) => ({
					...prev,
					phase: "error",
					error: msg,
					log: addLog(prev, msg, "error"),
				}));
			},
			onClose: () => {
				setState((prev) => {
					if (prev.phase === "complete" || prev.phase === "error") return prev;
					return {
						...prev,
						phase: "error",
						error: "Connection closed unexpectedly",
						log: addLog(prev, "Connection closed unexpectedly", "error"),
					};
				});
			},
		});
	}, [sseUrl, sseBody]);

	const abort = useCallback(() => {
		abortRef.current?.abort();
	}, []);

	return {
		...state,
		start,
		abort,
	};
}
