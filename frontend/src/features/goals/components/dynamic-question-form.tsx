import { type FormEvent, useState } from "react";
import type { QuestionSchema } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type AnswerValues = Record<string, string | string[] | number>;

// --- Field renderers ---

function TextField({
	question,
	value,
	onChange,
	disabled,
}: {
	question: QuestionSchema;
	value: string;
	onChange: (value: string) => void;
	disabled: boolean;
}) {
	return (
		<Input
			id={question.id}
			value={value}
			onChange={(e) => onChange(e.target.value)}
			placeholder="Type your answer..."
			disabled={disabled}
		/>
	);
}

function NumberField({
	question,
	value,
	onChange,
	disabled,
}: {
	question: QuestionSchema;
	value: string;
	onChange: (value: string) => void;
	disabled: boolean;
}) {
	return (
		<Input
			id={question.id}
			type="number"
			value={value}
			onChange={(e) => onChange(e.target.value)}
			placeholder="Enter a number..."
			disabled={disabled}
		/>
	);
}

function SelectField({
	question,
	value,
	onChange,
	disabled,
}: {
	question: QuestionSchema;
	value: string;
	onChange: (value: string) => void;
	disabled: boolean;
}) {
	const options = question.options ?? [];
	return (
		<div className="space-y-2">
			{options.map((option) => (
				<label
					key={option}
					className="flex cursor-pointer items-center gap-2 rounded-lg border p-3 transition-colors hover:bg-accent has-[:checked]:border-primary has-[:checked]:bg-primary/5"
				>
					<input
						type="radio"
						name={question.id}
						value={option}
						checked={value === option}
						onChange={() => onChange(option)}
						disabled={disabled}
						className="accent-primary"
					/>
					<span className="text-sm">{option}</span>
				</label>
			))}
		</div>
	);
}

function MultiselectField({
	question,
	value,
	onChange,
	disabled,
}: {
	question: QuestionSchema;
	value: string[];
	onChange: (value: string[]) => void;
	disabled: boolean;
}) {
	const options = question.options ?? [];

	function handleToggle(option: string) {
		if (value.includes(option)) {
			onChange(value.filter((v) => v !== option));
		} else {
			onChange([...value, option]);
		}
	}

	return (
		<div className="space-y-2">
			{options.map((option) => (
				<label
					key={option}
					className="flex cursor-pointer items-center gap-2 rounded-lg border p-3 transition-colors hover:bg-accent has-[:checked]:border-primary has-[:checked]:bg-primary/5"
				>
					<input
						type="checkbox"
						value={option}
						checked={value.includes(option)}
						onChange={() => handleToggle(option)}
						disabled={disabled}
						className="accent-primary"
					/>
					<span className="text-sm">{option}</span>
				</label>
			))}
		</div>
	);
}

// --- Question field wrapper ---

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
	const stringValue = value === undefined ? "" : String(value);

	return (
		<div className="space-y-2">
			<Label htmlFor={question.id}>
				{question.text}
				{question.required && <span className="ml-1 text-destructive">*</span>}
			</Label>
			{question.type === "text" && (
				<TextField
					question={question}
					value={stringValue}
					onChange={onChange}
					disabled={disabled}
				/>
			)}
			{question.type === "number" && (
				<NumberField
					question={question}
					value={stringValue}
					onChange={(v) => onChange(v === "" ? "" : Number(v))}
					disabled={disabled}
				/>
			)}
			{question.type === "select" && (
				<SelectField
					question={question}
					value={stringValue}
					onChange={onChange}
					disabled={disabled}
				/>
			)}
			{question.type === "multiselect" && (
				<MultiselectField
					question={question}
					value={Array.isArray(value) ? value : []}
					onChange={onChange}
					disabled={disabled}
				/>
			)}
			{question.rationale && <p className="text-xs text-muted-foreground">{question.rationale}</p>}
		</div>
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
