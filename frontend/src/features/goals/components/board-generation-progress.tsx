import { useNavigate } from "@tanstack/react-router";
import { Check, CircleAlert, CircleDot, Loader2 } from "lucide-react";
import { useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import {
	type LogEntry,
	useBoardGenerationStream,
} from "@/features/goals/hooks/use-board-generation-stream";

const MAX_VISIBLE_ENTRIES = 8;
const AUTO_NAV_DELAY_MS = 1500;

interface BoardGenerationProgressProps {
	goalId: string;
	onAbort?: () => void;
}

export function BoardGenerationProgress({ goalId, onAbort }: BoardGenerationProgressProps) {
	const stream = useBoardGenerationStream(goalId);
	const navigate = useNavigate();
	const navTimerRef = useRef<ReturnType<typeof setTimeout>>();

	// Start the stream on mount, abort on unmount.
	useEffect(() => {
		stream.start();
		return () => {
			stream.abort();
		};
	}, [stream.start, stream.abort]);

	// Auto-navigate on completion
	useEffect(() => {
		if (stream.phase === "complete" && stream.boardId) {
			navTimerRef.current = setTimeout(() => {
				navigate({
					to: "/boards/$boardId",
					params: { boardId: stream.boardId as string },
				});
			}, AUTO_NAV_DELAY_MS);
		}

		return () => {
			if (navTimerRef.current) clearTimeout(navTimerRef.current);
		};
	}, [stream.phase, stream.boardId, navigate]);

	function handleRetry() {
		stream.start();
	}

	function handleAbort() {
		stream.abort();
		onAbort?.();
	}

	const visibleLog = stream.log.slice(0, MAX_VISIBLE_ENTRIES);
	const hasOverflow = stream.log.length > MAX_VISIBLE_ENTRIES;

	const isActive = stream.phase === "connecting" || stream.phase === "enriching";
	const showProgress = stream.phase === "enriching" && stream.totalCount > 0;

	return (
		<div className="flex min-h-screen w-full flex-col items-center justify-center p-4">
			<div className="w-full max-w-md space-y-6">
				{/* Header */}
				<div className="text-center space-y-2">
					{stream.boardTitle ? (
						<h1 className="text-xl font-semibold tracking-tight">{stream.boardTitle}</h1>
					) : (
						<h1 className="text-xl font-semibold tracking-tight text-muted-foreground">
							Generating board...
						</h1>
					)}

					{/* Progress counter */}
					{showProgress && (
						<p className="text-sm text-muted-foreground">
							{stream.enrichedCount} / {stream.totalCount} tasks enriched
						</p>
					)}
					{stream.phase === "complete" && (
						<p className="text-sm text-green-500 font-medium">Board ready — redirecting...</p>
					)}
				</div>

				{/* Progress bar */}
				{showProgress && (
					<div className="h-1 w-full rounded-full bg-muted overflow-hidden">
						<div
							className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
							style={{
								width: `${(stream.enrichedCount / stream.totalCount) * 100}%`,
							}}
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
							Back
						</Button>
						{!stream.boardId && (
							<Button size="sm" onClick={handleRetry}>
								Try Again
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
								Check your board
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
