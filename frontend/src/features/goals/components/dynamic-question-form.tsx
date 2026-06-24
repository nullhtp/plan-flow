import { type FormEvent, useEffect, useRef, useState } from "react";
import type { QuestionSchema, ReadinessSchema } from "@/api/generated/model";
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
import { useSimpleMode } from "@/shared/hooks/use-simple-mode";
import { GenerateFooter } from "./generate-footer";

type AnswerValues = Record<string, string | string[] | number>;

/** A completed or in-progress round of Q&A. */
export interface Round {
	round: number;
	questions: QuestionSchema[];
	answers: AnswerValues;
	readiness: ReadinessSchema | null;
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

	// Backward compatibility: no options -> plain text input
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

// --- Collapsible read-only round section ---

function CompletedRound({
	round,
	onEdit,
	simple = false,
}: {
	round: Round;
	onEdit: (roundNum: number) => void;
	simple?: boolean;
}) {
	const [expanded, setExpanded] = useState(false);
	const answeredCount = Object.keys(round.answers).length;

	function formatAnswer(question: QuestionSchema): string {
		const value = round.answers[question.id];
		if (value === undefined || value === "") return "Not answered";
		if (Array.isArray(value)) return value.join(", ");
		return String(value);
	}

	// Simple mode: a plain, always-visible read-only summary with no expand/Edit.
	if (simple) {
		return (
			<div className="space-y-3 rounded-lg border bg-muted/30 px-4 py-3">
				<p className="text-sm font-medium text-muted-foreground">Your answers</p>
				{round.questions.map((q) => (
					<div key={q.id} className="space-y-1">
						<p className="text-sm font-medium">{q.text}</p>
						<p className="text-sm text-muted-foreground">{formatAnswer(q)}</p>
					</div>
				))}
			</div>
		);
	}

	return (
		<div className="rounded-lg border bg-muted/30">
			<div className="flex w-full items-center justify-between px-4 py-3">
				<button
					type="button"
					className="flex flex-1 items-center gap-2 text-left"
					onClick={() => setExpanded(!expanded)}
				>
					<span className="text-sm font-medium">Round {round.round}</span>
					<span className="text-xs text-muted-foreground">
						{answeredCount} question{answeredCount !== 1 ? "s" : ""} answered
					</span>
					<svg
						width="16"
						height="16"
						viewBox="0 0 16 16"
						fill="none"
						className={`ml-auto transform transition-transform ${expanded ? "rotate-180" : ""}`}
						aria-hidden="true"
					>
						<title>Toggle</title>
						<path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
					</svg>
				</button>
				<Button
					variant="ghost"
					size="sm"
					className="ml-2 flex-shrink-0"
					onClick={() => onEdit(round.round)}
				>
					Edit
				</Button>
			</div>
			{expanded && (
				<div className="space-y-3 border-t px-4 py-3">
					{round.questions.map((q) => (
						<div key={q.id} className="space-y-1">
							<p className="text-sm font-medium">{q.text}</p>
							<p className="text-sm text-muted-foreground">{formatAnswer(q)}</p>
						</div>
					))}
				</div>
			)}
		</div>
	);
}

// --- Main form component ---

interface DynamicQuestionFormProps {
	goalTitle: string;
	/** All completed and current rounds. The last round is the active editable one. */
	rounds: Round[];
	/** Questions for the current (active) round. */
	activeQuestions: QuestionSchema[];
	/** Current round number (1-indexed). */
	currentRound: number;
	/** Latest readiness assessment (from most recent submission). */
	readiness: ReadinessSchema | null;
	/** Whether at least one round has been submitted. */
	hasCompletedRounds: boolean;
	/** Called when user submits current round's answers. */
	onSubmitAnswers: (answers: AnswerValues, round: number) => void;
	/** Called when user clicks Edit on a completed round. */
	onEditRound: (roundNum: number) => void;
	/** Called when user clicks Generate Board. */
	onGenerate: () => void;
	/** Whether an API call is in progress. */
	isPending: boolean;
	/** Whether answers are being processed (loading indicator). */
	isLoadingFollowUp: boolean;
}

export function DynamicQuestionForm({
	goalTitle,
	rounds,
	activeQuestions,
	currentRound,
	readiness,
	hasCompletedRounds,
	onSubmitAnswers,
	onEditRound,
	onGenerate,
	isPending,
	isLoadingFollowUp,
}: DynamicQuestionFormProps) {
	const { isSimpleMode } = useSimpleMode();
	const newQuestionsRef = useRef<HTMLFormElement>(null);

	const [values, setValues] = useState<AnswerValues>(() => {
		// If the current round has partial answers (from editing), pre-fill
		const currentRoundData = rounds.find((r) => r.round === currentRound);
		if (currentRoundData && Object.keys(currentRoundData.answers).length > 0) {
			return { ...currentRoundData.answers };
		}
		return {};
	});

	// Auto-scroll to new questions when they appear
	useEffect(() => {
		if (currentRound > 1 && newQuestionsRef.current) {
			newQuestionsRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
		}
	}, [currentRound]);

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
		onSubmitAnswers(values, currentRound);
	}

	// Completed rounds = all rounds except the last (active) one
	const completedRounds = rounds.filter(
		(r) => r.round < currentRound && Object.keys(r.answers).length > 0,
	);

	return (
		<div className={`w-full max-w-2xl ${hasCompletedRounds ? "pt-24" : ""}`}>
			{/* Header */}
			<div className="mb-6">
				<h1 className="text-2xl font-semibold tracking-tight">{goalTitle}</h1>
				<p className="mt-1 text-sm text-muted-foreground">
					{currentRound === 1
						? "Help us understand your goal better by answering these questions."
						: "Answer follow-up questions to improve your board, or generate now."}
				</p>
			</div>

			{/* Completed rounds — collapsible+editable normally, plain read-only in Simple mode */}
			<div className="space-y-4">
				{completedRounds.map((round) => (
					<CompletedRound
						key={round.round}
						round={round}
						onEdit={onEditRound}
						simple={isSimpleMode}
					/>
				))}
			</div>

			{/* Divider between completed and active */}
			{completedRounds.length > 0 && activeQuestions.length > 0 && (
				<div className="my-6 border-t" />
			)}

			{/* Loading indicator while generating follow-up questions */}
			{isLoadingFollowUp && (
				<div className="flex items-center justify-center gap-2 py-12">
					<div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
					<span className="text-sm text-muted-foreground">Generating follow-up questions...</span>
				</div>
			)}

			{/* Active round form */}
			{!isLoadingFollowUp && activeQuestions.length > 0 && (
				<form ref={newQuestionsRef} onSubmit={handleSubmit} className="space-y-6">
					{currentRound > 1 && (
						<p className="text-sm font-medium text-muted-foreground">
							{isSimpleMode ? "A few more questions" : `Round ${currentRound}`}
						</p>
					)}
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
						{isPending ? "Submitting..." : "Continue"}
					</Button>
				</form>
			)}

			{/* Sticky generate footer - visible after first round is answered */}
			{hasCompletedRounds && (
				<GenerateFooter
					readiness={readiness}
					onGenerate={onGenerate}
					isPending={isPending}
					simple={isSimpleMode}
				/>
			)}
		</div>
	);
}
