import { type FormEvent, useState } from "react";
import type { QuestionSchema } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

// --- Internal state for managing option + other selections ---

interface FieldState {
	selectedOption: string;
	otherText: string;
	// multiselect only
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

// --- Unified Question Field ---

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
	const options = question.options ?? [];
	const hasOptions = options.length > 0;

	const [fieldState, setFieldState] = useState<FieldState>(() =>
		getInitialFieldState(question, value),
	);

	// Backward compatibility: no options → plain text input
	if (!hasOptions) {
		const stringValue = value === undefined ? "" : String(value);
		return (
			<QuestionFieldWrapper question={question}>
				<Input
					id={question.id}
					value={stringValue}
					onChange={(e) => onChange(e.target.value)}
					placeholder="Type your answer..."
					disabled={disabled}
				/>
			</QuestionFieldWrapper>
		);
	}

	// Multiselect: additive chips + other
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

	// Single-select (text, select, number): mutually exclusive chips + other
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

// --- Read-only answers display ---

function ReadOnlyAnswers({
	questions,
	answers,
	onEdit,
}: {
	questions: QuestionSchema[];
	answers: AnswerValues;
	onEdit: () => void;
}) {
	function formatAnswer(question: QuestionSchema): string {
		const value = answers[question.id];
		if (value === undefined || value === "") return "Not answered";
		if (Array.isArray(value)) return value.join(", ");
		return String(value);
	}

	return (
		<div className="space-y-4 rounded-lg border bg-muted/30 p-4">
			<div className="flex items-center justify-between">
				<p className="text-sm font-medium">Your answers</p>
				<Button variant="ghost" size="sm" onClick={onEdit}>
					Edit
				</Button>
			</div>
			<div className="space-y-3">
				{questions.map((q) => (
					<div key={q.id} className="space-y-1">
						<p className="text-sm font-medium">{q.text}</p>
						<p className="text-sm text-muted-foreground">{formatAnswer(q)}</p>
					</div>
				))}
			</div>
		</div>
	);
}

// --- Main form component ---

interface DynamicQuestionFormProps {
	goalTitle: string;
	initialQuestions: QuestionSchema[];
	followUpQuestions?: QuestionSchema[];
	initialAnswers?: AnswerValues;
	isRound1Submitted: boolean;
	onSubmitAnswers: (answers: AnswerValues, round: number) => void;
	isPending: boolean;
	onEdit: () => void;
}

export function DynamicQuestionForm({
	goalTitle,
	initialQuestions,
	followUpQuestions,
	initialAnswers,
	isRound1Submitted,
	onSubmitAnswers,
	isPending,
	onEdit,
}: DynamicQuestionFormProps) {
	const activeQuestions =
		isRound1Submitted && followUpQuestions ? followUpQuestions : initialQuestions;
	const round = isRound1Submitted && followUpQuestions ? 2 : 1;

	const [values, setValues] = useState<AnswerValues>(() => {
		if (round === 1 && initialAnswers) return { ...initialAnswers };
		return {};
	});

	function handleChange(questionId: string, value: string | string[] | number) {
		setValues((prev) => ({ ...prev, [questionId]: value }));
	}

	function isValid(): boolean {
		return activeQuestions.every((q) => {
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
		onSubmitAnswers(values, round);
	}

	return (
		<Card className="w-full max-w-2xl">
			<CardHeader>
				<CardTitle className="text-2xl">{goalTitle}</CardTitle>
				<p className="text-sm text-muted-foreground">
					{round === 1
						? "Help us understand your goal better by answering these questions."
						: "A few more questions to refine your plan."}
				</p>
			</CardHeader>
			<CardContent className="space-y-6">
				{isRound1Submitted && initialAnswers && (
					<ReadOnlyAnswers questions={initialQuestions} answers={initialAnswers} onEdit={onEdit} />
				)}
				<form onSubmit={handleSubmit} className="space-y-6">
					{activeQuestions.map((question) => (
						<QuestionField
							key={question.id}
							question={question}
							value={values[question.id]}
							onChange={(value) => handleChange(question.id, value)}
							disabled={isPending}
						/>
					))}
					<Button type="submit" className="w-full" disabled={isPending || !isValid()}>
						{isPending ? "Submitting..." : round === 2 ? "Complete" : "Continue"}
					</Button>
				</form>
			</CardContent>
		</Card>
	);
}
