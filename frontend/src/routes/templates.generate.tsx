import { createRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ErrorDisplay } from "@/features/goals/components/error-display";
import { LoadingState } from "@/features/goals/components/loading-state";
import { ReadinessIndicator } from "@/features/goals/components/readiness-indicator";
import { VagueGoalRejection } from "@/features/goals/components/vague-goal-rejection";
import { TemplateDagView } from "@/features/templates/components/TemplateDagView";
import { useCategoriesData } from "@/features/templates/hooks/use-categories";
import {
	useExtractContent,
	useSaveGeneratedTemplate,
	useTemplateClassify,
	useTemplateSubmitAnswers,
} from "@/features/templates/hooks/use-template-generation";
import {
	type StreamedTemplateTask,
	useTemplateGenerationStream,
} from "@/features/templates/hooks/use-template-generation-stream";
import type {
	TemplateClassificationData,
	TemplateQuestionSchema,
	TemplateReadinessSchema,
} from "@/features/templates/types";
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

type AnswerValues = Record<string, string>;

interface TemplateRound {
	round: number;
	questions: TemplateQuestionSchema[];
	answers: AnswerValues;
	readiness: TemplateReadinessSchema | null;
}

type PageState =
	| { step: "input" }
	| { step: "loading" }
	| { step: "rejected"; reason: string; suggestions: string[] }
	| {
			step: "questions";
			classification: TemplateClassificationData;
			rounds: TemplateRound[];
			activeQuestions: TemplateQuestionSchema[];
			currentRound: number;
			readiness: TemplateReadinessSchema | null;
	  }
	| {
			step: "answersLoading";
			classification: TemplateClassificationData;
			rounds: TemplateRound[];
			readiness: TemplateReadinessSchema | null;
	  }
	| {
			step: "generating";
			classification: TemplateClassificationData;
			rounds: TemplateRound[];
	  }
	| {
			step: "preview";
			classification: TemplateClassificationData;
			suggestedTitle: string;
			tasks: StreamedTemplateTask[];
			edges: { source: string; target: string }[];
	  }
	| { step: "error"; message: string; retryAction: () => void };

type InputTab = "describe" | "text" | "document" | "url";

export const templatesGenerateRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/templates/generate",
	component: TemplatesGeneratePage,
});

function TemplatesGeneratePage() {
	const navigate = useNavigate();
	const classify = useTemplateClassify();
	const submitAnswers = useTemplateSubmitAnswers();
	const extractContent = useExtractContent();
	const saveTemplate = useSaveGeneratedTemplate();
	const categories = useCategoriesData();

	const [pageState, setPageState] = useState<PageState>({ step: "input" });
	const [inputTab, setInputTab] = useState<InputTab>("describe");
	const [describeText, setDescribeText] = useState("");
	const [pasteText, setPasteText] = useState("");
	const [urlText, setUrlText] = useState("");
	const [extractedContent, setExtractedContent] = useState<string | null>(null);
	const [titleHint, setTitleHint] = useState("");
	// Preserved raw input for the pipeline
	const [rawInput, setRawInput] = useState("");

	function getErrorMessage(status: number): string {
		if (status === 503 || status === 504) {
			return "Our AI is taking longer than expected. Please try again.";
		}
		return "Something went wrong. Please try again.";
	}

	// ── Input Step ──────────────────────────────────────

	async function handleClassify() {
		let content = "";
		let inputType: "describe" | "text" | "file" | "url" = "describe";

		if (inputTab === "describe") {
			content = describeText;
			inputType = "describe";
		} else if (inputTab === "text") {
			content = pasteText;
			inputType = "text";
		} else if (inputTab === "url") {
			// Extract content from URL first
			inputType = "url";
			setPageState({ step: "loading" });
			try {
				const result = await extractContent.mutateAsync({ url: urlText });
				content = result.content;
				setExtractedContent(result.content);
			} catch {
				setPageState({
					step: "error",
					message: "Failed to extract content from URL. Please try again.",
					retryAction: handleClassify,
				});
				return;
			}
		} else if (inputTab === "document") {
			// File extraction handled separately via handleFileUpload
			content = extractedContent || "";
			inputType = "file";
		}

		if (!content.trim()) return;

		setRawInput(content);
		setPageState({ step: "loading" });

		classify.mutate(
			{
				input_type: inputType,
				content,
				title: titleHint || undefined,
			},
			{
				onSuccess: (data) => {
					if (data.is_rejected) {
						setPageState({
							step: "rejected",
							reason: data.rejection_reason || "Input is too vague.",
							suggestions: data.refinement_suggestions,
						});
						return;
					}
					const initialRound: TemplateRound = {
						round: 1,
						questions: data.questions,
						answers: {},
						readiness: data.readiness,
					};
					setPageState({
						step: "questions",
						classification: data.classification,
						rounds: [initialRound],
						activeQuestions: data.questions,
						currentRound: 1,
						readiness: data.readiness,
					});
				},
				onError: (error: unknown) => {
					const err = error as { status?: number };
					setPageState({
						step: "error",
						message: getErrorMessage(err.status ?? 500),
						retryAction: handleClassify,
					});
				},
			},
		);
	}

	function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
		const file = e.target.files?.[0];
		if (!file) return;
		extractContent.mutate(
			{ file },
			{
				onSuccess: (result) => {
					setExtractedContent(result.content);
				},
			},
		);
	}

	// ── Question Step ───────────────────────────────────

	function handleSubmitAnswers(
		classification: TemplateClassificationData,
		rounds: TemplateRound[],
		readiness: TemplateReadinessSchema | null,
		answers: AnswerValues,
		round: number,
	) {
		const updatedRounds = rounds.map((r) => (r.round === round ? { ...r, answers } : r));

		setPageState({
			step: "answersLoading",
			classification,
			rounds: updatedRounds,
			readiness,
		});

		const previousRounds = updatedRounds.map((r) => ({
			round: r.round,
			questions: r.questions.map((q) => ({
				id: q.id,
				text: q.text,
				type: q.type,
				options: q.options,
			})),
			answers: r.answers,
		}));

		submitAnswers.mutate(
			{
				answers,
				round,
				classification,
				previous_rounds: previousRounds,
				content: extractedContent,
				raw_input: rawInput,
			},
			{
				onSuccess: (data) => {
					const newReadiness = data.readiness ?? readiness;
					const roundsWithReadiness = updatedRounds.map((r) =>
						r.round === round ? { ...r, readiness: newReadiness } : r,
					);

					if (data.is_ready || !data.next_questions.length) {
						// No more questions
						setPageState({
							step: "questions",
							classification,
							rounds: roundsWithReadiness,
							activeQuestions: [],
							currentRound: round,
							readiness: newReadiness,
						});
					} else {
						const newRound: TemplateRound = {
							round: data.next_round,
							questions: data.next_questions,
							answers: {},
							readiness: null,
						};
						setPageState({
							step: "questions",
							classification,
							rounds: [...roundsWithReadiness, newRound],
							activeQuestions: data.next_questions,
							currentRound: data.next_round,
							readiness: newReadiness,
						});
					}
				},
				onError: (error: unknown) => {
					const err = error as { status?: number };
					setPageState({
						step: "error",
						message: getErrorMessage(err.status ?? 500),
						retryAction: () =>
							handleSubmitAnswers(classification, rounds, readiness, answers, round),
					});
				},
			},
		);
	}

	function handleGenerate(classification: TemplateClassificationData, rounds: TemplateRound[]) {
		setPageState({
			step: "generating",
			classification,
			rounds,
		});
	}

	// ── Render ───────────────────────────────────────────

	if (pageState.step === "input") {
		const canSubmit =
			(inputTab === "describe" && describeText.trim().length > 0) ||
			(inputTab === "text" && pasteText.trim().length > 0) ||
			(inputTab === "url" && urlText.trim().length > 0) ||
			(inputTab === "document" && extractedContent !== null);

		return (
			<div className="mx-auto min-h-screen max-w-2xl px-4 py-8">
				<div className="mb-6 flex items-center justify-between">
					<h1 className="text-2xl font-bold">Generate Template</h1>
					<Button variant="outline" onClick={() => navigate({ to: "/templates" })}>
						Cancel
					</Button>
				</div>

				{/* Tab selector */}
				<div className="mb-4 flex gap-1 rounded-lg border p-1">
					{(["describe", "text", "document", "url"] as InputTab[]).map((tab) => (
						<button
							key={tab}
							type="button"
							onClick={() => setInputTab(tab)}
							className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
								inputTab === tab
									? "bg-primary text-primary-foreground"
									: "text-muted-foreground hover:text-foreground"
							}`}
						>
							{tab === "describe"
								? "Describe"
								: tab === "text"
									? "Text"
									: tab === "document"
										? "Document"
										: "URL"}
						</button>
					))}
				</div>

				{/* Tab content */}
				<div className="space-y-4">
					{inputTab === "describe" && (
						<div className="space-y-2">
							<Label>Describe the template you want</Label>
							<Textarea
								placeholder="e.g., A template for launching a SaaS product, covering market research, MVP development, beta testing, and go-to-market strategy..."
								value={describeText}
								onChange={(e) => setDescribeText(e.target.value)}
								rows={5}
								className="resize-none"
							/>
						</div>
					)}
					{inputTab === "text" && (
						<div className="space-y-2">
							<Label>Paste content to create a template from</Label>
							<Textarea
								placeholder="Paste an article, process document, checklist, or any content that describes a project workflow..."
								value={pasteText}
								onChange={(e) => setPasteText(e.target.value)}
								rows={8}
								className="resize-none"
							/>
						</div>
					)}
					{inputTab === "document" && (
						<div className="space-y-2">
							<Label>Upload a document (PDF, DOCX, TXT, MD)</Label>
							<Input type="file" accept=".pdf,.docx,.txt,.md" onChange={handleFileUpload} />
							{extractContent.isPending && (
								<p className="text-sm text-muted-foreground">Extracting content...</p>
							)}
							{extractedContent && (
								<p className="text-sm text-green-600">
									Content extracted ({extractedContent.length.toLocaleString()} characters)
								</p>
							)}
						</div>
					)}
					{inputTab === "url" && (
						<div className="space-y-2">
							<Label>Enter a URL to extract content from</Label>
							<Input
								type="url"
								placeholder="https://example.com/article"
								value={urlText}
								onChange={(e) => setUrlText(e.target.value)}
							/>
						</div>
					)}

					{/* Optional title hint */}
					<div className="space-y-2">
						<Label className="text-muted-foreground">Template title (optional)</Label>
						<Input
							placeholder="e.g., SaaS Product Launch"
							value={titleHint}
							onChange={(e) => setTitleHint(e.target.value)}
						/>
					</div>

					<Button
						onClick={handleClassify}
						disabled={!canSubmit || classify.isPending || extractContent.isPending}
						className="w-full"
						size="lg"
					>
						{classify.isPending ? "Analyzing..." : "Continue"}
					</Button>
				</div>
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
						setDescribeText(suggestion);
						setInputTab("describe");
						setPageState({ step: "input" });
					}}
					onTryAgain={() => setPageState({ step: "input" })}
				/>
			</div>
		);
	}

	if (pageState.step === "questions") {
		return (
			<TemplateQuestionStep
				classification={pageState.classification}
				rounds={pageState.rounds}
				activeQuestions={pageState.activeQuestions}
				currentRound={pageState.currentRound}
				readiness={pageState.readiness}
				onSubmitAnswers={(answers, round) =>
					handleSubmitAnswers(
						pageState.classification,
						pageState.rounds,
						pageState.readiness,
						answers,
						round,
					)
				}
				onGenerate={() => handleGenerate(pageState.classification, pageState.rounds)}
				isPending={false}
			/>
		);
	}

	if (pageState.step === "answersLoading") {
		return (
			<TemplateQuestionStep
				classification={pageState.classification}
				rounds={pageState.rounds}
				activeQuestions={[]}
				currentRound={
					pageState.rounds.length > 0 ? pageState.rounds[pageState.rounds.length - 1].round + 1 : 2
				}
				readiness={pageState.readiness}
				onSubmitAnswers={() => {}}
				onGenerate={() => {}}
				isPending={true}
			/>
		);
	}

	if (pageState.step === "generating") {
		return (
			<TemplateGeneratingStep
				classification={pageState.classification}
				rounds={pageState.rounds}
				rawInput={rawInput}
				content={extractedContent}
				titleHint={titleHint}
				onComplete={(title, tasks, edges) =>
					setPageState({
						step: "preview",
						classification: pageState.classification,
						suggestedTitle: title,
						tasks,
						edges,
					})
				}
				onAbort={() => setPageState({ step: "input" })}
			/>
		);
	}

	if (pageState.step === "preview") {
		return (
			<TemplatePreviewStep
				classification={pageState.classification}
				suggestedTitle={pageState.suggestedTitle}
				tasks={pageState.tasks}
				edges={pageState.edges}
				categories={categories}
				onSave={async (title, description, categoryId, visibility, createBoard, saveTasks) => {
					const result = await saveTemplate.mutateAsync({
						title,
						description,
						category_id: categoryId,
						visibility,
						create_board: createBoard,
						tasks: saveTasks.map((t) => ({
							id: t.id,
							title: t.title,
							description: t.description,
							is_goal_node: t.is_goal_node,
							depends_on: t.depends_on,
							subtasks: t.subtasks,
							priority: t.priority,
							estimated_minutes: t.estimated_minutes,
						})),
					});
					navigate({ to: "/templates/$templateId", params: { templateId: result.id } });
				}}
				isSaving={saveTemplate.isPending}
				onBack={() => setPageState({ step: "input" })}
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

// ── Question Step Component ─────────────────────────────

interface TemplateQuestionStepProps {
	classification: TemplateClassificationData;
	rounds: TemplateRound[];
	activeQuestions: TemplateQuestionSchema[];
	currentRound: number;
	readiness: TemplateReadinessSchema | null;
	onSubmitAnswers: (answers: AnswerValues, round: number) => void;
	onGenerate: () => void;
	isPending: boolean;
}

function TemplateQuestionStep({
	classification,
	rounds,
	activeQuestions,
	currentRound,
	readiness,
	onSubmitAnswers,
	onGenerate,
	isPending,
}: TemplateQuestionStepProps) {
	const [answers, setAnswers] = useState<AnswerValues>(() => {
		const activeRound = rounds.find((r) => r.round === currentRound);
		return activeRound?.answers ?? {};
	});

	const hasCompletedRounds = rounds.some(
		(r) => r.round < currentRound && Object.keys(r.answers).length > 0,
	);

	const allRequiredAnswered = activeQuestions
		.filter((q) => q.required)
		.every((q) => {
			const val = answers[q.id];
			return val && val.trim().length > 0;
		});

	return (
		<div className="mx-auto min-h-screen max-w-2xl px-4 py-8">
			{/* Generate footer */}
			{hasCompletedRounds && (
				<div className="fixed inset-x-0 top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
					<div className="mx-auto max-w-2xl px-4 py-3">
						<div className="flex items-center justify-between gap-4">
							{readiness ? (
								<ReadinessIndicator readiness={readiness} />
							) : (
								<div className="flex-1" />
							)}
							<Button size="lg" onClick={onGenerate} disabled={isPending}>
								{isPending ? "Generating..." : "Generate Template"}
							</Button>
						</div>
						{readiness?.summary && (
							<p className="mt-1.5 text-xs leading-normal text-muted-foreground">
								{readiness.summary}
							</p>
						)}
					</div>
				</div>
			)}

			<div className={hasCompletedRounds ? "pt-20" : ""}>
				<h2 className="mb-1 text-lg font-semibold">{classification.suggested_title}</h2>
				<p className="mb-6 text-sm text-muted-foreground">
					Answer these questions to help us create a better template.
				</p>

				{/* Completed rounds (read-only) */}
				{rounds
					.filter((r) => r.round < currentRound && Object.keys(r.answers).length > 0)
					.map((r) => (
						<div key={r.round} className="mb-6 rounded-lg border bg-muted/30 p-4">
							<p className="mb-2 text-xs font-medium text-muted-foreground">
								Round {r.round} (completed)
							</p>
							{r.questions.map((q) => (
								<div key={q.id} className="mb-2">
									<p className="text-sm font-medium">{q.text}</p>
									<p className="text-sm text-muted-foreground">
										{r.answers[q.id] || "(not answered)"}
									</p>
								</div>
							))}
						</div>
					))}

				{/* Active questions */}
				{activeQuestions.length > 0 ? (
					<div className="space-y-6">
						{activeQuestions.map((q) => (
							<TemplateQuestionField
								key={q.id}
								question={q}
								value={answers[q.id] ?? ""}
								onChange={(val) => setAnswers((prev) => ({ ...prev, [q.id]: val }))}
							/>
						))}
						<Button
							onClick={() => onSubmitAnswers(answers, currentRound)}
							disabled={!allRequiredAnswered || isPending}
							className="w-full"
						>
							{isPending ? "Submitting..." : "Submit Answers"}
						</Button>
					</div>
				) : (
					!isPending && (
						<p className="text-center text-sm text-muted-foreground">
							All questions answered. Click "Generate Template" above to proceed.
						</p>
					)
				)}

				{isPending && (
					<div className="flex items-center justify-center py-8">
						<p className="text-sm text-muted-foreground">Generating follow-up questions...</p>
					</div>
				)}
			</div>
		</div>
	);
}

// ── Question Field Component ────────────────────────────

interface TemplateQuestionFieldProps {
	question: TemplateQuestionSchema;
	value: string;
	onChange: (value: string) => void;
}

function TemplateQuestionField({ question, value, onChange }: TemplateQuestionFieldProps) {
	const options = question.options ?? [];

	if (question.type === "multiselect") {
		// Parse the stored string value back into an array for multiselect
		let arrayValue: string[] = [];
		if (value) {
			try {
				const parsed = JSON.parse(value);
				if (Array.isArray(parsed)) arrayValue = parsed;
			} catch {
				// Legacy: comma-separated or single value
				if (value.trim()) arrayValue = [value];
			}
		}
		const parsed = parseMultiselectValue(arrayValue, options);
		return (
			<QuestionFieldWrapper question={question} compact>
				<MultiselectOptionField
					question={question}
					selectedOptions={parsed.selectedOptions}
					otherText={parsed.otherText}
					onToggleOption={(option) => {
						const next = parsed.selectedOptions.includes(option)
							? parsed.selectedOptions.filter((o) => o !== option)
							: [...parsed.selectedOptions, option];
						onChange(JSON.stringify(serializeMultiselectValue(next, parsed.otherText)));
					}}
					onOtherChange={(text) => {
						onChange(JSON.stringify(serializeMultiselectValue(parsed.selectedOptions, text)));
					}}
					disabled={false}
					compact
				/>
			</QuestionFieldWrapper>
		);
	}

	if (question.type === "select" || question.type === "number") {
		const parsed = parseOptionValue(value, options);
		return (
			<QuestionFieldWrapper question={question} compact>
				<OptionField
					question={question}
					value={parsed.selectedOption}
					otherText={parsed.otherText}
					onSelectOption={(option) => onChange(serializeOptionValue(option, ""))}
					onOtherChange={(text) => onChange(serializeOptionValue("", text))}
					disabled={false}
					compact
				/>
			</QuestionFieldWrapper>
		);
	}

	// text type with options
	if (options.length > 0) {
		const parsed = parseOptionValue(value, options);
		return (
			<QuestionFieldWrapper question={question} compact>
				<OptionField
					question={question}
					value={parsed.selectedOption}
					otherText={parsed.otherText}
					onSelectOption={(option) => onChange(serializeOptionValue(option, ""))}
					onOtherChange={(text) => onChange(serializeOptionValue("", text))}
					disabled={false}
					compact
				/>
			</QuestionFieldWrapper>
		);
	}

	// plain text
	return (
		<QuestionFieldWrapper question={question} compact>
			<Textarea
				value={value}
				onChange={(e) => onChange(e.target.value)}
				placeholder="Type your answer..."
				rows={2}
				className="resize-none"
			/>
		</QuestionFieldWrapper>
	);
}

// ── Generating Step Component ───────────────────────────

interface TemplateGeneratingStepProps {
	classification: TemplateClassificationData;
	rounds: TemplateRound[];
	rawInput: string;
	content: string | null;
	titleHint: string;
	onComplete: (
		title: string,
		tasks: StreamedTemplateTask[],
		edges: { source: string; target: string }[],
	) => void;
	onAbort: () => void;
}

function TemplateGeneratingStep({
	classification,
	rounds,
	rawInput,
	content,
	titleHint,
	onComplete,
	onAbort,
}: TemplateGeneratingStepProps) {
	const didCompleteRef = useRef(false);

	const sseBody = useRef({
		raw_input: rawInput,
		classification,
		qa_rounds: rounds.map((r) => ({
			round: r.round,
			questions: r.questions.map((q) => ({
				id: q.id,
				text: q.text,
				type: q.type,
				options: q.options,
			})),
			answers: r.answers,
		})),
		content,
		title: titleHint || null,
	}).current;

	const stream = useTemplateGenerationStream({
		sseUrl: "/api/templates/generate/stream",
		sseBody,
	});

	// Start the stream on mount
	const didStartRef = useRef(false);
	useEffect(() => {
		if (!didStartRef.current) {
			didStartRef.current = true;
			stream.start();
		}
		return () => {
			stream.abort();
		};
	}, [stream.start, stream.abort]);

	// Listen for completion — tasks and edges are captured by the stream hook
	useEffect(() => {
		if (stream.phase === "complete" && !didCompleteRef.current) {
			didCompleteRef.current = true;
			setTimeout(() => {
				onComplete(
					stream.boardTitle || titleHint || classification.suggested_title,
					stream.tasks,
					stream.edges,
				);
			}, 1000);
		}
	}, [
		stream.phase,
		stream.boardTitle,
		stream.tasks,
		stream.edges,
		onComplete,
		titleHint,
		classification.suggested_title,
	]);

	const progressPercent =
		stream.totalCount > 0 ? Math.round((stream.enrichedCount / stream.totalCount) * 100) : 0;

	const phaseText = (() => {
		switch (stream.phase) {
			case "idle":
			case "connecting":
				return "Preparing template generation...";
			case "researching":
				return "Researching best practices...";
			case "skeleton":
				return "Building template structure...";
			case "enriching":
				return `Adding details... (${stream.enrichedCount}/${stream.totalCount})`;
			case "complete":
				return "Template ready!";
			case "error":
				return "Generation failed";
			default:
				return "Processing...";
		}
	})();

	return (
		<div className="flex min-h-screen items-center justify-center p-4">
			<div className="w-full max-w-md space-y-6 text-center">
				<h2 className="text-xl font-semibold">{phaseText}</h2>

				{stream.phase === "enriching" && (
					<div className="mx-auto h-2 w-full max-w-xs overflow-hidden rounded-full bg-muted">
						<div
							className="h-full rounded-full bg-primary transition-all duration-300"
							style={{ width: `${progressPercent}%` }}
						/>
					</div>
				)}

				{stream.boardTitle && <p className="text-sm text-muted-foreground">{stream.boardTitle}</p>}

				{/* Recent log entries */}
				<div className="mx-auto max-w-sm space-y-1">
					{stream.log.slice(0, 6).map((entry) => (
						<p key={entry.id} className="text-xs text-muted-foreground">
							{entry.message}
						</p>
					))}
				</div>

				{stream.phase === "error" && (
					<div className="flex justify-center gap-2">
						<Button variant="outline" onClick={onAbort}>
							Back
						</Button>
						<Button onClick={() => stream.start()}>Try Again</Button>
					</div>
				)}
			</div>
		</div>
	);
}

// ── Preview Step Component ──────────────────────────────

interface TemplatePreviewStepProps {
	classification: TemplateClassificationData;
	suggestedTitle: string;
	tasks: StreamedTemplateTask[];
	edges: { source: string; target: string }[];
	categories: { id: string; name: string; slug: string }[];
	onSave: (
		title: string,
		description: string | null,
		categoryId: string | null,
		visibility: string,
		createBoard: boolean,
		tasks: StreamedTemplateTask[],
	) => Promise<void>;
	isSaving: boolean;
	onBack: () => void;
}

function TemplatePreviewStep({
	suggestedTitle,
	tasks: initialTasks,
	edges: initialEdges,
	categories,
	onSave,
	isSaving,
	onBack,
}: TemplatePreviewStepProps) {
	const [title, setTitle] = useState(suggestedTitle);
	const [description, setDescription] = useState("");
	const [categoryId, setCategoryId] = useState<string | null>(null);
	const [visibility, setVisibility] = useState("private");
	const [createBoard, setCreateBoard] = useState(false);
	const [tasks, setTasks] = useState<StreamedTemplateTask[]>(initialTasks);
	const [edges, setEdges] = useState<{ source: string; target: string }[]>(initialEdges);

	// Task editing
	const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
	const selectedTask = tasks.find((t) => t.id === selectedTaskId);

	function updateTask(id: string, updates: Partial<StreamedTemplateTask>) {
		setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, ...updates } : t)));
	}

	function removeTask(id: string) {
		setTasks((prev) => {
			const filtered = prev.filter((t) => t.id !== id);
			return filtered.map((t) => ({
				...t,
				depends_on: t.depends_on.filter((d) => d !== id),
			}));
		});
		// Remove edges involving this task
		setEdges((prev) => prev.filter((e) => e.source !== id && e.target !== id));
		if (selectedTaskId === id) setSelectedTaskId(null);
	}

	function addTask() {
		const newId = `t_new_${Date.now()}`;
		const newTask: StreamedTemplateTask = {
			id: newId,
			title: "New Task",
			depends_on: [],
			is_goal_node: false,
			description: "",
			priority: null,
			estimated_minutes: null,
			subtasks: [],
		};
		setTasks((prev) => [...prev, newTask]);
		setSelectedTaskId(newId);
	}

	// Sync depends_on when edges change
	function handleEdgesChange(newEdges: { source: string; target: string }[]) {
		setEdges(newEdges);
		// Rebuild depends_on for all tasks from edges
		setTasks((prev) =>
			prev.map((t) => ({
				...t,
				depends_on: newEdges.filter((e) => e.target === t.id).map((e) => e.source),
			})),
		);
	}

	return (
		<div className="flex h-screen flex-col">
			{/* Header */}
			<div className="flex items-center justify-between border-b px-4 py-3">
				<h1 className="text-xl font-bold">Preview Template</h1>
				<div className="flex items-center gap-2">
					<Button variant="outline" size="sm" onClick={addTask}>
						Add Task
					</Button>
					<Button variant="outline" size="sm" onClick={onBack}>
						Back
					</Button>
				</div>
			</div>

			<div className="flex flex-1 overflow-hidden">
				{/* DAG View — fills available space */}
				<div className="flex-1">
					<TemplateDagView
						tasks={tasks}
						edges={edges}
						selectedTaskId={selectedTaskId}
						onSelectTask={setSelectedTaskId}
						onEdgesChange={handleEdgesChange}
					/>
				</div>

				{/* Right sidebar: task editor + save form */}
				<div className="w-80 shrink-0 overflow-y-auto border-l bg-background p-4">
					<div className="space-y-6">
						{/* Task detail editor */}
						{selectedTask && (
							<div className="rounded-lg border p-4">
								<h4 className="mb-3 font-semibold">Edit Task</h4>
								<div className="space-y-3">
									<div>
										<Label>Title</Label>
										<Input
											value={selectedTask.title}
											onChange={(e) => updateTask(selectedTask.id, { title: e.target.value })}
										/>
									</div>
									<div>
										<Label>Description</Label>
										<Textarea
											value={selectedTask.description}
											onChange={(e) =>
												updateTask(selectedTask.id, {
													description: e.target.value,
												})
											}
											rows={3}
											className="resize-none"
										/>
									</div>
									<div>
										<Label>Priority</Label>
										<select
											value={selectedTask.priority || ""}
											onChange={(e) =>
												updateTask(selectedTask.id, {
													priority: e.target.value || null,
												})
											}
											className="w-full rounded-md border px-3 py-2 text-sm"
										>
											<option value="">None</option>
											<option value="low">Low</option>
											<option value="medium">Medium</option>
											<option value="high">High</option>
										</select>
									</div>
									<div>
										<Label>Estimated minutes</Label>
										<Input
											type="number"
											value={selectedTask.estimated_minutes ?? ""}
											onChange={(e) =>
												updateTask(selectedTask.id, {
													estimated_minutes: e.target.value
														? Number.parseInt(e.target.value)
														: null,
												})
											}
										/>
									</div>
									<Button
										variant="destructive"
										size="sm"
										onClick={() => removeTask(selectedTask.id)}
									>
										Delete Task
									</Button>
								</div>
							</div>
						)}

						{/* Save form */}
						<div className="rounded-lg border p-4">
							<h4 className="mb-3 font-semibold">Save Template</h4>
							<div className="space-y-3">
								<div>
									<Label>Title</Label>
									<Input value={title} onChange={(e) => setTitle(e.target.value)} />
								</div>
								<div>
									<Label>Description</Label>
									<Textarea
										value={description}
										onChange={(e) => setDescription(e.target.value)}
										rows={2}
										className="resize-none"
									/>
								</div>
								<div>
									<Label>Category</Label>
									<select
										value={categoryId || ""}
										onChange={(e) => setCategoryId(e.target.value || null)}
										className="w-full rounded-md border px-3 py-2 text-sm"
									>
										<option value="">None</option>
										{categories.map((c) => (
											<option key={c.id} value={c.id}>
												{c.name}
											</option>
										))}
									</select>
								</div>
								<div>
									<Label>Visibility</Label>
									<select
										value={visibility}
										onChange={(e) => setVisibility(e.target.value)}
										className="w-full rounded-md border px-3 py-2 text-sm"
									>
										<option value="private">Private</option>
										<option value="public">Public</option>
									</select>
								</div>
								<label className="flex items-center gap-2">
									<input
										type="checkbox"
										checked={createBoard}
										onChange={(e) => setCreateBoard(e.target.checked)}
									/>
									<span className="text-sm">Also create a board from this template</span>
								</label>
								<Button
									onClick={() =>
										onSave(title, description || null, categoryId, visibility, createBoard, tasks)
									}
									disabled={!title.trim() || tasks.length === 0 || isSaving}
									className="w-full"
								>
									{isSaving ? "Saving..." : "Save Template"}
								</Button>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
