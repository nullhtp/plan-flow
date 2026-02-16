import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { ColumnResponse } from "@/features/board/types";

interface DeleteColumnDialogProps {
	column: ColumnResponse;
	otherColumns: ColumnResponse[];
	onConfirm: (targetColumnId: string | null) => void;
	onCancel: () => void;
}

export function DeleteColumnDialog({
	column,
	otherColumns,
	onConfirm,
	onCancel,
}: DeleteColumnDialogProps) {
	const [targetId, setTargetId] = useState<string>(otherColumns[0]?.id ?? "");
	const taskCount = column.tasks.length;

	return (
		// biome-ignore lint/a11y/noStaticElementInteractions: modal backdrop dismiss pattern
		<div
			className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
			onClick={onCancel}
			onKeyDown={(e) => e.key === "Escape" && onCancel()}
		>
			<div
				className="w-full max-w-md rounded-lg bg-card p-6 shadow-xl"
				onClick={(e) => e.stopPropagation()}
				onKeyDown={() => {}}
				role="dialog"
			>
				<h3 className="text-lg font-semibold">Delete "{column.title}"?</h3>
				{taskCount > 0 ? (
					<>
						<p className="mt-2 text-sm text-muted-foreground">
							This column has {taskCount} task{taskCount > 1 ? "s" : ""}. Move them to:
						</p>
						<select
							className="mt-3 w-full rounded-md border bg-background px-3 py-2 text-sm"
							value={targetId}
							onChange={(e) => setTargetId(e.target.value)}
						>
							{otherColumns.map((col) => (
								<option key={col.id} value={col.id}>
									{col.title} ({col.tasks.length} tasks)
								</option>
							))}
						</select>
					</>
				) : (
					<p className="mt-2 text-sm text-muted-foreground">
						This column is empty and will be permanently deleted.
					</p>
				)}
				<div className="mt-4 flex justify-end gap-2">
					<Button variant="outline" onClick={onCancel}>
						Cancel
					</Button>
					<Button variant="destructive" onClick={() => onConfirm(taskCount > 0 ? targetId : null)}>
						Delete
					</Button>
				</div>
			</div>
		</div>
	);
}
