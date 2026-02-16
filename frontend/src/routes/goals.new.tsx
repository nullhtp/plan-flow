import { createRoute } from "@tanstack/react-router";
import { useState } from "react";
import type {
	GoalQuestionsResponse,
	GoalRejectionResponse,
	QuestionSchema,
} from "@/api/generated/model";
import { DynamicQuestionForm } from "@/features/goals/components/dynamic-question-form";
import { ErrorDisplay } from "@/features/goals/components/error-display";
import { GoalInput } from "@/features/goals/components/goal-input";
import { GoalSummary } from "@/features/goals/components/goal-summary";
import { LoadingState } from "@/features/goals/components/loading-state";
import { VagueGoalRejection } from "@/features/goals/components/vague-goal-rejection";
import { useCreateGoal, useSubmitAnswers } from "@/features/goals/hooks/use-goals";
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
			questions: QuestionSchema[];
			followUpQuestions?: QuestionSchema[];
			round1Answers?: AnswerValues;
	  }
	| { step: "answersLoading"; goalId: string; title: string }
	| {
			step: "summary";
			goalId: string;
			title: string;
			originalInput: string;
			allQuestions: QuestionSchema[];
			allAnswers: AnswerValues;
	  }
	| { step: "error"; message: string; retryAction: () => void };

export const goalsNewRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/goals/new",
	component: GoalsNewPage,
});

function GoalsNewPage() {
	const createGoal = useCreateGoal();
	const submitAnswers = useSubmitAnswers();

	const [pageState, setPageState] = useState<PageState>({ step: "input" });
	const [lastInput, setLastInput] = useState("");

	function getErrorMessage(status: number): string {
		if (status === 503 || status === 504) {
			return "Our AI is taking longer than expected. Please try again.";
		}
		return "Something went wrong while processing your goal. Please try again.";
	}

	function handleCreateGoal(input: string) {
		setLastInput(input);
		setPageState({ step: "loading" });

		createGoal.mutate(
			{ data: { original_input: input } },
			{
				onSuccess: (response) => {
					if (response.status === 201) {
						const data = response.data as GoalQuestionsResponse;
						setPageState({
							step: "questions",
							goalId: data.goal_id,
							title: data.title,
							questions: data.questions,
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
		questions: QuestionSchema[],
		answers: AnswerValues,
		round: number,
		previousQuestions?: QuestionSchema[],
		previousAnswers?: AnswerValues,
	) {
		setPageState({ step: "answersLoading", goalId, title });

		submitAnswers.mutate(
			{ goalId, data: { answers, round } },
			{
				onSuccess: (response) => {
					if (response.status === 200) {
						const data = response.data;
						if (data.is_complete) {
							const allQuestions = [...(previousQuestions ?? []), ...questions];
							const allAnswers = {
								...(previousAnswers ?? {}),
								...answers,
							};
							setPageState({
								step: "summary",
								goalId,
								title,
								originalInput: lastInput,
								allQuestions,
								allAnswers,
							});
						} else if (data.follow_up_questions && data.follow_up_questions.length > 0) {
							setPageState({
								step: "questions",
								goalId,
								title,
								questions,
								followUpQuestions: data.follow_up_questions,
								round1Answers: answers,
							});
						} else {
							setPageState({
								step: "summary",
								goalId,
								title,
								originalInput: lastInput,
								allQuestions: questions,
								allAnswers: answers,
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
								questions,
								answers,
								round,
								previousQuestions,
								previousAnswers,
							),
					});
				},
			},
		);
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
		const { goalId, title, questions, followUpQuestions, round1Answers } = pageState;
		return (
			<div className="flex min-h-screen items-center justify-center p-4">
				<DynamicQuestionForm
					goalTitle={title}
					initialQuestions={questions}
					followUpQuestions={followUpQuestions}
					initialAnswers={round1Answers}
					isRound1Submitted={!!round1Answers}
					onSubmitAnswers={(answers, round) =>
						handleSubmitAnswers(
							goalId,
							title,
							round === 2 ? (followUpQuestions ?? []) : questions,
							answers,
							round,
							round === 2 ? questions : undefined,
							round === 2 ? round1Answers : undefined,
						)
					}
					isPending={false}
					onEdit={() => {
						setPageState({
							step: "questions",
							goalId,
							title,
							questions,
						});
					}}
				/>
			</div>
		);
	}

	if (pageState.step === "answersLoading") {
		return (
			<div className="flex min-h-screen items-center justify-center p-4">
				<LoadingState message="Processing your answers..." />
			</div>
		);
	}

	if (pageState.step === "summary") {
		const { title, originalInput, allQuestions, allAnswers } = pageState;
		const qaPairs = allQuestions.map((q) => ({
			question: q,
			answer: allAnswers[q.id] ?? "",
		}));
		return (
			<div className="flex min-h-screen items-center justify-center p-4">
				<GoalSummary title={title} originalInput={originalInput} qaPairs={qaPairs} />
			</div>
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
