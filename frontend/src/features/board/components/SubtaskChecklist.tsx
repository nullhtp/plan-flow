import { Plus, Trash2 } from "lucide-react";
import { type KeyboardEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { SubtaskResponse } from "@/features/board/types";

interface SubtaskChecklistProps {
	subtasks: SubtaskResponse[];
	onToggle: (subtaskId: string, completed: boolean) => void;
	onAdd: (title: string) => void;
	onDelete: (subtaskId: string) => void;
}

export function SubtaskChecklist({ subtasks, onToggle, onAdd, onDelete }: SubtaskChecklistProps) {
	const [newTitle, setNewTitle] = useState("");

	const handleAdd = () => {
		const trimmed = newTitle.trim();
		if (trimmed) {
			onAdd(trimmed);
			setNewTitle("");
		}
	};

	const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
		if (e.key === "Enter") handleAdd();
	};

	return (
		<div className="space-y-2">
			<h4 className="text-sm font-medium">Subtasks</h4>
			<div className="space-y-1">
				{subtasks.map((subtask) => (
					<div
						key={subtask.id}
						className="group flex items-center gap-2 rounded px-1 py-0.5 hover:bg-muted"
					>
						<input
							type="checkbox"
							checked={subtask.completed}
							onChange={() => onToggle(subtask.id, !subtask.completed)}
							className="h-4 w-4 rounded border-muted-foreground/50"
						/>
						<span
							className={`flex-1 text-sm ${subtask.completed ? "text-muted-foreground line-through" : ""}`}
						>
							{subtask.title}
						</span>
						<Button
							variant="ghost"
							size="sm"
							className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
							onClick={() => onDelete(subtask.id)}
						>
							<Trash2 className="h-3 w-3" />
						</Button>
					</div>
				))}
			</div>
			<div className="flex items-center gap-2">
				<Input
					placeholder="Add subtask..."
					value={newTitle}
					onChange={(e) => setNewTitle(e.target.value)}
					onKeyDown={handleKeyDown}
					className="h-8 text-sm"
				/>
				<Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={handleAdd}>
					<Plus className="h-4 w-4" />
				</Button>
			</div>
		</div>
	);
}
