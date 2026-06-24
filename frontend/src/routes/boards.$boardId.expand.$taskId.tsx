import { createRoute, useNavigate } from "@tanstack/react-router";
import { Loader2 } from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSubBoardQuestionsEndpointApiTasksTaskIdSubBoardQuestionsPost } from "@/api/generated/boards/boards";
import type { QuestionSchema } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useBoard } from "@/features/board/hooks/use-board";
import type { BoardResponse } from "@/features/board/types";
import { BoardGenerationProgress } from "@/features/goals/components/board-generation-progress";
import { ErrorDisplay } from "@/features/goals/components/error-display";
import {
	MultiselectOptionField,
	OptionField,
	parseMultiselectValue,
	parseOptionValue,
	QuestionFieldWrapper,
	serializeMultiselectValue,
	serializeOptionValue,
} from "@/shared/components/question-fields";
import { authenticatedRoute } from "./_authenticated";

// ── Route Definition ────────────────────────────────────

export const boardExpandTaskRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/boards/$boardId/expand/$taskId",
	component: BoardExpandTaskPage,
});

// ── Types ───────────────────────────────────────────────

type AnswerValues = Record<string, string | string[] | number>;

type PageState =
	| { step: "loading-context" }
	| { step: "loading-questions" }
	| { step: "questions"; questions: QuestionSchema[] }
	| { step: "generating"; answers: AnswerValues }
	| { step: "error"; message: string; canRetry: boolean };

// ── Field State Helpers ─────────────────────────────────

interface FieldState {
	selectedOption: string;
	otherText: string;
	selectedOptions: string[];
}

function getInitialFieldState(
	question: QuestionSchema,
	value: string | string[] | number | undefined,
): FieldState {
	const options = question.options ?? [];
	if (question.type === "multiselect") {
		const arrValue = Array.isArray(value) ? value : [];
		const parsed = parseMultiselectValue(arrValue, options);
		return {
			selectedOption: "",
			otherText: parsed.otherText,
			selectedOptions: parsed.selectedOptions,
		};
	}
	const strValue = value === undefined ? "" : String(value);
	const parsed = parseOptionValue(strValue, options);
	return {
		selectedOption: parsed.selectedOption,
		otherText: parsed.otherText,
		selectedOptions: [],
	};
}

// ── Full-Size Question Field ────────────────────────────

function QuestionField({
	question,
	value,
	onChange,
	disabled,
}: {
	question: QuestionSchema;
	value: string | string[] | number | undefined;
	onChange: (value: string | string[] | number) => void;
	disabled: boolean;
}) {
	const { t } = useTranslation("board");
	const options = question.options ?? [];
	const hasOptions = options.length > 0;

	const [fieldState, setFieldState] = useState<FieldState>(() =>
		getInitialFieldState(question, value),
	);

	if (!hasOptions) {
		const stringValue = value === undefined ? "" : String(value);
		return (
			<QuestionFieldWrapper question={question}>
				<Input
					id={question.id}
					value={stringValue}
					onChange={(e) => onChange(e.target.value)}
					placeholder={t("boardExpand.typeAnswer")}
					disabled={disabled}
				/>
			</QuestionFieldWrapper>
		);
	}

	if (question.type === "multiselect") {
		return (
			<QuestionFieldWrapper question={question}>
				<MultiselectOptionField
					question={question}
					selectedOptions={fieldState.selectedOptions}
					otherText={fieldState.otherText}
					onToggleOption={(option) => {
						setFieldState((prev) => {
							const next = prev.selectedOptions.includes(option)
								? prev.selectedOptions.filter((o) => o !== option)
								: [...prev.selectedOptions, option];
							const serialized = serializeMultiselectValue(next, prev.otherText);
							onChange(serialized);
							return { ...prev, selectedOptions: next };
						});
					}}
					onOtherChange={(text) => {
						setFieldState((prev) => {
							const serialized = serializeMultiselectValue(prev.selectedOptions, text);
							onChange(serialized);
							return { ...prev, otherText: text };
						});
					}}
					disabled={disabled}
				/>
			</QuestionFieldWrapper>
		);
	}

	return (
		<QuestionFieldWrapper question={question}>
			<OptionField
				question={question}
				value={fieldState.selectedOption}
				otherText={fieldState.otherText}
				onSelectOption={(option) => {
					setFieldState({ selectedOption: option, otherText: "", selectedOptions: [] });
					onChange(option);
				}}
				onOtherChange={(text) => {
					const serialized = serializeOptionValue("", text);
					setFieldState({ selectedOption: "", otherText: text, selectedOptions: [] });
					onChange(serialized);
				}}
				disabled={disabled}
			/>
		</QuestionFieldWrapper>
	);
}

// ── Page Component ──────────────────────────────────────

function BoardExpandTaskPage() {
	const { t } = useTranslation("board");
	const { boardId, taskId } = boardExpandTaskRoute.useParams();
	const navigate = useNavigate();
	const boardQuery = useBoard(boardId);

	const [pageState, setPageState] = useState<PageState>({ step: "loading-context" });
	const [values, setValues] = useState<AnswerValues>({});

	const questionsQuery = useSubBoardQuestionsEndpointApiTasksTaskIdSubBoardQuestionsPost({
		mutation: {
			onSuccess: (response: any) => {
				if (response.status !== 200) return;
				const qs = (response.data.questions ?? []) as unknown as QuestionSchema[];
				setPageState({ step: "questions", questions: qs });
			},
			onError: (error: unknown) => {
				const err = error as { status?: number; data?: { detail?: string } };
				if (err.status === 409) {
					// Task already has a sub-board — handled in the board-loaded effect
					setPageState({
						step: "error",
						message: t("boardExpand.subBoardExists"),
						canRetry: false,
					});
				} else if (err.status === 422) {
					setPageState({
						step: "error",
						message: t("boardExpand.subBoardsCannotBeNested"),
						canRetry: false,
					});
				} else {
					setPageState({
						step: "error",
						message: t("boardExpand.failedQuestions"),
						canRetry: true,
					});
				}
			},
		},
	});

	// Resolve board + task data, then load questions
	const didInit = useRef(false);
	useEffect(() => {
		if (didInit.current) return;
		if (boardQuery.isLoading) return;

		didInit.current = true;

		if (boardQuery.isError || !boardQuery.data) {
			setPageState({
				step: "error",
				message: t("boardExpand.couldNotLoadBoard"),
				canRetry: false,
			});
			return;
		}

		const board = boardQuery.data.data as BoardResponse;
		const task = board.tasks.find((t) => t.id === taskId);

		if (!task) {
			setPageState({
				step: "error",
				message: t("boardExpand.taskNotFound"),
				canRetry: false,
			});
			return;
		}

		// Guard: redirect if task already has a sub-board
		if (task.sub_board_id) {
			navigate({
				to: "/boards/$boardId",
				params: { boardId: task.sub_board_id },
				replace: true,
			});
			return;
		}

		// Guard: sub-boards can't be nested
		if (board.parent_task_id) {
			setPageState({
				step: "error",
				message: t("boardExpand.subBoardsCannotBeNested"),
				canRetry: false,
			});
			return;
		}

		setPageState({ step: "loading-questions" });
		questionsQuery.mutate({ taskId });
	}, [
		boardQuery.isLoading,
		boardQuery.isError,
		boardQuery.data,
		taskId,
		navigate,
		questionsQuery.mutate,
		t,
	]);

	// Derive task and board info from query data
	const board = boardQuery.data?.data as BoardResponse | undefined;
	const task = board?.tasks.find((t) => t.id === taskId);
	const taskTitle = task?.title ?? t("boardExpand.defaultTaskTitle");
	const boardTitle = board?.title ?? t("boardExpand.defaultBoardTitle");

	function handleChange(questionId: string, value: string | string[] | number) {
		setValues((prev) => ({ ...prev, [questionId]: value }));
	}

	function isValid(): boolean {
		if (pageState.step !== "questions") return false;
		return pageState.questions.every((q) => {
			if (!q.required) return true;
			const val = values[q.id];
			if (val === undefined || val === "") return false;
			if (Array.isArray(val) && val.length === 0) return false;
			return true;
		});
	}

	function handleSubmit(e: FormEvent) {
		e.preventDefault();
		if (!isValid()) return;
		setPageState({ step: "generating", answers: values });
	}

	function handleRetryQuestions() {
		setPageState({ step: "loading-questions" });
		questionsQuery.mutate({ taskId });
	}

	// ── Rendering ───────────────────────────────────────

	// Context header (shown in all states)
	const contextHeader = (
		<div className="text-center space-y-1 mb-6">
			<h1 className="text-2xl font-semibold tracking-tight">{taskTitle}</h1>
			<p className="text-sm text-muted-foreground">
				{t("boardExpand.expandingTaskFrom", { board: boardTitle })}
			</p>
		</div>
	);

	// Loading context (board data)
	if (pageState.step === "loading-context") {
		return (
			<div className="flex min-h-screen items-center justify-center p-4">
				<div className="w-full max-w-2xl text-center space-y-4">
					{contextHeader}
					<div className="flex items-center justify-center gap-2">
						<Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
						<span className="text-sm text-muted-foreground">{t("boardExpand.loading")}</span>
					</div>
				</div>
			</div>
		);
	}

	// Loading questions
	if (pageState.step === "loading-questions") {
		return (
			<div className="flex min-h-screen items-center justify-center p-4">
				<div className="w-full max-w-2xl text-center space-y-4">
					{contextHeader}
					<div className="flex items-center justify-center gap-2">
						<Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
						<span className="text-sm text-muted-foreground">
							{t("boardExpand.preparingQuestions")}
						</span>
					</div>
				</div>
			</div>
		);
	}

	// Questions form
	if (pageState.step === "questions") {
		return (
			<div className="flex min-h-screen items-center justify-center p-4">
				<Card className="w-full max-w-2xl">
					<CardHeader>
						<CardTitle className="text-2xl">{taskTitle}</CardTitle>
						<p className="text-sm text-muted-foreground">
							{t("boardExpand.expandingTaskFrom", { board: boardTitle })}
						</p>
						<p className="text-sm text-muted-foreground">{t("boardExpand.answerQuestions")}</p>
					</CardHeader>
					<CardContent>
						<form onSubmit={handleSubmit} className="space-y-6">
							{pageState.questions.map((question) => (
								<QuestionField
									key={question.id}
									question={question}
									value={values[question.id]}
									onChange={(value) => handleChange(question.id, value)}
									disabled={false}
								/>
							))}
							<div className="flex gap-3">
								<Button
									type="button"
									variant="outline"
									onClick={() => navigate({ to: "/boards/$boardId", params: { boardId } })}
								>
									{t("boardExpand.cancel")}
								</Button>
								<Button type="submit" className="flex-1" disabled={!isValid()}>
									{t("boardExpand.generateBoard")}
								</Button>
							</div>
						</form>
					</CardContent>
				</Card>
			</div>
		);
	}

	// Generating (SSE progress)
	if (pageState.step === "generating") {
		const sseBody = {
			answers: Object.entries(pageState.answers).map(([question_id, value]) => ({
				question_id,
				value,
			})),
		};

		return (
			<BoardGenerationProgress
				sseUrl={`/api/tasks/${taskId}/generate-sub-board/stream`}
				sseBody={sseBody}
				onAbort={() => navigate({ to: "/boards/$boardId", params: { boardId } })}
				onComplete={(subBoardId) =>
					navigate({
						to: "/boards/$boardId",
						params: { boardId: subBoardId },
					})
				}
			/>
		);
	}

	// Error state
	if (pageState.step === "error") {
		return (
			<div className="flex min-h-screen items-center justify-center p-4">
				<div className="w-full max-w-md space-y-4">
					{contextHeader}
					{pageState.canRetry ? (
						<ErrorDisplay message={pageState.message} onRetry={handleRetryQuestions} />
					) : (
						<div className="text-center space-y-4">
							<p className="text-sm text-muted-foreground">{pageState.message}</p>
						</div>
					)}
					<div className="flex justify-center">
						<Button
							variant="outline"
							onClick={() => navigate({ to: "/boards/$boardId", params: { boardId } })}
						>
							{t("boardExpand.backToBoard")}
						</Button>
					</div>
				</div>
			</div>
		);
	}

	return null;
}
