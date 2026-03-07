import { useNavigate } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCategoriesData } from "../hooks/use-categories";
import {
	useExtractContent,
	useGenerateTemplate,
	useSaveGeneratedTemplate,
} from "../hooks/use-template-generation";
import type { GenerateTemplateTaskResponse } from "../types";

type Step = "input" | "generating" | "preview";
type InputTab = "text" | "document" | "url";

const ACCEPTED_FILE_TYPES = ".pdf,.docx,.txt,.md";
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

interface GenerateTemplateDialogProps {
	open: boolean;
	onClose: () => void;
}

export function GenerateTemplateDialog({ open, onClose }: GenerateTemplateDialogProps) {
	const navigate = useNavigate();
	const categories = useCategoriesData();
	const extractContent = useExtractContent();
	const generateTemplate = useGenerateTemplate();
	const saveTemplate = useSaveGeneratedTemplate();
	const fileInputRef = useRef<HTMLInputElement>(null);

	// Input step state
	const [inputTab, setInputTab] = useState<InputTab>("text");
	const [textContent, setTextContent] = useState("");
	const [urlValue, setUrlValue] = useState("");
	const [selectedFile, setSelectedFile] = useState<File | null>(null);
	const [titleHint, setTitleHint] = useState("");
	const [error, setError] = useState<string | null>(null);

	// Preview step state
	const [tasks, setTasks] = useState<GenerateTemplateTaskResponse[]>([]);
	const [suggestedTitle, setSuggestedTitle] = useState("");
	const [suggestedDescription, setSuggestedDescription] = useState("");
	const [categoryId, setCategoryId] = useState("");
	const [visibility, setVisibility] = useState<"private" | "public">("private");
	const [step, setStep] = useState<Step>("input");

	if (!open) return null;

	const resetState = () => {
		setStep("input");
		setInputTab("text");
		setTextContent("");
		setUrlValue("");
		setSelectedFile(null);
		setTitleHint("");
		setError(null);
		setTasks([]);
		setSuggestedTitle("");
		setSuggestedDescription("");
		setCategoryId("");
		setVisibility("private");
	};

	const handleClose = () => {
		resetState();
		onClose();
	};

	const handleGenerate = async () => {
		setError(null);
		let content = "";

		try {
			if (inputTab === "text") {
				content = textContent;
			} else if (inputTab === "document" && selectedFile) {
				if (selectedFile.size > MAX_FILE_SIZE) {
					setError("File exceeds 10 MB limit");
					return;
				}
				const result = await extractContent.mutateAsync({
					file: selectedFile,
				});
				content = result.content;
			} else if (inputTab === "url" && urlValue) {
				const result = await extractContent.mutateAsync({ url: urlValue });
				content = result.content;
			} else {
				setError("Please provide content to generate from");
				return;
			}

			if (content.length < 20) {
				setError("Content is too short (minimum 20 characters)");
				return;
			}

			setStep("generating");

			const generated = await generateTemplate.mutateAsync({
				content,
				title: titleHint || undefined,
			});

			setTasks(generated.tasks);
			setSuggestedTitle(generated.suggested_title);
			setSuggestedDescription(generated.suggested_description);

			// Match suggested category slug to a category ID
			const matchedCat = categories.find((c) => c.slug === generated.suggested_category_slug);
			if (matchedCat) setCategoryId(matchedCat.id);

			setStep("preview");
		} catch (err: unknown) {
			setStep("input");
			const detail =
				err && typeof err === "object" && "data" in err
					? (err as { data?: { detail?: string } }).data?.detail
					: undefined;
			setError(detail || "Generation failed. Please try again.");
		}
	};

	const handleSave = async () => {
		try {
			const result = await saveTemplate.mutateAsync({
				title: suggestedTitle,
				description: suggestedDescription || undefined,
				category_id: categoryId || undefined,
				visibility,
				tasks: tasks.map((t) => ({
					id: t.id,
					title: t.title,
					description: t.description,
					is_goal_node: t.is_goal_node,
					depends_on: t.depends_on,
					subtasks: t.subtasks.map((s) => ({ title: s.title })),
				})),
			});
			handleClose();
			navigate({
				to: "/templates/$templateId",
				params: { templateId: result.id },
			});
		} catch {
			setError("Failed to save template. Please try again.");
		}
	};

	const updateTaskTitle = (taskId: string, newTitle: string) => {
		setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, title: newTitle } : t)));
	};

	const updateTaskDescription = (taskId: string, newDesc: string) => {
		setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, description: newDesc } : t)));
	};

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
			<div className="flex max-h-[90vh] w-full max-w-2xl flex-col rounded-lg bg-background shadow-lg">
				{/* Header */}
				<div className="flex items-center justify-between border-b px-6 py-4">
					<h3 className="text-lg font-semibold">
						{step === "input" && "Generate Template"}
						{step === "generating" && "Generating..."}
						{step === "preview" && "Preview & Edit"}
					</h3>
					<button
						type="button"
						onClick={handleClose}
						className="text-muted-foreground hover:text-foreground"
					>
						&times;
					</button>
				</div>

				{/* Body */}
				<div className="flex-1 overflow-y-auto p-6">
					{error && (
						<div className="mb-4 rounded-md bg-destructive/10 px-4 py-2 text-sm text-destructive">
							{error}
						</div>
					)}

					{/* Input Step */}
					{step === "input" && (
						<>
							<div className="mb-4">
								<Label htmlFor="title-hint">Title (optional)</Label>
								<Input
									id="title-hint"
									value={titleHint}
									onChange={(e) => setTitleHint(e.target.value)}
									placeholder="e.g., Wedding Planning Template"
									maxLength={200}
								/>
							</div>

							{/* Tabs */}
							<div className="mb-4 flex gap-1 rounded-md bg-muted p-1">
								{(["text", "document", "url"] as const).map((tab) => (
									<button
										key={tab}
										type="button"
										onClick={() => setInputTab(tab)}
										className={`flex-1 rounded-sm px-3 py-1.5 text-sm font-medium capitalize transition-colors ${
											inputTab === tab
												? "bg-background shadow-sm"
												: "text-muted-foreground hover:text-foreground"
										}`}
									>
										{tab}
									</button>
								))}
							</div>

							{/* Text Tab */}
							{inputTab === "text" && (
								<div>
									<Label htmlFor="text-content">Paste or type your content</Label>
									<textarea
										id="text-content"
										value={textContent}
										onChange={(e) => setTextContent(e.target.value)}
										placeholder="e.g., Steps to plan a wedding: book venue, choose catering, send invitations..."
										className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm min-h-[200px] resize-y"
										maxLength={50000}
									/>
									<p className="mt-1 text-xs text-muted-foreground">
										{textContent.length.toLocaleString()} / 50,000 characters
									</p>
								</div>
							)}

							{/* Document Tab */}
							{inputTab === "document" && (
								<div>
									<Label>Upload a document</Label>
									<button
										type="button"
										className="mt-1 flex w-full flex-col items-center justify-center rounded-md border-2 border-dashed border-input p-8 cursor-pointer hover:border-primary/50 bg-transparent"
										onClick={() => fileInputRef.current?.click()}
									>
										<input
											ref={fileInputRef}
											type="file"
											accept={ACCEPTED_FILE_TYPES}
											className="hidden"
											onChange={(e) => {
												const file = e.target.files?.[0] ?? null;
												setSelectedFile(file);
											}}
										/>
										{selectedFile ? (
											<p className="text-sm">{selectedFile.name}</p>
										) : (
											<>
												<p className="text-sm text-muted-foreground">Click to select a file</p>
												<p className="mt-1 text-xs text-muted-foreground">
													PDF, DOCX, TXT, or Markdown (max 10 MB)
												</p>
											</>
										)}
									</button>
								</div>
							)}

							{/* URL Tab */}
							{inputTab === "url" && (
								<div>
									<Label htmlFor="url-input">Enter a URL</Label>
									<Input
										id="url-input"
										value={urlValue}
										onChange={(e) => setUrlValue(e.target.value)}
										placeholder="https://example.com/project-guide"
										type="url"
									/>
									<p className="mt-1 text-xs text-muted-foreground">
										Content will be extracted from the webpage
									</p>
								</div>
							)}
						</>
					)}

					{/* Generating Step */}
					{step === "generating" && (
						<div className="flex flex-col items-center justify-center py-12">
							<div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
							<p className="text-muted-foreground">AI is generating your template...</p>
						</div>
					)}

					{/* Preview Step */}
					{step === "preview" && (
						<>
							{/* Metadata fields */}
							<div className="mb-4 grid gap-3 sm:grid-cols-2">
								<div>
									<Label htmlFor="gen-title">Title</Label>
									<Input
										id="gen-title"
										value={suggestedTitle}
										onChange={(e) => setSuggestedTitle(e.target.value)}
										maxLength={200}
										required
									/>
								</div>
								<div>
									<Label htmlFor="gen-category">Category</Label>
									<select
										id="gen-category"
										value={categoryId}
										onChange={(e) => setCategoryId(e.target.value)}
										className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
									>
										<option value="">None</option>
										{categories.map((cat) => (
											<option key={cat.id} value={cat.id}>
												{cat.name}
											</option>
										))}
									</select>
								</div>
							</div>
							<div className="mb-4">
								<Label htmlFor="gen-description">Description</Label>
								<Input
									id="gen-description"
									value={suggestedDescription}
									onChange={(e) => setSuggestedDescription(e.target.value)}
									maxLength={1000}
								/>
							</div>
							<div className="mb-4">
								<Label>Visibility</Label>
								<div className="mt-1 flex gap-3">
									<label className="flex items-center gap-1.5 text-sm">
										<input
											type="radio"
											name="gen-visibility"
											checked={visibility === "private"}
											onChange={() => setVisibility("private")}
										/>
										Private
									</label>
									<label className="flex items-center gap-1.5 text-sm">
										<input
											type="radio"
											name="gen-visibility"
											checked={visibility === "public"}
											onChange={() => setVisibility("public")}
										/>
										Public
									</label>
								</div>
							</div>

							{/* Task list */}
							<h4 className="mb-2 font-medium">Tasks ({tasks.length})</h4>
							<div className="space-y-2">
								{tasks
									.filter((t) => !t.is_goal_node)
									.map((task) => (
										<div key={task.id} className="rounded-md border p-3">
											<Input
												value={task.title}
												onChange={(e) => updateTaskTitle(task.id, e.target.value)}
												className="mb-1 font-medium"
											/>
											<Input
												value={task.description}
												onChange={(e) => updateTaskDescription(task.id, e.target.value)}
												className="text-sm text-muted-foreground"
												placeholder="Description"
											/>
											{task.subtasks.length > 0 && (
												<div className="mt-2 space-y-0.5 pl-3">
													{task.subtasks.map((st) => (
														<p
															key={`${task.id}-st-${st.title}`}
															className="text-xs text-muted-foreground"
														>
															&bull; {st.title}
														</p>
													))}
												</div>
											)}
											{task.depends_on.length > 0 && (
												<p className="mt-1 text-xs text-muted-foreground">
													Depends on:{" "}
													{task.depends_on
														.map((depId) => tasks.find((t) => t.id === depId)?.title ?? depId)
														.join(", ")}
												</p>
											)}
										</div>
									))}

								{/* Goal task */}
								{tasks
									.filter((t) => t.is_goal_node)
									.map((task) => (
										<div key={task.id} className="rounded-md border-2 border-primary/30 p-3">
											<div className="mb-1 text-xs font-medium uppercase text-primary">Goal</div>
											<Input
												value={task.title}
												onChange={(e) => updateTaskTitle(task.id, e.target.value)}
												className="font-medium"
											/>
										</div>
									))}
							</div>
						</>
					)}
				</div>

				{/* Footer */}
				<div className="flex justify-end gap-2 border-t px-6 py-4">
					<Button variant="outline" onClick={handleClose}>
						Cancel
					</Button>
					{step === "input" && (
						<Button
							onClick={handleGenerate}
							disabled={
								extractContent.isPending ||
								generateTemplate.isPending ||
								(inputTab === "text" && textContent.length < 20) ||
								(inputTab === "document" && !selectedFile) ||
								(inputTab === "url" && !urlValue)
							}
						>
							{extractContent.isPending ? "Extracting..." : "Generate"}
						</Button>
					)}
					{step === "preview" && (
						<>
							<Button
								variant="outline"
								onClick={() => {
									setStep("input");
									setError(null);
								}}
							>
								Back
							</Button>
							<Button onClick={handleSave} disabled={saveTemplate.isPending || !suggestedTitle}>
								{saveTemplate.isPending ? "Saving..." : "Save Template"}
							</Button>
						</>
					)}
				</div>
			</div>
		</div>
	);
}
