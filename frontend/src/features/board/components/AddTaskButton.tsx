import { Plus } from "lucide-react";
import { type KeyboardEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface AddTaskButtonProps {
	onAdd: (title: string) => void;
	isPending?: boolean;
}

export function AddTaskButton({ onAdd, isPending }: AddTaskButtonProps) {
	const [isEditing, setIsEditing] = useState(false);
	const [title, setTitle] = useState("");

	const handleSubmit = () => {
		const trimmed = title.trim();
		if (trimmed) {
			onAdd(trimmed);
			setTitle("");
		}
	};

	const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
		if (e.key === "Enter") handleSubmit();
		if (e.key === "Escape") {
			setTitle("");
			setIsEditing(false);
		}
	};

	if (isEditing) {
		return (
			<div className="px-2 pb-2">
				<Input
					autoFocus
					placeholder="Task title..."
					value={title}
					onChange={(e) => setTitle(e.target.value)}
					onKeyDown={handleKeyDown}
					onBlur={() => {
						handleSubmit();
						setIsEditing(false);
					}}
					disabled={isPending}
					className="text-sm"
				/>
			</div>
		);
	}

	return (
		<Button
			variant="ghost"
			size="sm"
			className="mx-2 mb-2 w-[calc(100%-1rem)] justify-start text-muted-foreground"
			onClick={() => setIsEditing(true)}
		>
			<Plus className="mr-1 h-4 w-4" />
			Add task
		</Button>
	);
}
