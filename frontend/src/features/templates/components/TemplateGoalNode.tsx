import { Handle, Position } from "@xyflow/react";
import { Trophy } from "lucide-react";
import type { TemplateTaskNodeData } from "./TemplateDagView";

interface TemplateGoalNodeProps {
	data: TemplateTaskNodeData;
	selected?: boolean;
}

export function TemplateGoalNode({ data, selected }: TemplateGoalNodeProps) {
	const { task } = data;

	return (
		<div
			className={`relative rounded-3xl border-3 px-5 py-4 shadow-md cursor-pointer transition-all duration-200 ${
				selected
					? "border-primary bg-primary/5 ring-2 ring-primary/30"
					: "border-amber-400 bg-amber-50 dark:bg-amber-950/20 hover:border-amber-500"
			}`}
			style={{ width: 320 }}
		>
			{/* Visible target handle (dependencies flow into goal) */}
			<Handle
				type="target"
				position={Position.Top}
				className="!w-3 !h-3 !bg-amber-400 !border-2 !border-white dark:!border-gray-800 !rounded-full"
			/>

			<div className="flex items-start gap-3">
				<div className="mt-0.5 shrink-0">
					<Trophy className="h-6 w-6 text-amber-500" />
				</div>
				<div className="min-w-0 flex-1">
					<p className="text-base font-bold leading-tight">{task.title}</p>
					{task.description && (
						<p className="mt-1 text-sm text-muted-foreground line-clamp-2">{task.description}</p>
					)}
				</div>
			</div>

			{/* Goal node has no source handle — nothing depends on it */}
		</div>
	);
}
