import { createRoute, useNavigate } from "@tanstack/react-router";
import { Plus, Save } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/features/auth/hooks/use-auth";
import { TemplateDagView } from "@/features/templates/components/TemplateDagView";
import { TemplateTaskDetailPanel } from "@/features/templates/components/TemplateTaskDetailPanel";
import { UseTemplateDialog } from "@/features/templates/components/UseTemplateDialog";
import { useCategoriesData } from "@/features/templates/hooks/use-categories";
import { useTemplateDetail } from "@/features/templates/hooks/use-template-detail";
import type { StreamedTemplateTask } from "@/features/templates/hooks/use-template-generation-stream";
import {
	useUpdateTemplate,
	useUpdateTemplateStructure,
} from "@/features/templates/hooks/use-template-mutations";
import type { TemplateTaskResponse } from "@/features/templates/types";
import { useSimpleMode } from "@/shared/hooks/use-simple-mode";
import { authenticatedRoute } from "./_authenticated";

export const templateDetailRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/templates/$templateId",
	component: TemplateDetailPage,
});

// ── Helpers: convert between TemplateTaskResponse and StreamedTemplateTask ──

function toStreamedTask(
	task: TemplateTaskResponse,
	edges: Array<{ source: string; target: string }>,
): StreamedTemplateTask {
	return {
		id: task.id,
		title: task.title,
		description: task.description,
		is_goal_node: task.is_goal_node,
		priority: task.priority ?? null,
		estimated_minutes: task.estimated_minutes ?? null,
		subtasks: task.subtasks.map((s) => ({ title: s.title })),
		depends_on: edges.filter((e) => e.target === task.id).map((e) => e.source),
	};
}

// ── Dirty state comparison ──

interface GraphSnapshot {
	tasks: StreamedTemplateTask[];
	edges: Array<{ source: string; target: string }>;
}

function serializeSnapshot(snapshot: GraphSnapshot): string {
	const sortedTasks = [...snapshot.tasks]
		.sort((a, b) => a.id.localeCompare(b.id))
		.map((t) => ({
			id: t.id,
			title: t.title,
			description: t.description,
			is_goal_node: t.is_goal_node,
			priority: t.priority,
			estimated_minutes: t.estimated_minutes,
			subtasks: t.subtasks.map((s) => s.title),
			depends_on: [...t.depends_on].sort(),
		}));
	const sortedEdges = [...snapshot.edges].sort((a, b) =>
		a.source === b.source ? a.target.localeCompare(b.target) : a.source.localeCompare(b.source),
	);
	return JSON.stringify({ tasks: sortedTasks, edges: sortedEdges });
}

// ── Component ──

function TemplateDetailPage() {
	const { t } = useTranslation("templates");
	const { templateId } = templateDetailRoute.useParams();
	const navigate = useNavigate();
	const { user } = useAuth();
	const { data: template, isLoading, dataUpdatedAt } = useTemplateDetail(templateId);
	const updateStructure = useUpdateTemplateStructure(templateId);
	const updateTemplate = useUpdateTemplate(templateId);
	const categories = useCategoriesData();

	// Simple mode hides template viewing/editing — only creating a board from a
	// template is allowed, so redirect the editor route back to the gallery.
	const { isSimpleMode, isLoading: simpleModeLoading } = useSimpleMode();
	useEffect(() => {
		if (!simpleModeLoading && isSimpleMode) {
			navigate({ to: "/", search: { tab: "templates" }, replace: true });
		}
	}, [simpleModeLoading, isSimpleMode, navigate]);

	const [showUseDialog, setShowUseDialog] = useState(false);
	const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

	// ── Metadata editing state ──
	const [editTitle, setEditTitle] = useState("");
	const [editDescription, setEditDescription] = useState("");
	const [editCategoryId, setEditCategoryId] = useState<string | null>(null);

	// ── Editable graph state ──
	const [tasks, setTasks] = useState<StreamedTemplateTask[]>([]);
	const [edges, setEdges] = useState<Array<{ source: string; target: string }>>([]);
	const savedSnapshotRef = useRef<string>("");

	// Initialize/reset graph state when template data loads.
	// Depend on dataUpdatedAt (stable timestamp from React Query) instead of the
	// template object reference to avoid infinite re-render loops.
	// biome-ignore lint/correctness/useExhaustiveDependencies: intentionally using dataUpdatedAt as proxy for template data changes
	useEffect(() => {
		if (!template) return;
		const streamedTasks = template.tasks.map((t) => toStreamedTask(t, template.edges));
		const templateEdges = [...template.edges];
		setTasks(streamedTasks);
		setEdges(templateEdges);
		savedSnapshotRef.current = serializeSnapshot({
			tasks: streamedTasks,
			edges: templateEdges,
		});
		setEditTitle(template.title);
		setEditDescription(template.description ?? "");
		setEditCategoryId(template.category?.id ?? null);
	}, [dataUpdatedAt]);

	const isOwner = !!(user && template && template.creator.id === user.id);

	// Dirty state
	const isDirty = useMemo(() => {
		if (!template || tasks.length === 0) return false;
		const current = serializeSnapshot({ tasks, edges });
		return current !== savedSnapshotRef.current;
	}, [template, tasks, edges]);

	// Warn on navigation away with unsaved changes
	useEffect(() => {
		if (!isDirty) return;
		const handler = (e: BeforeUnloadEvent) => {
			e.preventDefault();
		};
		window.addEventListener("beforeunload", handler);
		return () => window.removeEventListener("beforeunload", handler);
	}, [isDirty]);

	// ── Callbacks ──

	const handleEdgesChange = useCallback((newEdges: Array<{ source: string; target: string }>) => {
		setEdges(newEdges);
		// Sync depends_on in tasks
		setTasks((prev) =>
			prev.map((t) => ({
				...t,
				depends_on: newEdges.filter((e) => e.target === t.id).map((e) => e.source),
			})),
		);
	}, []);

	const handleTaskUpdate = useCallback((updated: StreamedTemplateTask) => {
		setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
	}, []);

	const handleTaskDelete = useCallback(
		(taskId: string) => {
			setTasks((prev) => prev.filter((t) => t.id !== taskId));
			setEdges((prev) => prev.filter((e) => e.source !== taskId && e.target !== taskId));
			if (selectedTaskId === taskId) {
				setSelectedTaskId(null);
			}
		},
		[selectedTaskId],
	);

	const handleMetadataSave = useCallback(
		(field: "title" | "description" | "category_id" | "visibility", value: string | null) => {
			updateTemplate.mutate({ [field]: value });
		},
		[updateTemplate],
	);

	const handleAddTask = useCallback(() => {
		const newTask: StreamedTemplateTask = {
			id: crypto.randomUUID(),
			title: t("detail.newTask"),
			description: "",
			is_goal_node: false,
			priority: null,
			estimated_minutes: null,
			subtasks: [],
			depends_on: [],
		};
		setTasks((prev) => [...prev, newTask]);
		setSelectedTaskId(newTask.id);
	}, [t]);

	const handleSave = useCallback(() => {
		const payload = {
			tasks: tasks.map((t) => ({
				id: t.id,
				title: t.title,
				description: t.description,
				is_goal_node: t.is_goal_node,
				depends_on: t.depends_on,
				subtasks: t.subtasks,
				priority: t.priority,
				estimated_minutes: t.estimated_minutes,
			})),
		};
		updateStructure.mutate(payload, {
			onSuccess: () => {
				savedSnapshotRef.current = serializeSnapshot({ tasks, edges });
			},
		});
	}, [tasks, edges, updateStructure]);

	const selectedTask = useMemo(
		() => (selectedTaskId ? (tasks.find((t) => t.id === selectedTaskId) ?? null) : null),
		[selectedTaskId, tasks],
	);

	// ── Render ──

	// While Simple mode resolves (or if it's on), don't flash the editor — the
	// effect above redirects Simple-mode users to the gallery.
	if (simpleModeLoading || isSimpleMode) {
		return (
			<div className="flex min-h-screen items-center justify-center">
				<p className="text-muted-foreground">{t("detail.loadingSimpleMode")}</p>
			</div>
		);
	}

	if (isLoading) {
		return (
			<div className="flex min-h-screen items-center justify-center">
				<p className="text-muted-foreground">{t("detail.loadingTemplate")}</p>
			</div>
		);
	}

	if (!template) {
		return (
			<div className="flex min-h-screen items-center justify-center">
				<p className="text-muted-foreground">{t("detail.notFound")}</p>
			</div>
		);
	}

	return (
		<div className="flex h-screen flex-col">
			{/* Header */}
			<header className="flex items-center justify-between border-b px-6 py-4">
				<div className="min-w-0 flex-1">
					<button
						type="button"
						className="mb-1 text-sm text-muted-foreground hover:underline"
						onClick={() => navigate({ to: "/", search: { tab: "templates" } })}
					>
						&larr; {t("detail.backToTemplates")}
					</button>

					{/* Title */}
					{isOwner ? (
						<Input
							value={editTitle}
							onChange={(e) => setEditTitle(e.target.value)}
							onBlur={() => {
								const trimmed = editTitle.trim();
								if (trimmed && trimmed !== template.title) {
									handleMetadataSave("title", trimmed);
								}
							}}
							className="mt-1 h-auto border-none p-0 text-2xl font-bold shadow-none focus-visible:ring-0"
						/>
					) : (
						<h1 className="truncate text-2xl font-bold">{template.title}</h1>
					)}

					{/* Metadata row */}
					<div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
						{isOwner ? (
							<select
								value={editCategoryId ?? ""}
								onChange={(e) => {
									const val = e.target.value || null;
									setEditCategoryId(val);
									handleMetadataSave("category_id", val);
								}}
								className="rounded-full bg-muted px-3 py-1 text-sm"
							>
								<option value="">{t("detail.noCategory")}</option>
								{categories.map((cat) => (
									<option key={cat.id} value={cat.id}>
										{cat.name}
									</option>
								))}
							</select>
						) : (
							template.category && (
								<span className="rounded-full bg-muted px-3 py-1">{template.category.name}</span>
							)
						)}
						<span>{t("detail.taskCount", { count: template.task_count })}</span>
						<span>{t("detail.byCreator", { email: template.creator.email })}</span>
						{isOwner ? (
							<select
								value={template.visibility}
								onChange={(e) => {
									handleMetadataSave("visibility", e.target.value);
								}}
								className="rounded-full bg-muted px-3 py-1 text-sm capitalize"
							>
								<option value="private">{t("detail.private")}</option>
								<option value="public">{t("detail.public")}</option>
							</select>
						) : (
							<span className="capitalize">{template.visibility}</span>
						)}
					</div>

					{/* Description */}
					{isOwner ? (
						<textarea
							value={editDescription}
							onChange={(e) => setEditDescription(e.target.value)}
							onBlur={() => {
								if (editDescription !== (template.description ?? "")) {
									handleMetadataSave("description", editDescription || null);
								}
							}}
							placeholder={t("detail.descriptionPlaceholder")}
							rows={1}
							className="mt-2 w-full max-w-2xl resize-none border-none bg-transparent p-0 text-sm text-muted-foreground shadow-none outline-none focus:ring-0"
						/>
					) : (
						template.description && (
							<p className="mt-2 max-w-2xl text-sm text-muted-foreground">{template.description}</p>
						)
					)}
				</div>
				<div className="flex items-center gap-2">
					{isOwner && (
						<Button onClick={handleAddTask} variant="outline" size="sm">
							<Plus className="mr-1.5 h-4 w-4" />
							{t("detail.addTask")}
						</Button>
					)}
					{isOwner && isDirty && (
						<Button onClick={handleSave} disabled={updateStructure.isPending} variant="default">
							<Save className="mr-1.5 h-4 w-4" />
							{updateStructure.isPending ? t("detail.saving") : t("detail.saveChanges")}
						</Button>
					)}
					<Button onClick={() => setShowUseDialog(true)} variant="outline">
						{t("detail.useTemplate")}
					</Button>
				</div>
			</header>

			{/* Save error */}
			{updateStructure.isError && (
				<div className="border-b border-destructive/30 bg-destructive/10 px-6 py-2 text-sm text-destructive">
					{t("detail.saveFailed")}{" "}
					{updateStructure.error instanceof Error
						? updateStructure.error.message
						: t("detail.unknownError")}
				</div>
			)}

			{/* Main area: DAG + optional panel */}
			<div className="flex flex-1 overflow-hidden">
				{/* DAG view */}
				<div className="flex-1">
					{tasks.length > 0 ? (
						<TemplateDagView
							tasks={tasks}
							edges={edges}
							selectedTaskId={selectedTaskId}
							onSelectTask={setSelectedTaskId}
							onEdgesChange={handleEdgesChange}
							readOnly={!isOwner}
						/>
					) : (
						<div className="flex h-full items-center justify-center">
							<p className="text-muted-foreground">{t("detail.noTasks")}</p>
						</div>
					)}
				</div>

				{/* Task detail panel */}
				{selectedTask && (
					<div className="w-80 shrink-0">
						<TemplateTaskDetailPanel
							task={selectedTask}
							readOnly={!isOwner}
							onUpdate={handleTaskUpdate}
							onDelete={() => handleTaskDelete(selectedTask.id)}
							onClose={() => setSelectedTaskId(null)}
						/>
					</div>
				)}
			</div>

			<UseTemplateDialog
				templateId={template.id}
				templateTitle={template.title}
				open={showUseDialog}
				onClose={() => setShowUseDialog(false)}
			/>
		</div>
	);
}
