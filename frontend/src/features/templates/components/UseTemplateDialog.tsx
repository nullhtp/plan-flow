import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateBoardFromTemplate } from "../hooks/use-template-mutations";

interface UseTemplateDialogProps {
	templateId: string;
	templateTitle: string;
	open: boolean;
	onClose: () => void;
}

export function UseTemplateDialog({
	templateId,
	templateTitle,
	open,
	onClose,
}: UseTemplateDialogProps) {
	const [title, setTitle] = useState(templateTitle);
	const createBoard = useCreateBoardFromTemplate(templateId);
	const navigate = useNavigate();

	if (!open) return null;

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		const result = await createBoard.mutateAsync({ title: title || undefined });
		onClose();
		navigate({ to: "/boards/$boardId", params: { boardId: result.board_id } });
	};

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
			<div className="w-full max-w-md rounded-lg bg-background p-6 shadow-lg">
				<h3 className="mb-4 text-lg font-semibold">Use Template</h3>
				<p className="mb-4 text-sm text-muted-foreground">
					This will create a new board from the template. You can optionally customize the title.
				</p>
				<form onSubmit={handleSubmit}>
					<div className="mb-4">
						<Label htmlFor="board-title">Board Title</Label>
						<Input
							id="board-title"
							value={title}
							onChange={(e) => setTitle(e.target.value)}
							placeholder={templateTitle}
						/>
					</div>
					<div className="flex justify-end gap-2">
						<Button type="button" variant="outline" onClick={onClose}>
							Cancel
						</Button>
						<Button type="submit" disabled={createBoard.isPending}>
							{createBoard.isPending ? "Creating..." : "Create Board"}
						</Button>
					</div>
				</form>
			</div>
		</div>
	);
}
