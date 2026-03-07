import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, X } from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import {
	getGetBoardEndpointApiBoardsBoardIdGetQueryKey,
	useGenerateSubBoardEndpointApiTasksTaskIdGenerateSubBoardPost,
	useSubBoardQuestionsEndpointApiTasksTaskIdSubBoardQuestionsPost,
} from "@/api/generated/boards/boards";
import type { QuestionSchema } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
	MultiselectOptionField,
	OptionField,
	parseMultiselectValue,
	parseOptionValue,
	QuestionFieldWrapper,
	serializeMultiselectValue,
	serializeOptionValue,
} from "@/shared/components/question-fields";

type AnswerValues = Record<string, string | string[] | number>;

type FlowState = "loading-questions" | "questions" | "generating" | "complete";

interface SubBoardCreationFlowProps {
	taskId: string;
	boardId: string;
	onComplete: () => void;
	onCancel: () => void;
}

// --- Internal state for managing option + other selections ---

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

// --- Compact Question Field using shared components ---

function CompactQuestionField({
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
	const options = question.options ?? [];
	const hasOptions = options.length > 0;

	const [fieldState, setFieldState] = useState<FieldState>(() =>
		getInitialFieldState(question, value),
	);

	// Backward compatibility: no options → plain text input
	if (!hasOptions) {
		const stringValue = value === undefined ? "" : String(value);
		return (
			<QuestionFieldWrapper question={question} compact>
				<Input
					id={question.id}
					value={stringValue}
					onChange={(e) => onChange(e.target.value)}
					placeholder="Type your answer..."
					disabled={disabled}
					className="h-8 text-xs"
				/>
			</QuestionFieldWrapper>
		);
	}

	// Multiselect: additive chips + other
	if (question.type === "multiselect") {
		return (
			<QuestionFieldWrapper question={question} compact>
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
					compact
				/>
			</QuestionFieldWrapper>
		);
	}

	// Single-select (text, select, number): mutually exclusive chips + other
	return (
		<QuestionFieldWrapper question={question} compact>
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
				compact
			/>
		</QuestionFieldWrapper>
	);
}

// --- Main flow component ---

export function SubBoardCreationFlow({
	taskId,
	boardId,
	onComplete,
	onCancel,
}: SubBoardCreationFlowProps) {
	const queryClient = useQueryClient();
	const [flowState, setFlowState] = useState<FlowState>("loading-questions");
	const [questions, setQuestions] = useState<QuestionSchema[]>([]);
	const [values, setValues] = useState<AnswerValues>({});

	const questionsQuery = useSubBoardQuestionsEndpointApiTasksTaskIdSubBoardQuestionsPost({
		mutation: {
			onSuccess: (response: any) => {
				if (response.status !== 200) return;
				// Cast the loosely-typed question items to QuestionSchema
				const qs = (response.data.questions ?? []) as unknown as QuestionSchema[];
				setQuestions(qs);
				setFlowState("questions");
			},
			onError: () => {
				toast.error("Failed to generate questions. Please try again.");
				onCancel();
			},
		},
	});

	const generateMutation = useGenerateSubBoardEndpointApiTasksTaskIdGenerateSubBoardPost({
		mutation: {
			onSuccess: (response: any) => {
				if (response.status !== 200) return;
				setFlowState("complete");
				// Invalidate the board query to refresh the DAG with sub-board data
				const boardQueryKey = getGetBoardEndpointApiBoardsBoardIdGetQueryKey(boardId);
				queryClient.invalidateQueries({ queryKey: boardQueryKey });
				toast.success("Sub-board created successfully!");
			},
			onError: () => {
				toast.error("Failed to generate sub-board. Please try again.");
				setFlowState("questions");
			},
		},
	});

	// Trigger question loading on mount
	const didFetch = useRef(false);
	useEffect(() => {
		if (!didFetch.current) {
			didFetch.current = true;
			questionsQuery.mutate({ taskId });
		}
	}, [taskId, questionsQuery.mutate]);

	function handleChange(questionId: string, value: string | string[] | number) {
		setValues((prev) => ({ ...prev, [questionId]: value }));
	}

	function isValid(): boolean {
		return questions.every((q) => {
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

		const answers = Object.entries(values).map(([question_id, value]) => ({
			question_id,
			value,
		}));

		setFlowState("generating");
		generateMutation.mutate({ taskId, data: { answers } });
	}

	// --- Loading questions state ---
	if (flowState === "loading-questions") {
		return (
			<div className="rounded-lg border border-violet-200 bg-violet-50/30 dark:border-violet-800 dark:bg-violet-950/20 p-4">
				<div className="flex items-center justify-between mb-3">
					<h4 className="text-sm font-medium text-violet-700 dark:text-violet-300">
						Expand to Board
					</h4>
					<Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={onCancel}>
						<X className="h-3.5 w-3.5" />
					</Button>
				</div>
				<div className="flex items-center justify-center py-6">
					<Loader2 className="h-5 w-5 animate-spin text-violet-500 mr-2" />
					<span className="text-sm text-muted-foreground">Preparing questions...</span>
				</div>
			</div>
		);
	}

	// --- Question form state ---
	if (flowState === "questions") {
		return (
			<div className="rounded-lg border border-violet-200 bg-violet-50/30 dark:border-violet-800 dark:bg-violet-950/20 p-4">
				<div className="flex items-center justify-between mb-3">
					<h4 className="text-sm font-medium text-violet-700 dark:text-violet-300">
						Expand to Board
					</h4>
					<Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={onCancel}>
						<X className="h-3.5 w-3.5" />
					</Button>
				</div>
				<p className="text-xs text-muted-foreground mb-3">
					Answer a few questions to help generate a task board for this work.
				</p>
				<form onSubmit={handleSubmit} className="space-y-4">
					{questions.map((question) => (
						<CompactQuestionField
							key={question.id}
							question={question}
							value={values[question.id]}
							onChange={(value) => handleChange(question.id, value)}
							disabled={false}
						/>
					))}
					<div className="flex gap-2">
						<Button type="button" variant="outline" size="sm" className="flex-1" onClick={onCancel}>
							Cancel
						</Button>
						<Button
							type="submit"
							size="sm"
							className="flex-1 bg-violet-600 hover:bg-violet-700 text-white"
							disabled={!isValid()}
						>
							Generate Board
						</Button>
					</div>
				</form>
			</div>
		);
	}

	// --- Generating state ---
	if (flowState === "generating") {
		return (
			<div className="rounded-lg border border-violet-200 bg-violet-50/30 dark:border-violet-800 dark:bg-violet-950/20 p-4">
				<div className="flex items-center justify-between mb-3">
					<h4 className="text-sm font-medium text-violet-700 dark:text-violet-300">
						Expand to Board
					</h4>
				</div>
				<div className="flex flex-col items-center justify-center py-6 gap-3">
					<Loader2 className="h-6 w-6 animate-spin text-violet-500" />
					<div className="text-center">
						<p className="text-sm font-medium">Generating your board...</p>
						<p className="text-xs text-muted-foreground mt-1">
							Creating tasks, dependencies, and enrichments
						</p>
					</div>
				</div>
			</div>
		);
	}

	// --- Complete state ---
	return (
		<div className="rounded-lg border border-green-200 bg-green-50/30 dark:border-green-800 dark:bg-green-950/20 p-4">
			<div className="flex flex-col items-center justify-center py-4 gap-3">
				<CheckCircle2 className="h-8 w-8 text-green-600" />
				<div className="text-center">
					<p className="text-sm font-medium text-green-700 dark:text-green-300">Board created!</p>
					<p className="text-xs text-muted-foreground mt-1">
						The task has been expanded into a full board.
					</p>
				</div>
				<Button
					size="sm"
					variant="outline"
					className="border-green-300 text-green-700 hover:bg-green-100"
					onClick={onComplete}
				>
					Done
				</Button>
			</div>
		</div>
	);
}
