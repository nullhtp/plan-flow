import { useNavigate } from "@tanstack/react-router";
import type { TFunction } from "i18next";
import { Check, CircleAlert, CircleDot, Loader2, Search } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import {
	type LogEntry,
	useBoardGenerationStream,
} from "@/features/goals/hooks/use-board-generation-stream";

const MAX_VISIBLE_ENTRIES = 8;
const AUTO_NAV_DELAY_MS = 1500;

interface BoardGenerationProgressProps {
	/** SSE endpoint URL. Defaults to goal-based endpoint if goalId is provided. */
	sseUrl?: string;
	/** Optional JSON body to send with the SSE POST request. */
	sseBody?: unknown;
	/** @deprecated Use sseUrl instead. Goal ID for the default goal-based endpoint. */
	goalId?: string;
	/** Called when user clicks "Back" on error. */
	onAbort?: () => void;
	/** Called when generation completes. If provided, overrides default auto-navigation. */
	onComplete?: (boardId: string) => void;
}

function getPhaseText(
	stream: ReturnType<typeof useBoardGenerationStream>,
	t: TFunction<"goals">,
): string {
	switch (stream.phase) {
		case "idle":
		case "connecting":
			return t("boardProgress.analyzing");
		case "researching": {
			const rp = stream.researchProgress;
			if (rp) {
				return t("boardProgress.researchingProgress", {
					completed: rp.queriesCompleted,
					total: rp.totalQueries,
				});
			}
			return t("boardProgress.researching");
		}
		case "skeleton":
			return t("boardProgress.creatingStructure");
		case "enriching": {
			if (stream.totalCount > 0) {
				return t("boardProgress.addingDetailsProgress", {
					enriched: stream.enrichedCount,
					total: stream.totalCount,
				});
			}
			return t("boardProgress.addingDetails");
		}
		case "complete":
			return t("boardProgress.boardReady");
		case "error":
			return t("boardProgress.generationFailed");
		default:
			return t("boardProgress.generatingBoard");
	}
}

export function BoardGenerationProgress({
	sseUrl,
	sseBody,
	goalId,
	onAbort,
	onComplete,
}: BoardGenerationProgressProps) {
	const { t } = useTranslation("goals");
	const url = sseUrl ?? `/api/goals/${goalId}/generate-board/stream`;
	const streamOptions = useMemo(() => ({ url, body: sseBody, t }), [url, sseBody, t]);
	const stream = useBoardGenerationStream(streamOptions);
	const navigate = useNavigate();
	const navTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

	// Start the stream on mount, abort on unmount.
	// Guard prevents the double-fire caused by React StrictMode's
	// unmount-remount cycle which would send two POST requests to the server.
	const didStart = useRef(false);
	useEffect(() => {
		if (!didStart.current) {
			didStart.current = true;
			stream.start();
		}
		return () => {
			stream.abort();
		};
	}, [stream.start, stream.abort]);

	// Auto-navigate on completion
	useEffect(() => {
		if (stream.phase === "complete" && stream.boardId) {
			if (onComplete) {
				navTimerRef.current = setTimeout(() => {
					onComplete(stream.boardId as string);
				}, AUTO_NAV_DELAY_MS);
			} else {
				navTimerRef.current = setTimeout(() => {
					navigate({
						to: "/boards/$boardId",
						params: { boardId: stream.boardId as string },
					});
				}, AUTO_NAV_DELAY_MS);
			}
		}

		return () => {
			if (navTimerRef.current) clearTimeout(navTimerRef.current);
		};
	}, [stream.phase, stream.boardId, navigate, onComplete]);

	function handleRetry() {
		stream.start();
	}

	function handleAbort() {
		stream.abort();
		onAbort?.();
	}

	const visibleLog = stream.log.slice(0, MAX_VISIBLE_ENTRIES);
	const hasOverflow = stream.log.length > MAX_VISIBLE_ENTRIES;

	const isActive =
		stream.phase === "connecting" ||
		stream.phase === "researching" ||
		stream.phase === "skeleton" ||
		stream.phase === "enriching";
	const showEnrichmentProgress = stream.phase === "enriching" && stream.totalCount > 0;
	const showResearchProgress = stream.phase === "researching" && stream.researchProgress !== null;

	const phaseText = getPhaseText(stream, t);

	// Compute progress bar percentage across all phases
	const progressPercent = (() => {
		if (showResearchProgress && stream.researchProgress) {
			const rp = stream.researchProgress;
			return rp.totalQueries > 0 ? (rp.queriesCompleted / rp.totalQueries) * 100 : 0;
		}
		if (showEnrichmentProgress) {
			return (stream.enrichedCount / stream.totalCount) * 100;
		}
		return 0;
	})();

	const showProgressBar = showResearchProgress || showEnrichmentProgress;

	return (
		<div className="flex min-h-screen w-full flex-col items-center justify-center p-4">
			<div className="w-full max-w-md space-y-6">
				{/* Header */}
				<div className="text-center space-y-2">
					{stream.boardTitle ? (
						<h1 className="text-xl font-semibold tracking-tight">{stream.boardTitle}</h1>
					) : (
						<h1 className="text-xl font-semibold tracking-tight text-muted-foreground">
							{phaseText}
						</h1>
					)}

					{/* Phase text (shown below title when board title is visible) */}
					{stream.boardTitle && stream.phase !== "complete" && stream.phase !== "error" && (
						<p className="text-sm text-muted-foreground">{phaseText}</p>
					)}

					{/* Research subtitle: current query */}
					{showResearchProgress && stream.researchProgress?.currentQuery && (
						<p className="text-xs text-muted-foreground/70 truncate max-w-sm mx-auto">
							<Search className="inline-block h-3 w-3 mr-1 -mt-0.5" />
							{stream.researchProgress.currentQuery}
						</p>
					)}

					{stream.phase === "complete" && (
						<p className="text-sm text-green-500 font-medium">{t("boardProgress.redirecting")}</p>
					)}
				</div>

				{/* Progress bar */}
				{showProgressBar && (
					<div className="h-1 w-full rounded-full bg-muted overflow-hidden">
						<div
							className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
							style={{ width: `${progressPercent}%` }}
						/>
					</div>
				)}

				{/* Log stack */}
				{visibleLog.length > 0 && (
					<div className="relative">
						<div className="space-y-1">
							{visibleLog.map((entry, index) => (
								<LogLine key={entry.id} entry={entry} isLatest={index === 0 && isActive} />
							))}
						</div>
						{/* Gradient fade at bottom */}
						{hasOverflow && (
							<div className="pointer-events-none absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-background to-transparent" />
						)}
					</div>
				)}

				{/* Error actions */}
				{stream.phase === "error" && (
					<div className="flex items-center justify-center gap-3 pt-2">
						<Button variant="outline" size="sm" onClick={handleAbort}>
							{t("boardProgress.back")}
						</Button>
						{!stream.boardId && (
							<Button size="sm" onClick={handleRetry}>
								{t("boardProgress.tryAgain")}
							</Button>
						)}
						{stream.boardId && (
							<Button
								size="sm"
								onClick={() =>
									navigate({
										to: "/boards/$boardId",
										params: {
											boardId: stream.boardId as string,
										},
									})
								}
							>
								{t("boardProgress.checkBoard")}
							</Button>
						)}
					</div>
				)}
			</div>
		</div>
	);
}

function LogLine({ entry, isLatest }: { entry: LogEntry; isLatest: boolean }) {
	return (
		<div
			className={`flex items-start gap-2 py-1 text-xs font-mono transition-opacity duration-300 ${
				isLatest ? "animate-in fade-in slide-in-from-top-1 duration-200" : ""
			}`}
		>
			<div className="flex-shrink-0 mt-0.5">
				{entry.type === "success" && <Check className="h-3 w-3 text-green-500" />}
				{entry.type === "error" && <CircleAlert className="h-3 w-3 text-destructive" />}
				{entry.type === "info" && isLatest && (
					<Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
				)}
				{entry.type === "info" && !isLatest && (
					<CircleDot className="h-3 w-3 text-muted-foreground/50" />
				)}
			</div>
			<span
				className={
					entry.type === "error"
						? "text-destructive"
						: entry.type === "success"
							? "text-foreground/80"
							: "text-muted-foreground"
				}
			>
				{entry.message}
			</span>
		</div>
	);
}
