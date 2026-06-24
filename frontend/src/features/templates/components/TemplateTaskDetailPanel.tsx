import { Clock, Plus, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { StreamedTemplateTask } from "../hooks/use-template-generation-stream";

interface TemplateTaskDetailPanelProps {
	task: StreamedTemplateTask;
	readOnly: boolean;
	onUpdate: (updated: StreamedTemplateTask) => void;
	onDelete: () => void;
	onClose: () => void;
}

const PRIORITY_OPTIONS = [
	{ value: "", labelKey: "detailPanel.priorityOptionNone" },
	{ value: "low", labelKey: "detailPanel.priorityOptionLow" },
	{ value: "medium", labelKey: "detailPanel.priorityOptionMedium" },
	{ value: "high", labelKey: "detailPanel.priorityOptionHigh" },
];

export function TemplateTaskDetailPanel({
	task,
	readOnly,
	onUpdate,
	onDelete,
	onClose,
}: TemplateTaskDetailPanelProps) {
	const { t } = useTranslation("templates");
	const [title, setTitle] = useState(task.title);
	const [description, setDescription] = useState(task.description);
	const [priority, setPriority] = useState(task.priority ?? "");
	const [estimatedMinutes, setEstimatedMinutes] = useState<string>(
		task.estimated_minutes != null ? String(task.estimated_minutes) : "",
	);
	const [subtasks, setSubtasks] = useState(task.subtasks.map((s) => s.title));
	const [newSubtaskTitle, setNewSubtaskTitle] = useState("");
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

	// Sync when task changes
	useEffect(() => {
		setTitle(task.title);
		setDescription(task.description);
		setPriority(task.priority ?? "");
		setEstimatedMinutes(task.estimated_minutes != null ? String(task.estimated_minutes) : "");
		setSubtasks(task.subtasks.map((s) => s.title));
		setShowDeleteConfirm(false);
	}, [task]);

	const emitUpdate = useCallback(
		(partial: Partial<StreamedTemplateTask>) => {
			onUpdate({ ...task, ...partial });
		},
		[task, onUpdate],
	);

	const handleTitleBlur = () => {
		if (title !== task.title && title.trim()) {
			emitUpdate({ title: title.trim() });
		}
	};

	const handleDescriptionBlur = () => {
		if (description !== task.description) {
			emitUpdate({ description });
		}
	};

	const handlePriorityChange = (value: string) => {
		setPriority(value);
		emitUpdate({ priority: value || null });
	};

	const handleEstimatedMinutesBlur = () => {
		const parsed = estimatedMinutes ? Number.parseInt(estimatedMinutes, 10) : null;
		const current = task.estimated_minutes;
		if (parsed !== current) {
			emitUpdate({ estimated_minutes: parsed && !Number.isNaN(parsed) ? parsed : null });
		}
	};

	const handleAddSubtask = () => {
		const trimmed = newSubtaskTitle.trim();
		if (!trimmed) return;
		const updated = [...subtasks, trimmed];
		setSubtasks(updated);
		setNewSubtaskTitle("");
		emitUpdate({ subtasks: updated.map((t) => ({ title: t })) });
	};

	const handleRemoveSubtask = (index: number) => {
		const updated = subtasks.filter((_, i) => i !== index);
		setSubtasks(updated);
		emitUpdate({ subtasks: updated.map((t) => ({ title: t })) });
	};

	const handleSubtaskChange = (index: number, value: string) => {
		const updated = [...subtasks];
		updated[index] = value;
		setSubtasks(updated);
	};

	const handleSubtaskBlur = (_index: number) => {
		emitUpdate({ subtasks: subtasks.map((t) => ({ title: t })) });
	};

	const handleDelete = () => {
		if (task.is_goal_node) {
			return; // Should not happen, button is hidden
		}
		onDelete();
	};

	return (
		<div className="flex h-full flex-col border-l bg-background">
			{/* Header */}
			<div className="flex items-center justify-between border-b px-4 py-3">
				<h3 className="text-sm font-semibold">
					{task.is_goal_node ? t("detailPanel.goalTask") : t("detailPanel.taskDetails")}
				</h3>
				<button type="button" onClick={onClose} className="rounded-md p-1 hover:bg-muted">
					<X className="h-4 w-4" />
				</button>
			</div>

			{/* Content */}
			<div className="flex-1 space-y-4 overflow-y-auto p-4">
				{/* Title */}
				<div>
					<Label className="text-xs text-muted-foreground">{t("detailPanel.title")}</Label>
					{readOnly ? (
						<p className="mt-1 text-sm font-medium">{task.title}</p>
					) : (
						<Input
							value={title}
							onChange={(e) => setTitle(e.target.value)}
							onBlur={handleTitleBlur}
							className="mt-1"
						/>
					)}
				</div>

				{/* Description */}
				<div>
					<Label className="text-xs text-muted-foreground">{t("detailPanel.description")}</Label>
					{readOnly ? (
						<p className="mt-1 text-sm text-muted-foreground whitespace-pre-wrap">
							{task.description || t("detailPanel.noDescription")}
						</p>
					) : (
						<textarea
							value={description}
							onChange={(e) => setDescription(e.target.value)}
							onBlur={handleDescriptionBlur}
							rows={3}
							className="mt-1 w-full rounded-md border bg-transparent px-3 py-2 text-sm"
						/>
					)}
				</div>

				{/* Priority */}
				<div>
					<Label className="text-xs text-muted-foreground">{t("detailPanel.priority")}</Label>
					{readOnly ? (
						<p className="mt-1 text-sm">
							{task.priority ? (
								<span className="rounded bg-muted px-1.5 py-0.5 text-xs capitalize">
									{task.priority}
								</span>
							) : (
								<span className="text-muted-foreground">{t("detailPanel.priorityNone")}</span>
							)}
						</p>
					) : (
						<select
							value={priority}
							onChange={(e) => handlePriorityChange(e.target.value)}
							className="mt-1 w-full rounded-md border bg-transparent px-3 py-2 text-sm"
						>
							{PRIORITY_OPTIONS.map((opt) => (
								<option key={opt.value} value={opt.value}>
									{t(opt.labelKey)}
								</option>
							))}
						</select>
					)}
				</div>

				{/* Estimated Minutes */}
				<div>
					<Label className="text-xs text-muted-foreground">
						<Clock className="mr-1 inline h-3 w-3" />
						{t("detailPanel.estimatedTime")}
					</Label>
					{readOnly ? (
						<p className="mt-1 text-sm">
							{task.estimated_minutes != null ? (
								t("detailPanel.minutesShort", { count: task.estimated_minutes })
							) : (
								<span className="text-muted-foreground">{t("detailPanel.notSet")}</span>
							)}
						</p>
					) : (
						<Input
							type="number"
							value={estimatedMinutes}
							onChange={(e) => setEstimatedMinutes(e.target.value)}
							onBlur={handleEstimatedMinutesBlur}
							placeholder={t("detailPanel.estimatedPlaceholder")}
							className="mt-1"
							min={0}
						/>
					)}
				</div>

				{/* Subtasks */}
				<div>
					<Label className="text-xs text-muted-foreground">
						{t("detailPanel.subtasks", { count: subtasks.length })}
					</Label>
					<div className="mt-1 space-y-1">
						{subtasks.map((st, i) => (
							// biome-ignore lint/suspicious/noArrayIndexKey: subtasks are plain strings without unique IDs
							<div key={`subtask-${i}`} className="flex items-center gap-1">
								{readOnly ? (
									<p className="text-sm">&bull; {st}</p>
								) : (
									<>
										<Input
											value={st}
											onChange={(e) => handleSubtaskChange(i, e.target.value)}
											onBlur={() => handleSubtaskBlur(i)}
											className="h-8 text-sm"
										/>
										<button
											type="button"
											onClick={() => handleRemoveSubtask(i)}
											className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
										>
											<X className="h-3 w-3" />
										</button>
									</>
								)}
							</div>
						))}
						{subtasks.length === 0 && readOnly && (
							<p className="text-sm text-muted-foreground">{t("detailPanel.noSubtasks")}</p>
						)}
					</div>
					{!readOnly && (
						<div className="mt-2 flex gap-1">
							<Input
								value={newSubtaskTitle}
								onChange={(e) => setNewSubtaskTitle(e.target.value)}
								onKeyDown={(e) => {
									if (e.key === "Enter") {
										e.preventDefault();
										handleAddSubtask();
									}
								}}
								placeholder={t("detailPanel.addSubtaskPlaceholder")}
								className="h-8 text-sm"
							/>
							<Button
								type="button"
								variant="ghost"
								size="sm"
								onClick={handleAddSubtask}
								className="h-8 px-2"
							>
								<Plus className="h-3 w-3" />
							</Button>
						</div>
					)}
				</div>
			</div>

			{/* Footer actions */}
			{!readOnly && !task.is_goal_node && (
				<div className="border-t p-4">
					{showDeleteConfirm ? (
						<div className="space-y-2">
							<p className="text-sm text-destructive">{t("detailPanel.deleteConfirm")}</p>
							<div className="flex gap-2">
								<Button variant="destructive" size="sm" onClick={handleDelete}>
									{t("detailPanel.delete")}
								</Button>
								<Button variant="outline" size="sm" onClick={() => setShowDeleteConfirm(false)}>
									{t("detailPanel.cancel")}
								</Button>
							</div>
						</div>
					) : (
						<Button
							variant="ghost"
							size="sm"
							className="text-destructive hover:text-destructive"
							onClick={() => setShowDeleteConfirm(true)}
						>
							<Trash2 className="mr-1 h-3 w-3" />
							{t("detailPanel.deleteTask")}
						</Button>
					)}
				</div>
			)}
			{!readOnly && task.is_goal_node && (
				<div className="border-t p-4">
					<p className="text-xs text-muted-foreground">{t("detailPanel.goalCannotDelete")}</p>
				</div>
			)}
		</div>
	);
}
