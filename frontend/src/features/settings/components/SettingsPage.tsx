import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import {
	getGetMemoriesApiMemoriesGetQueryKey,
	getGetStatsApiMemoriesStatsGetQueryKey,
	useBulkDeleteApiMemoriesDelete,
	useDeleteMemoryByIdApiMemoriesMemoryIdDelete,
	useGetMemoriesApiMemoriesGet,
	useGetStatsApiMemoriesStatsGet,
	usePatchMemoryApiMemoriesMemoryIdPatch,
} from "@/api/generated/memories/memories";
import type { MemoryResponse } from "@/api/generated/model";
import {
	useGetSettingsApiSettingsGet,
	usePatchSettingsApiSettingsPatch,
} from "@/api/generated/settings/settings";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const CATEGORIES = ["preference", "fact", "pattern", "context"] as const;

const CATEGORY_TOOLTIPS: Record<string, string> = {
	preference:
		"Your preferences and answers from goal Q&A (e.g. language, budget, timeline). " +
		"Used in: question generation, board planning, task enrichment, and chat.",
	fact:
		"Factual information about you or your situation (e.g. location, job role). " +
		"Created manually. Used in: question generation, board planning, task enrichment, and chat.",
	pattern:
		"Summaries of boards you've generated (e.g. task count, plan type). " +
		"Used in: question generation, board planning, task enrichment, and chat.",
	context:
		"Goal domains and key dimensions you've worked on (e.g. relocation, career change). " +
		"Used in: question generation, board planning, task enrichment, and chat.",
};

export function SettingsPage() {
	const navigate = useNavigate();
	const queryClient = useQueryClient();

	// Settings
	const settingsQuery = useGetSettingsApiSettingsGet();
	const patchSettings = usePatchSettingsApiSettingsPatch();

	// Memory list state
	const [page, setPage] = useState(1);
	const [searchQuery, setSearchQuery] = useState("");
	const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);
	const [editingId, setEditingId] = useState<string | null>(null);
	const [editContent, setEditContent] = useState("");

	// Memory queries
	const memoriesQuery = useGetMemoriesApiMemoriesGet({
		page,
		page_size: 20,
		category: categoryFilter,
		q: searchQuery || undefined,
	});
	const statsQuery = useGetStatsApiMemoriesStatsGet();

	// Mutations
	const patchMemory = usePatchMemoryApiMemoriesMemoryIdPatch();
	const deleteMemory = useDeleteMemoryByIdApiMemoriesMemoryIdDelete();
	const bulkDelete = useBulkDeleteApiMemoriesDelete();

	const memoryEnabled = settingsQuery.data?.data.memory_enabled ?? true;
	const memories = (memoriesQuery.data?.data.items ?? []) as MemoryResponse[];
	const totalMemories = memoriesQuery.data?.data.total ?? 0;
	const totalPages = Math.ceil(totalMemories / 20);
	const stats = statsQuery.data?.data;

	const invalidateMemories = () => {
		queryClient.invalidateQueries({ queryKey: getGetMemoriesApiMemoriesGetQueryKey() });
		queryClient.invalidateQueries({ queryKey: getGetStatsApiMemoriesStatsGetQueryKey() });
	};

	const handleToggleMemory = () => {
		patchSettings.mutate(
			{ data: { memory_enabled: !memoryEnabled } },
			{ onSuccess: () => queryClient.invalidateQueries({ queryKey: ["/api/settings"] }) },
		);
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
		if (!confirm("Delete this memory?")) return;
		deleteMemory.mutate({ memoryId }, { onSuccess: invalidateMemories });
	};

	const handleBulkDelete = () => {
		const msg = categoryFilter
			? `Clear all "${categoryFilter}" memories?`
			: "Clear ALL memories? This cannot be undone.";
		if (!confirm(msg)) return;
		bulkDelete.mutate(
			{ data: { category: categoryFilter ?? null } },
			{ onSuccess: invalidateMemories },
		);
	};

	return (
		<div className="flex min-h-screen flex-col">
			<header className="flex items-center justify-between border-b px-6 py-4">
				<div className="flex items-center gap-4">
					<Button variant="outline" onClick={() => navigate({ to: "/" })}>
						Back
					</Button>
					<h1 className="text-2xl font-bold">Settings</h1>
				</div>
			</header>

			<main className="mx-auto w-full max-w-4xl flex-1 space-y-6 p-6">
				{/* Memory Toggle */}
				<Card className="p-6">
					<div className="flex items-center justify-between">
						<div>
							<h2 className="text-lg font-semibold">AI Memory</h2>
							<p className="text-sm text-muted-foreground">
								When enabled, the AI remembers your preferences and past goals to personalize
								responses.
							</p>
						</div>
						<Button
							variant={memoryEnabled ? "default" : "outline"}
							onClick={handleToggleMemory}
							disabled={patchSettings.isPending}
						>
							{memoryEnabled ? "Enabled" : "Disabled"}
						</Button>
					</div>
				</Card>

				{/* Memory Stats */}
				{stats && (
					<Card className="p-6">
						<h3 className="mb-3 font-semibold">Memory Statistics</h3>
						<div className="flex gap-6 text-sm">
							<div title="Total number of memories stored by the AI across all categories">
								<span className="text-muted-foreground">Total: </span>
								<span className="font-medium">{stats.total}</span>
							</div>
							{Object.entries(stats.by_category).map(([cat, count]) => (
								<div
									key={cat}
									title={CATEGORY_TOOLTIPS[cat] ?? cat}
									className="cursor-help border-b border-dotted border-muted-foreground/40"
								>
									<span className="text-muted-foreground">{cat}: </span>
									<span className="font-medium">{count as number}</span>
								</div>
							))}
						</div>
					</Card>
				)}

				{/* Memory List Controls */}
				<div className="flex items-center gap-3">
					<Input
						placeholder="Search memories..."
						value={searchQuery}
						onChange={(e) => {
							setSearchQuery(e.target.value);
							setPage(1);
						}}
						className="max-w-xs"
					/>
					<select
						className="rounded-md border px-3 py-2 text-sm"
						value={categoryFilter ?? ""}
						onChange={(e) => {
							setCategoryFilter(e.target.value || undefined);
							setPage(1);
						}}
					>
						<option value="">All categories</option>
						{CATEGORIES.map((cat) => (
							<option key={cat} value={cat}>
								{cat}
							</option>
						))}
					</select>
					<div className="flex-1" />
					<Button
						variant="outline"
						onClick={handleBulkDelete}
						disabled={bulkDelete.isPending || totalMemories === 0}
					>
						{categoryFilter ? `Clear "${categoryFilter}"` : "Clear All Memories"}
					</Button>
				</div>

				{/* Memory List */}
				<div className="space-y-2">
					{memories.map((memory) => (
						<Card key={memory.id} className="p-4">
							{editingId === memory.id ? (
								<div className="space-y-2">
									<Input
										value={editContent}
										onChange={(e) => setEditContent(e.target.value)}
										autoFocus
									/>
									<div className="flex gap-2">
										<Button size="sm" onClick={handleSaveEdit} disabled={patchMemory.isPending}>
											Save
										</Button>
										<Button size="sm" variant="outline" onClick={() => setEditingId(null)}>
											Cancel
										</Button>
									</div>
								</div>
							) : (
								<div className="flex items-start justify-between gap-4">
									<div className="flex-1">
										<p className="text-sm">{memory.content}</p>
										<div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
											<span className="rounded bg-muted px-1.5 py-0.5">{memory.category}</span>
											<span>{memory.source_stage}</span>
											<span>{new Date(memory.created_at).toLocaleDateString()}</span>
										</div>
									</div>
									<div className="flex gap-1">
										<Button size="sm" variant="outline" onClick={() => handleEdit(memory)}>
											Edit
										</Button>
										<Button
											size="sm"
											variant="outline"
											onClick={() => handleDelete(memory.id)}
											disabled={deleteMemory.isPending}
										>
											Delete
										</Button>
									</div>
								</div>
							)}
						</Card>
					))}
					{memories.length === 0 && (
						<p className="py-8 text-center text-muted-foreground">
							{searchQuery ? "No memories match your search." : "No memories stored yet."}
						</p>
					)}
				</div>

				{/* Pagination */}
				{totalPages > 1 && (
					<div className="flex items-center justify-center gap-2">
						<Button
							size="sm"
							variant="outline"
							disabled={page <= 1}
							onClick={() => setPage((p) => p - 1)}
						>
							Previous
						</Button>
						<span className="text-sm text-muted-foreground">
							Page {page} of {totalPages}
						</span>
						<Button
							size="sm"
							variant="outline"
							disabled={page >= totalPages}
							onClick={() => setPage((p) => p + 1)}
						>
							Next
						</Button>
					</div>
				)}
			</main>
		</div>
	);
}
