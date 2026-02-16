import { Plus } from "lucide-react";
import { type KeyboardEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface AddColumnButtonProps {
	onAdd: (title: string) => void;
	isPending?: boolean;
}

export function AddColumnButton({ onAdd, isPending }: AddColumnButtonProps) {
	const [isEditing, setIsEditing] = useState(false);
	const [title, setTitle] = useState("");

	const handleSubmit = () => {
		const trimmed = title.trim();
		if (trimmed) {
			onAdd(trimmed);
			setTitle("");
			setIsEditing(false);
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
			<div className="flex w-72 shrink-0 flex-col gap-2 rounded-lg border border-dashed border-muted-foreground/30 bg-muted/30 p-3">
				<Input
					autoFocus
					placeholder="Column title..."
					value={title}
					onChange={(e) => setTitle(e.target.value)}
					onKeyDown={handleKeyDown}
					onBlur={handleSubmit}
					disabled={isPending}
				/>
			</div>
		);
	}

	return (
		<Button
			variant="ghost"
			className="flex h-auto w-72 shrink-0 flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-muted-foreground/30 p-6 text-muted-foreground hover:border-muted-foreground/50 hover:text-foreground"
			onClick={() => setIsEditing(true)}
		>
			<Plus className="h-5 w-5" />
			<span>Add Column</span>
		</Button>
	);
}
