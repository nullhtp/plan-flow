import type { TFunction } from "i18next";
import { useCallback, useEffect, useRef, useState } from "react";
import { fetchSSE } from "@/api/sse";

export type GenerationPhase =
	| "idle"
	| "connecting"
	| "researching"
	| "skeleton"
	| "enriching"
	| "complete"
	| "error";

export interface LogEntry {
	id: string;
	message: string;
	type: "info" | "success" | "error";
	timestamp: number;
}

export interface ResearchProgress {
	queriesCompleted: number;
	totalQueries: number;
	currentQuery: string | null;
	totalResults: number;
	urlsFetched: number;
}

interface GenerationState {
	phase: GenerationPhase;
	boardTitle: string | null;
	log: LogEntry[];
	enrichedCount: number;
	totalCount: number;
	boardId: string | null;
	error: string | null;
	researchProgress: ResearchProgress | null;
}

const initialState: GenerationState = {
	phase: "idle",
	boardTitle: null,
	log: [],
	enrichedCount: 0,
	totalCount: 0,
	boardId: null,
	error: null,
	researchProgress: null,
};

let logIdCounter = 0;
function nextLogId(): string {
	return `log-${++logIdCounter}`;
}

function addLog(
	prev: GenerationState,
	message: string,
	type: LogEntry["type"] = "info",
): LogEntry[] {
	return [{ id: nextLogId(), message, type, timestamp: Date.now() }, ...prev.log];
}

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
	board_id: string;
	board_title: string;
	tasks: Array<{ id: string; title: string; is_goal_node: boolean }>;
}

interface TaskEnrichedData {
	task_id: string;
	title: string;
}

interface GenerationCompleteData {
	board_id: string;
	failed_tasks: string[];
}

interface GenerationErrorData {
	error: string;
}

interface UseBoardGenerationStreamOptions {
	/** The SSE endpoint URL (e.g. `/api/goals/{id}/generate-board/stream`) */
	url: string;
	/** Optional JSON body to send with the POST request */
	body?: unknown;
	/** Translation function from the "goals" namespace for user-facing log messages. */
	t: TFunction<"goals">;
}

export function useBoardGenerationStream({ url, body, t }: UseBoardGenerationStreamOptions) {
	const [state, setState] = useState<GenerationState>(initialState);
	const abortRef = useRef<AbortController | null>(null);
	// Keep a ref to task map so we can resolve titles in task_enriched
	const taskMapRef = useRef<Map<string, string>>(new Map());

	// Cleanup on unmount
	useEffect(() => {
		return () => {
			abortRef.current?.abort();
		};
	}, []);

	const start = useCallback(() => {
		// Abort any existing connection
		abortRef.current?.abort();

		const controller = new AbortController();
		abortRef.current = controller;
		taskMapRef.current = new Map();

		const connectingState: GenerationState = {
			...initialState,
			phase: "connecting",
			log: [
				{
					id: nextLogId(),
					message: t("stream.connecting"),
					type: "info",
					timestamp: Date.now(),
				},
			],
		};
		setState(connectingState);

		fetchSSE({
			url,
			body,
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
							log: addLog(prev, t("stream.researchingGoal", { count: data.query_count }), "info"),
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
							log: addLog(prev, t("stream.searching", { query: data.query }), "info"),
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
							log: addLog(
								prev,
								t("stream.researchComplete", {
									results: data.total_results,
									queries: data.total_queries,
								}),
								"success",
							),
						}));
						break;
					}
					case "skeleton_ready": {
						const data = event.data as SkeletonReadyData;
						// Store task map for resolving titles later
						for (const t of data.tasks) {
							taskMapRef.current.set(t.id, t.title);
						}
						setState((prev) => ({
							...prev,
							phase: "enriching",
							boardTitle: data.board_title,
							boardId: data.board_id,
							totalCount: data.tasks.length,
							enrichedCount: 0,
							log: [
								{
									id: nextLogId(),
									message: t("stream.createdTasks", { count: data.tasks.length }),
									type: "success",
									timestamp: Date.now(),
								},
								{
									id: nextLogId(),
									message: t("stream.boardStructureReady", { title: data.board_title }),
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
						const title =
							taskMapRef.current.get(data.task_id) || data.title || t("stream.fallbackTask");
						setState((prev) => ({
							...prev,
							enrichedCount: prev.enrichedCount + 1,
							log: addLog(prev, t("stream.enriched", { title }), "success"),
						}));
						break;
					}
					case "generation_complete": {
						const data = event.data as GenerationCompleteData;
						setState((prev) => ({
							...prev,
							phase: "complete",
							boardId: data.board_id || prev.boardId,
							log: addLog(prev, t("stream.generationComplete"), "success"),
						}));
						break;
					}
					case "generation_error": {
						const data = event.data as GenerationErrorData;
						setState((prev) => ({
							...prev,
							phase: "error",
							error: data.error,
							log: addLog(prev, data.error, "error"),
						}));
						break;
					}
				}
			},
			onError: (error) => {
				if (controller.signal.aborted) return;
				const msg = error.message || t("stream.connectionFailed");
				setState((prev) => ({
					...prev,
					phase: "error",
					error: prev.boardId ? t("stream.connectionLost") : msg,
					log: addLog(prev, msg, "error"),
				}));
			},
			onClose: () => {
				setState((prev) => {
					if (prev.phase === "complete" || prev.phase === "error") return prev;
					const msg = prev.boardId ? t("stream.connectionLost") : t("stream.connectionClosed");
					return {
						...prev,
						phase: "error",
						error: msg,
						log: addLog(prev, msg, "error"),
					};
				});
			},
		});
	}, [url, body, t]);

	const abort = useCallback(() => {
		abortRef.current?.abort();
	}, []);

	return {
		...state,
		start,
		abort,
	};
}
