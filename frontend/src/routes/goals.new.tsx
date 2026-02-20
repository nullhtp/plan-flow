import { createRoute } from "@tanstack/react-router";
import { useState } from "react";
import type {
	GoalCreate,
	GoalQuestionsResponse,
	GoalRejectionResponse,
	QuestionSchema,
	ReadinessSchema,
} from "@/api/generated/model";
import { BoardGenerationProgress } from "@/features/goals/components/board-generation-progress";
import { DynamicQuestionForm, type Round } from "@/features/goals/components/dynamic-question-form";
import { ErrorDisplay } from "@/features/goals/components/error-display";
import { GoalInput } from "@/features/goals/components/goal-input";
import { LoadingState } from "@/features/goals/components/loading-state";
import { VagueGoalRejection } from "@/features/goals/components/vague-goal-rejection";
import { useCreateGoal, useSubmitAnswers } from "@/features/goals/hooks/use-goals";
import { useUserMeta } from "@/shared/hooks/use-user-meta";
import { authenticatedRoute } from "./_authenticated";

type AnswerValues = Record<string, string | string[] | number>;

type PageState =
	| { step: "input" }
	| { step: "loading" }
	| { step: "rejected"; reason: string; suggestions: string[] }
	| {
			step: "questions";
			goalId: string;
			title: string;
			rounds: Round[];
			activeQuestions: QuestionSchema[];
			currentRound: number;
			readiness: ReadinessSchema | null;
	  }
	| {
			step: "answersLoading";
			goalId: string;
			title: string;
			rounds: Round[];
			readiness: ReadinessSchema | null;
	  }
	| { step: "generating"; goalId: string }
	| { step: "error"; message: string; retryAction: () => void };

export const goalsNewRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/goals/new",
	component: GoalsNewPage,
});

function GoalsNewPage() {
	const createGoal = useCreateGoal();
	const submitAnswers = useSubmitAnswers();
	const { resolveLocation } = useUserMeta();

	const [pageState, setPageState] = useState<PageState>({ step: "input" });
	const [lastInput, setLastInput] = useState("");

	function getErrorMessage(status: number): string {
		if (status === 503 || status === 504) {
			return "Our AI is taking longer than expected. Please try again.";
		}
		return "Something went wrong while processing your goal. Please try again.";
	}

	async function handleCreateGoal(input: string) {
		setLastInput(input);
		setPageState({ step: "loading" });

		// Resolve location from user gesture context (triggers permission prompt)
		const userMeta = await resolveLocation();

		createGoal.mutate(
			// user_meta included for AI context; typed after Orval regeneration
			{ data: { original_input: input, user_meta: userMeta } as GoalCreate },
			{
				onSuccess: (response) => {
					if (response.status === 201) {
						const data = response.data as GoalQuestionsResponse;
						const initialRound: Round = {
							round: 1,
							questions: data.questions,
							answers: {},
							readiness: data.readiness ?? null,
						};
						setPageState({
							step: "questions",
							goalId: data.goal_id,
							title: data.title,
							rounds: [initialRound],
							activeQuestions: data.questions,
							currentRound: 1,
							readiness: data.readiness ?? null,
						});
					}
				},
				onError: (error: unknown) => {
					const err = error as { status?: number; data?: GoalRejectionResponse };
					if (err.status === 422 && err.data?.rejection_reason) {
						setPageState({
							step: "rejected",
							reason: err.data.rejection_reason,
							suggestions: err.data.refinement_suggestions ?? [],
						});
					} else {
						setPageState({
							step: "error",
							message: getErrorMessage(err.status ?? 500),
							retryAction: () => handleCreateGoal(input),
						});
					}
				},
			},
		);
	}

	function handleSubmitAnswers(
		goalId: string,
		title: string,
		rounds: Round[],
		currentRound: number,
		currentReadiness: ReadinessSchema | null,
		answers: AnswerValues,
		round: number,
	) {
		// Update the current round with answers
		const updatedRounds = rounds.map((r) => (r.round === round ? { ...r, answers } : r));

		setPageState({
			step: "answersLoading",
			goalId,
			title,
			rounds: updatedRounds,
			readiness: currentReadiness,
		});

		submitAnswers.mutate(
			{ goalId, data: { answers, round } },
			{
				onSuccess: (response) => {
					if (response.status === 200) {
						const data = response.data;
						const newReadiness = data.readiness ?? currentReadiness;

						// Update current round's readiness
						const roundsWithReadiness = updatedRounds.map((r) =>
							r.round === round ? { ...r, readiness: newReadiness } : r,
						);

						if (data.next_questions && data.next_questions.length > 0) {
							// New follow-up questions arrived - add as new round
							const nextRound = data.next_round;
							const newRound: Round = {
								round: nextRound,
								questions: data.next_questions,
								answers: {},
								readiness: null,
							};
							setPageState({
								step: "questions",
								goalId,
								title,
								rounds: [...roundsWithReadiness, newRound],
								activeQuestions: data.next_questions,
								currentRound: nextRound,
								readiness: newReadiness,
							});
						} else {
							// No more questions - stay on current view
							// User can generate from the footer
							setPageState({
								step: "questions",
								goalId,
								title,
								rounds: roundsWithReadiness,
								activeQuestions: [],
								currentRound: round,
								readiness: newReadiness,
							});
						}
					}
				},
				onError: (error: unknown) => {
					const err = error as { status?: number };
					setPageState({
						step: "error",
						message: getErrorMessage(err.status ?? 500),
						retryAction: () =>
							handleSubmitAnswers(
								goalId,
								title,
								rounds,
								currentRound,
								currentReadiness,
								answers,
								round,
							),
					});
				},
			},
		);
	}

	function handleEditRound(goalId: string, title: string, rounds: Round[], roundNum: number) {
		// Truncate all rounds after roundNum, make roundNum editable
		const keptRounds = rounds.filter((r) => r.round <= roundNum);
		const editRound = keptRounds.find((r) => r.round === roundNum);
		if (!editRound) return;

		// Find readiness from the round before the one being edited
		const previousRound = keptRounds.find((r) => r.round === roundNum - 1);
		const previousReadiness = previousRound?.readiness ?? null;

		setPageState({
			step: "questions",
			goalId,
			title,
			rounds: keptRounds,
			activeQuestions: editRound.questions,
			currentRound: roundNum,
			readiness: previousReadiness,
		});
	}

	if (pageState.step === "input") {
		return (
			<div className="flex min-h-screen items-center justify-center p-4">
				<GoalInput onSubmit={handleCreateGoal} isPending={false} defaultValue={lastInput} />
			</div>
		);
	}

	if (pageState.step === "loading") {
		return (
			<div className="flex min-h-screen items-center justify-center p-4">
				<LoadingState />
			</div>
		);
	}

	if (pageState.step === "rejected") {
		return (
			<div className="flex min-h-screen items-center justify-center p-4">
				<VagueGoalRejection
					reason={pageState.reason}
					suggestions={pageState.suggestions}
					onSuggestionClick={(suggestion) => {
						setLastInput(suggestion);
						setPageState({ step: "input" });
					}}
					onTryAgain={() => {
						setLastInput("");
						setPageState({ step: "input" });
					}}
				/>
			</div>
		);
	}

	if (pageState.step === "questions") {
		const { goalId, title, rounds, activeQuestions, currentRound, readiness } = pageState;
		const hasCompletedRounds = rounds.some(
			(r) => r.round < currentRound && Object.keys(r.answers).length > 0,
		);
		return (
			<div className="mx-auto min-h-screen max-w-2xl px-4 py-8">
				<DynamicQuestionForm
					goalTitle={title}
					rounds={rounds}
					activeQuestions={activeQuestions}
					currentRound={currentRound}
					readiness={readiness}
					hasCompletedRounds={hasCompletedRounds}
					onSubmitAnswers={(answers, round) =>
						handleSubmitAnswers(goalId, title, rounds, currentRound, readiness, answers, round)
					}
					onEditRound={(roundNum) => handleEditRound(goalId, title, rounds, roundNum)}
					onGenerate={() => setPageState({ step: "generating", goalId })}
					isPending={false}
					isLoadingFollowUp={false}
				/>
			</div>
		);
	}

	if (pageState.step === "answersLoading") {
		const { goalId, title, rounds, readiness } = pageState;
		const currentRound = rounds.length > 0 ? rounds[rounds.length - 1].round : 1;
		const hasCompletedRounds = rounds.some((r) => Object.keys(r.answers).length > 0);
		return (
			<div className="mx-auto min-h-screen max-w-2xl px-4 py-8">
				<DynamicQuestionForm
					goalTitle={title}
					rounds={rounds}
					activeQuestions={[]}
					currentRound={currentRound + 1}
					readiness={readiness}
					hasCompletedRounds={hasCompletedRounds}
					onSubmitAnswers={() => {}}
					onEditRound={() => {}}
					onGenerate={() => setPageState({ step: "generating", goalId })}
					isPending={true}
					isLoadingFollowUp={true}
				/>
			</div>
		);
	}

	if (pageState.step === "generating") {
		return (
			<BoardGenerationProgress
				sseUrl={`/api/goals/${pageState.goalId}/generate-board/stream`}
				onAbort={() => setPageState({ step: "input" })}
			/>
		);
	}

	if (pageState.step === "error") {
		return (
			<div className="flex min-h-screen items-center justify-center p-4">
				<ErrorDisplay message={pageState.message} onRetry={pageState.retryAction} />
			</div>
		);
	}

	return null;
}
