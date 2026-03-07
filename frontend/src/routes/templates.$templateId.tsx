import { createRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { UseTemplateDialog } from "@/features/templates/components/UseTemplateDialog";
import { useTemplateDetail } from "@/features/templates/hooks/use-template-detail";
import { authenticatedRoute } from "./_authenticated";

export const templateDetailRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/templates/$templateId",
	component: TemplateDetailPage,
});

function TemplateDetailPage() {
	const { templateId } = templateDetailRoute.useParams();
	const navigate = useNavigate();
	const { data: template, isLoading } = useTemplateDetail(templateId);
	const [showUseDialog, setShowUseDialog] = useState(false);

	if (isLoading) {
		return (
			<div className="flex min-h-screen items-center justify-center">
				<p className="text-muted-foreground">Loading template...</p>
			</div>
		);
	}

	if (!template) {
		return (
			<div className="flex min-h-screen items-center justify-center">
				<p className="text-muted-foreground">Template not found.</p>
			</div>
		);
	}

	const goalTask = template.tasks.find((t) => t.is_goal_node);
	const regularTasks = template.tasks.filter((t) => !t.is_goal_node);

	return (
		<div className="flex min-h-screen flex-col">
			<header className="flex items-center justify-between border-b px-6 py-4">
				<div>
					<button
						type="button"
						className="mb-1 text-sm text-muted-foreground hover:underline"
						onClick={() => navigate({ to: "/templates" })}
					>
						&larr; Back to Templates
					</button>
					<h1 className="text-2xl font-bold">{template.title}</h1>
				</div>
				<Button onClick={() => setShowUseDialog(true)}>Use Template</Button>
			</header>

			<main className="flex-1 p-6">
				<div className="mx-auto max-w-3xl">
					{/* Metadata */}
					<div className="mb-6 flex flex-wrap gap-3 text-sm text-muted-foreground">
						{template.category && (
							<span className="rounded-full bg-muted px-3 py-1">{template.category.name}</span>
						)}
						<span>{template.task_count} tasks</span>
						<span>by {template.creator.email}</span>
						<span className="capitalize">{template.visibility}</span>
					</div>

					{template.description && (
						<p className="mb-6 text-muted-foreground">{template.description}</p>
					)}

					{/* Task list */}
					<h2 className="mb-3 text-lg font-semibold">Tasks</h2>
					<div className="space-y-3">
						{regularTasks.map((task) => {
							const deps = template.edges
								.filter((e) => e.target === task.id)
								.map((e) => {
									const depTask = template.tasks.find((t) => t.id === e.source);
									return depTask?.title ?? "Unknown";
								});

							return (
								<div key={task.id} className="rounded-lg border p-4">
									<div className="flex items-start justify-between">
										<div>
											<h3 className="font-medium">{task.title}</h3>
											{task.description && (
												<p className="mt-1 text-sm text-muted-foreground">{task.description}</p>
											)}
										</div>
										<div className="flex gap-2 text-xs text-muted-foreground">
											{task.priority && (
												<span className="rounded bg-muted px-1.5 py-0.5">{task.priority}</span>
											)}
											{task.estimated_minutes && <span>{task.estimated_minutes}min</span>}
										</div>
									</div>
									{deps.length > 0 && (
										<p className="mt-2 text-xs text-muted-foreground">
											Depends on: {deps.join(", ")}
										</p>
									)}
									{task.subtasks.length > 0 && (
										<div className="mt-2 space-y-1">
											{task.subtasks.map((st) => (
												<div key={st.id} className="text-sm text-muted-foreground">
													&bull; {st.title}
												</div>
											))}
										</div>
									)}
								</div>
							);
						})}

						{/* Goal task */}
						{goalTask && (
							<div className="rounded-lg border-2 border-primary/30 p-4">
								<div className="mb-1 text-xs font-medium uppercase text-primary">Goal</div>
								<h3 className="font-medium">{goalTask.title}</h3>
								{goalTask.description && (
									<p className="mt-1 text-sm text-muted-foreground">{goalTask.description}</p>
								)}
							</div>
						)}
					</div>
				</div>
			</main>

			<UseTemplateDialog
				templateId={template.id}
				templateTitle={template.title}
				open={showUseDialog}
				onClose={() => setShowUseDialog(false)}
			/>
		</div>
	);
}
