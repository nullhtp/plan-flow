import { createRoute } from "@tanstack/react-router";
import { useState } from "react";
import type { GoalResponse, QuestionSchema, ReadinessSchema } from "@/api/generated/model";
import { BoardGenerationProgress } from "@/features/goals/components/board-generation-progress";
import { DynamicQuestionForm, type Round } from "@/features/goals/components/dynamic-question-form";
import { ErrorDisplay } from "@/features/goals/components/error-display";
import { GoalSummary } from "@/features/goals/components/goal-summary";
import { LoadingState } from "@/features/goals/components/loading-state";
import { useGoal, useSubmitAnswers } from "@/features/goals/hooks/use-goals";
import { authenticatedRoute } from "./_authenticated";

type AnswerValues = Record<string, string | string[] | number>;

/** Convert ai_context to Round[] — supports both rounds-based and legacy flat format. */
function extractRounds(aiContext: Record<string, unknown>): Round[] {
	// New rounds-based format
	const rawRounds = aiContext.rounds as
		| Array<{
				round: number;
				questions: QuestionSchema[];
				answers: Record<string, unknown>;
				readiness: ReadinessSchema | null;
		  }>
		| undefined;

	if (rawRounds && Array.isArray(rawRounds)) {
		return rawRounds.map((r) => ({
			round: r.round,
			questions: r.questions ?? [],
			answers: (r.answers ?? {}) as AnswerValues,
			readiness: r.readiness ?? null,
		}));
	}

	// Legacy flat format: questions + follow_up_questions + round_1_answers + round_2_answers
	const questions = (aiContext.questions as QuestionSchema[]) ?? [];
	const followUpQuestions = (aiContext.follow_up_questions as QuestionSchema[]) ?? [];
	const round1Answers = (aiContext.round_1_answers as AnswerValues) ?? {};
	const round2Answers = (aiContext.round_2_answers as AnswerValues) ?? {};

	const rounds: Round[] = [];
	if (questions.length > 0) {
		rounds.push({
			round: 1,
			questions,
			answers: round1Answers,
			readiness: null,
		});
	}
	if (followUpQuestions.length > 0) {
		rounds.push({
			round: 2,
			questions: followUpQuestions,
			answers: round2Answers,
			readiness: null,
		});
	}
	return rounds;
}

export const goalDetailRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/goals/$goalId",
	component: GoalDetailPage,
});

function GoalDetailPage() {
	const { goalId } = goalDetailRoute.useParams();
	const goalQuery = useGoal(goalId);
	const submitAnswers = useSubmitAnswers();
	const [isGenerating, setIsGenerating] = useState(false);
	const [localRounds, setLocalRounds] = useState<Round[] | null>(null);
	const [readiness, setReadiness] = useState<ReadinessSchema | null>(null);

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

	// For questioning status: show growing question form
	if (goal.status === "questioning") {
		const rounds = localRounds ?? extractRounds(aiContext);
		const lastRound = rounds.length > 0 ? rounds[rounds.length - 1] : null;
		const hasUnansweredRound = lastRound && Object.keys(lastRound.answers).length === 0;
		const currentRound = lastRound?.round ?? 1;
		const activeQuestions = hasUnansweredRound ? lastRound.questions : [];
		const hasCompletedRounds = rounds.some((r) => Object.keys(r.answers).length > 0);

		// Get readiness from the last round that has one, or from local state
		const latestReadiness =
			readiness ?? [...rounds].reverse().find((r) => r.readiness !== null)?.readiness ?? null;

		return (
			<div className="mx-auto min-h-screen max-w-2xl px-4 py-8">
				<DynamicQuestionForm
					goalTitle={goal.title}
					rounds={rounds}
					activeQuestions={activeQuestions}
					currentRound={currentRound}
					readiness={latestReadiness}
					hasCompletedRounds={hasCompletedRounds}
					onSubmitAnswers={(answers, round) => {
						const updatedRounds = rounds.map((r) => (r.round === round ? { ...r, answers } : r));
						setLocalRounds(updatedRounds);

						submitAnswers.mutate(
							{ goalId: goal.id, data: { answers, round } },
							{
								onSuccess: (response: any) => {
									if (response.status === 200) {
										const data = response.data;
										const newReadiness = data.readiness ?? latestReadiness;
										setReadiness(newReadiness);

										const roundsWithReadiness = updatedRounds.map((r) =>
											r.round === round ? { ...r, readiness: newReadiness } : r,
										);

										if (data.next_questions && data.next_questions.length > 0) {
											const newRound: Round = {
												round: data.next_round,
												questions: data.next_questions,
												answers: {},
												readiness: null,
											};
											setLocalRounds([...roundsWithReadiness, newRound]);
										} else {
											setLocalRounds(roundsWithReadiness);
										}
									}
								},
							},
						);
					}}
					onEditRound={(roundNum) => {
						const keptRounds = rounds.filter((r) => r.round <= roundNum);
						setLocalRounds(keptRounds);
						const prevRound = keptRounds.find((r) => r.round === roundNum - 1);
						setReadiness(prevRound?.readiness ?? null);
					}}
					onGenerate={() => setIsGenerating(true)}
					isPending={submitAnswers.isPending}
					isLoadingFollowUp={submitAnswers.isPending}
				/>
			</div>
		);
	}

	// For answered status (legacy): show summary view
	if (goal.status === "answered") {
		const rounds = extractRounds(aiContext);
		const allQuestions = rounds.flatMap((r) => r.questions);
		const allAnswers = Object.assign({}, ...rounds.map((r) => r.answers)) as AnswerValues;
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
