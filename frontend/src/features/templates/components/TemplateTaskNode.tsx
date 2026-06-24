import { Handle, Position } from "@xyflow/react";
import { Clock } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { TemplateTaskNodeData } from "./TemplateDagView";

const priorityDots: Record<string, string> = {
	high: "bg-rose-400",
	medium: "bg-amber-400",
	low: "bg-sky-400",
};

interface TemplateTaskNodeProps {
	data: TemplateTaskNodeData;
	selected?: boolean;
}

export function TemplateTaskNode({ data, selected }: TemplateTaskNodeProps) {
	const { t } = useTranslation("templates");
	const { task } = data;
	const subtaskCount = task.subtasks?.length ?? 0;

	return (
		<div
			className={`relative rounded-3xl border-2 px-4 py-3 shadow-md cursor-pointer transition-all duration-200 ${
				selected
					? "border-primary bg-primary/5 ring-2 ring-primary/30"
					: "border-gray-300 bg-gray-50/80 dark:bg-gray-900/20 hover:border-gray-400"
			}`}
			style={{ width: 280 }}
		>
			{/* Visible handles for connection */}
			<Handle
				type="target"
				position={Position.Top}
				className="!w-3 !h-3 !bg-indigo-400 !border-2 !border-white dark:!border-gray-800 !rounded-full"
			/>

			<div className="min-w-0">
				<p className="text-sm font-semibold leading-snug tracking-tight">{task.title}</p>
				{task.description && (
					<p className="mt-1 text-xs text-muted-foreground line-clamp-2">{task.description}</p>
				)}
				<div className="mt-2 flex flex-wrap items-center gap-2.5">
					{task.priority && (
						<span
							className={`inline-block h-2 w-2 rounded-full ${priorityDots[task.priority] ?? "bg-gray-400"}`}
							title={task.priority}
						/>
					)}
					{task.estimated_minutes && (
						<span className="flex items-center gap-1 text-xs text-muted-foreground">
							<Clock className="h-3 w-3" />
							{task.estimated_minutes}m
						</span>
					)}
					{subtaskCount > 0 && (
						<span className="text-xs text-muted-foreground">
							{t("taskNode.subtaskCount", { count: subtaskCount })}
						</span>
					)}
				</div>
			</div>

			<Handle
				type="source"
				position={Position.Bottom}
				className="!w-3 !h-3 !bg-indigo-400 !border-2 !border-white dark:!border-gray-800 !rounded-full"
			/>
		</div>
	);
}
