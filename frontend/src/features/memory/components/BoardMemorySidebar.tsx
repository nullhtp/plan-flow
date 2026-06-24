import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { Brain, ExternalLink, Pencil, Trash2, X } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
	getGetBoardMemoriesApiBoardsBoardIdMemoriesGetQueryKey,
	getGetMemoriesApiMemoriesGetQueryKey,
	getGetStatsApiMemoriesStatsGetQueryKey,
	useDeleteMemoryByIdApiMemoriesMemoryIdDelete,
	useGetBoardMemoriesApiBoardsBoardIdMemoriesGet,
	usePatchMemoryApiMemoriesMemoryIdPatch,
} from "@/api/generated/memories/memories";
import type { MemoryResponse } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const CATEGORY_COLORS: Record<string, string> = {
	preference: "bg-blue-100 text-blue-700",
	fact: "bg-green-100 text-green-700",
	pattern: "bg-purple-100 text-purple-700",
	context: "bg-orange-100 text-orange-700",
};

interface BoardMemorySidebarProps {
	boardId: string;
	onClose: () => void;
}

export function BoardMemorySidebar({ boardId, onClose }: BoardMemorySidebarProps) {
	const { t } = useTranslation("memory");
	const navigate = useNavigate();
	const queryClient = useQueryClient();

	const memoriesQuery = useGetBoardMemoriesApiBoardsBoardIdMemoriesGet(boardId, { limit: 20 });
	const patchMemory = usePatchMemoryApiMemoriesMemoryIdPatch();
	const deleteMemory = useDeleteMemoryByIdApiMemoriesMemoryIdDelete();

	const [editingId, setEditingId] = useState<string | null>(null);
	const [editContent, setEditContent] = useState("");

	const memories = (memoriesQuery.data?.data ?? []) as MemoryResponse[];

	const invalidateMemories = () => {
		queryClient.invalidateQueries({
			queryKey: getGetBoardMemoriesApiBoardsBoardIdMemoriesGetQueryKey(boardId),
		});
		queryClient.invalidateQueries({ queryKey: getGetMemoriesApiMemoriesGetQueryKey() });
		queryClient.invalidateQueries({ queryKey: getGetStatsApiMemoriesStatsGetQueryKey() });
	};

	const handleEdit = (memory: MemoryResponse) => {
		setEditingId(memory.id);
		setEditContent(memory.content);
	};

	const handleSaveEdit = () => {
		if (!editingId) return;
		patchMemory.mutate(
			{ memoryId: editingId, data: { content: editContent } },
			{
				onSuccess: () => {
					setEditingId(null);
					invalidateMemories();
				},
			},
		);
	};

	const handleDelete = (memoryId: string) => {
		if (!confirm(t("deleteConfirm"))) return;
		deleteMemory.mutate({ memoryId }, { onSuccess: invalidateMemories });
	};

	return (
		<div className="fixed inset-y-0 right-0 z-40 flex w-full max-w-sm flex-col border-l bg-background shadow-xl">
			{/* Header */}
			<div className="flex items-center justify-between border-b p-4">
				<div className="flex items-center gap-2">
					<Brain className="h-4 w-4" />
					<h2 className="text-sm font-semibold">{t("boardMemories")}</h2>
					{memories.length > 0 && (
						<span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
							{memories.length}
						</span>
					)}
				</div>
				<Button variant="ghost" size="icon-xs" onClick={onClose}>
					<X className="h-4 w-4" />
				</Button>
			</div>

			{/* Content */}
			<div className="flex-1 overflow-y-auto p-4 space-y-3">
				{memoriesQuery.isLoading && (
					<p className="py-6 text-center text-xs text-muted-foreground">{t("loadingMemories")}</p>
				)}

				{!memoriesQuery.isLoading && memories.length === 0 && (
					<p className="py-6 text-center text-xs text-muted-foreground">
						{t("noRelevantMemories")}
					</p>
				)}

				{memories.map((memory) => (
					<div key={memory.id} className="rounded-lg border p-3 space-y-2">
						{editingId === memory.id ? (
							<div className="space-y-2">
								<Input
									value={editContent}
									onChange={(e) => setEditContent(e.target.value)}
									autoFocus
									className="text-sm"
								/>
								<div className="flex gap-2">
									<Button
										size="sm"
										onClick={handleSaveEdit}
										disabled={patchMemory.isPending}
										className="h-7 text-xs"
									>
										{t("save")}
									</Button>
									<Button
										size="sm"
										variant="outline"
										onClick={() => setEditingId(null)}
										className="h-7 text-xs"
									>
										{t("cancel")}
									</Button>
								</div>
							</div>
						) : (
							<>
								<p className="text-sm leading-relaxed">{memory.content}</p>
								<div className="flex items-center justify-between">
									<div className="flex items-center gap-2">
										<span
											className={`rounded px-1.5 py-0.5 text-xs ${CATEGORY_COLORS[memory.category] ?? "bg-muted text-muted-foreground"}`}
										>
											{memory.category}
										</span>
										<span className="text-xs text-muted-foreground">{memory.source_stage}</span>
									</div>
									<div className="flex gap-1">
										<Button
											variant="ghost"
											size="icon-xs"
											onClick={() => handleEdit(memory)}
											title={t("editMemory")}
										>
											<Pencil className="h-3 w-3" />
										</Button>
										<Button
											variant="ghost"
											size="icon-xs"
											onClick={() => handleDelete(memory.id)}
											disabled={deleteMemory.isPending}
											title={t("deleteMemory")}
										>
											<Trash2 className="h-3 w-3" />
										</Button>
									</div>
								</div>
							</>
						)}
					</div>
				))}
			</div>

			{/* Footer */}
			<div className="border-t p-3">
				<Button
					variant="outline"
					size="sm"
					className="w-full gap-1.5 text-xs"
					onClick={() => navigate({ to: "/settings" })}
				>
					<ExternalLink className="h-3 w-3" />
					{t("manageAllMemories")}
				</Button>
			</div>
		</div>
	);
}
