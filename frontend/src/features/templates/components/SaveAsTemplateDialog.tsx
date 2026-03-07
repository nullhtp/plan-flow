import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCategoriesData } from "../hooks/use-categories";
import { useCreateTemplate } from "../hooks/use-template-mutations";

interface SaveAsTemplateDialogProps {
	boardId: string;
	boardTitle: string;
	taskCount: number;
	open: boolean;
	onClose: () => void;
}

export function SaveAsTemplateDialog({
	boardId,
	boardTitle,
	taskCount,
	open,
	onClose,
}: SaveAsTemplateDialogProps) {
	const [title, setTitle] = useState(boardTitle);
	const [description, setDescription] = useState("");
	const [categoryId, setCategoryId] = useState<string>("");
	const [visibility, setVisibility] = useState<"private" | "public">("private");
	const [success, setSuccess] = useState(false);

	const categories = useCategoriesData();
	const createTemplate = useCreateTemplate();

	if (!open) return null;

	if (success) {
		return (
			<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
				<div className="w-full max-w-md rounded-lg bg-background p-6 shadow-lg">
					<h3 className="mb-2 text-lg font-semibold">Template Created</h3>
					<p className="mb-4 text-sm text-muted-foreground">
						Your board has been saved as a template with {taskCount} tasks.
					</p>
					<div className="flex justify-end">
						<Button
							onClick={() => {
								setSuccess(false);
								onClose();
							}}
						>
							Done
						</Button>
					</div>
				</div>
			</div>
		);
	}

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		await createTemplate.mutateAsync({
			board_id: boardId,
			title,
			description: description || undefined,
			category_id: categoryId || undefined,
			visibility,
		});
		setSuccess(true);
	};

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
			<div className="w-full max-w-md rounded-lg bg-background p-6 shadow-lg">
				<h3 className="mb-4 text-lg font-semibold">Save as Template</h3>
				<form onSubmit={handleSubmit}>
					<div className="mb-3">
						<Label htmlFor="template-title">Title</Label>
						<Input
							id="template-title"
							value={title}
							onChange={(e) => setTitle(e.target.value)}
							maxLength={200}
							required
						/>
					</div>
					<div className="mb-3">
						<Label htmlFor="template-description">Description (optional)</Label>
						<Input
							id="template-description"
							value={description}
							onChange={(e) => setDescription(e.target.value)}
							maxLength={1000}
							placeholder="Brief description of this template"
						/>
					</div>
					<div className="mb-3">
						<Label htmlFor="template-category">Category (optional)</Label>
						<select
							id="template-category"
							value={categoryId}
							onChange={(e) => setCategoryId(e.target.value)}
							className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
						>
							<option value="">None</option>
							{categories.map((cat) => (
								<option key={cat.id} value={cat.id}>
									{cat.name}
								</option>
							))}
						</select>
					</div>
					<div className="mb-4">
						<Label>Visibility</Label>
						<div className="mt-1 flex gap-3">
							<label className="flex items-center gap-1.5 text-sm">
								<input
									type="radio"
									name="visibility"
									checked={visibility === "private"}
									onChange={() => setVisibility("private")}
								/>
								Private
							</label>
							<label className="flex items-center gap-1.5 text-sm">
								<input
									type="radio"
									name="visibility"
									checked={visibility === "public"}
									onChange={() => setVisibility("public")}
								/>
								Public
							</label>
						</div>
					</div>
					<div className="flex justify-end gap-2">
						<Button type="button" variant="outline" onClick={onClose}>
							Cancel
						</Button>
						<Button type="submit" disabled={createTemplate.isPending || !title}>
							{createTemplate.isPending ? "Saving..." : "Save Template"}
						</Button>
					</div>
				</form>
			</div>
		</div>
	);
}
