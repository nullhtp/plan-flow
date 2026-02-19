import { createRoute } from "@tanstack/react-router";
import { useState } from "react";
import type { GoalResponse, QuestionSchema } from "@/api/generated/model";
import { BoardGenerationProgress } from "@/features/goals/components/board-generation-progress";
import { ErrorDisplay } from "@/features/goals/components/error-display";
import { GoalSummary } from "@/features/goals/components/goal-summary";
import { LoadingState } from "@/features/goals/components/loading-state";
import { useGoal } from "@/features/goals/hooks/use-goals";
import { authenticatedRoute } from "./_authenticated";

export const goalDetailRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/goals/$goalId",
	component: GoalDetailPage,
});

function GoalDetailPage() {
	const { goalId } = goalDetailRoute.useParams();
	const goalQuery = useGoal(goalId);
	const [isGenerating, setIsGenerating] = useState(false);

	if (isGenerating) {
		return (
			<BoardGenerationProgress
				sseUrl={`/api/goals/${goalId}/generate-board/stream`}
				onAbort={() => setIsGenerating(false)}
			/>
		);
	}

	if (goalQuery.isLoading) {
		return (
			<div className="flex min-h-screen items-center justify-center p-4">
				<LoadingState message="Loading goal..." />
			</div>
		);
	}

	if (goalQuery.isError || !goalQuery.data) {
		return (
			<div className="flex min-h-screen items-center justify-center p-4">
				<ErrorDisplay
					message="Could not load this goal. It may not exist or you may not have access."
					onRetry={() => goalQuery.refetch()}
					isRetrying={goalQuery.isRefetching}
				/>
			</div>
		);
	}

	const goal = goalQuery.data.data as GoalResponse;
	const aiContext = goal.ai_context as Record<string, unknown>;

	const allQuestions: QuestionSchema[] = [
		...((aiContext.questions as QuestionSchema[]) ?? []),
		...((aiContext.follow_up_questions as QuestionSchema[]) ?? []),
	];
	const allAnswers = {
		...((aiContext.round_1_answers as Record<string, unknown>) ?? {}),
		...((aiContext.round_2_answers as Record<string, unknown>) ?? {}),
	} as Record<string, string | string[] | number>;

	if (goal.status === "answered" || goal.status === "questioning") {
		const qaPairs = allQuestions
			.filter((q) => allAnswers[q.id] !== undefined)
			.map((q) => ({
				question: q,
				answer: allAnswers[q.id] ?? "",
			}));

		return (
			<div className="flex min-h-screen items-center justify-center p-4">
				<GoalSummary
					goalId={goal.id}
					title={goal.title}
					originalInput={goal.original_input}
					qaPairs={qaPairs}
					onGenerateBoard={() => setIsGenerating(true)}
				/>
			</div>
		);
	}

	return (
		<div className="flex min-h-screen items-center justify-center p-4">
			<LoadingState message="Loading goal..." />
		</div>
	);
}
