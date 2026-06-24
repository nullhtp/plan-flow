import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
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
	getGetSettingsApiSettingsGetQueryKey,
	type getSettingsApiSettingsGetResponse,
	useGetSettingsApiSettingsGet,
	usePatchSettingsApiSettingsPatch,
} from "@/api/generated/settings/settings";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const CATEGORIES = ["preference", "fact", "pattern", "context"] as const;

const LANGUAGES = [
	{ code: "ru", label: "Русский" },
	{ code: "en", label: "English" },
] as const;

export function SettingsPage() {
	const { t, i18n } = useTranslation("settings");
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

	const settingsKey = getGetSettingsApiSettingsGetQueryKey();
	const settingsData = settingsQuery.data?.data as Record<string, unknown> | undefined;
	const memoriesData = memoriesQuery.data?.data as Record<string, unknown> | undefined;
	const memoryEnabled = (settingsData?.memory_enabled as boolean) ?? true;
	const simpleMode = (settingsData?.simple_mode as boolean) ?? true;
	const memories = (memoriesData?.items ?? []) as MemoryResponse[];
	const totalMemories = (memoriesData?.total as number) ?? 0;
	const totalPages = Math.ceil(totalMemories / 20);
	const stats = statsQuery.data?.data as Record<string, unknown> | undefined;

	const invalidateMemories = () => {
		queryClient.invalidateQueries({ queryKey: getGetMemoriesApiMemoriesGetQueryKey() });
		queryClient.invalidateQueries({ queryKey: getGetStatsApiMemoriesStatsGetQueryKey() });
	};

	const handleToggleMemory = () => {
		patchSettings.mutate(
			{ data: { memory_enabled: !memoryEnabled } },
			{ onSuccess: () => queryClient.invalidateQueries({ queryKey: settingsKey }) },
		);
	};

	// Optimistically write simple_mode into the settings cache so the toggle flips
	// immediately; rolled back on error.
	const writeSimpleMode = (next: boolean) => {
		queryClient.setQueryData<getSettingsApiSettingsGetResponse>(settingsKey, (old) =>
			old && old.status === 200 ? { ...old, data: { ...old.data, simple_mode: next } } : old,
		);
	};

	const handleToggleSimpleMode = () => {
		const next = !simpleMode;
		writeSimpleMode(next);
		patchSettings.mutate(
			{ data: { simple_mode: next } },
			{
				onSuccess: () => queryClient.invalidateQueries({ queryKey: settingsKey }),
				onError: () => {
					writeSimpleMode(!next);
					toast.error(t("updateFailed"));
				},
			},
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
		if (!confirm(t("confirm.deleteMemory"))) return;
		deleteMemory.mutate({ memoryId }, { onSuccess: invalidateMemories });
	};

	const handleBulkDelete = () => {
		const msg = categoryFilter
			? t("confirm.clearCategory", {
					category: t(`categoryLabels.${categoryFilter}`, { defaultValue: categoryFilter }),
				})
			: t("confirm.clearAll");
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
						{t("back")}
					</Button>
					<h1 className="text-2xl font-bold">{t("title")}</h1>
				</div>
			</header>

			<main className="mx-auto w-full max-w-4xl flex-1 space-y-6 p-6">
				{/* Language */}
				<Card className="p-6">
					<div className="flex items-center justify-between">
						<div>
							<h2 className="text-lg font-semibold">{t("language.title")}</h2>
							<p className="text-sm text-muted-foreground">{t("language.description")}</p>
						</div>
						<div className="flex gap-2">
							{LANGUAGES.map((lang) => (
								<Button
									key={lang.code}
									variant={i18n.language === lang.code ? "default" : "outline"}
									onClick={() => i18n.changeLanguage(lang.code)}
								>
									{lang.label}
								</Button>
							))}
						</div>
					</div>
				</Card>

				{/* Simple Mode Toggle (master switch) */}
				<Card className="p-6">
					<div className="flex items-center justify-between">
						<div>
							<h2 className="text-lg font-semibold">{t("simpleMode.title")}</h2>
							<p className="text-sm text-muted-foreground">{t("simpleMode.description")}</p>
						</div>
						<Button
							variant={simpleMode ? "default" : "outline"}
							onClick={handleToggleSimpleMode}
							disabled={patchSettings.isPending}
						>
							{simpleMode ? t("enabled") : t("disabled")}
						</Button>
					</div>
				</Card>

				{/* Memory Toggle */}
				<Card className="p-6">
					<div className="flex items-center justify-between">
						<div>
							<h2 className="text-lg font-semibold">{t("aiMemory.title")}</h2>
							<p className="text-sm text-muted-foreground">{t("aiMemory.description")}</p>
						</div>
						<Button
							variant={memoryEnabled ? "default" : "outline"}
							onClick={handleToggleMemory}
							disabled={patchSettings.isPending}
						>
							{memoryEnabled ? t("enabled") : t("disabled")}
						</Button>
					</div>
				</Card>

				{/* Memory management — hidden in Simple mode */}
				{!simpleMode && (
					<>
						{/* Memory Stats */}
						{stats && (
							<Card className="p-6">
								<h3 className="mb-3 font-semibold">{t("stats.title")}</h3>
								<div className="flex gap-6 text-sm">
									<div title={t("stats.totalTooltip")}>
										<span className="text-muted-foreground">{t("stats.total")}</span>
										<span className="font-medium">{stats.total as number}</span>
									</div>
									{Object.entries((stats.by_category ?? {}) as Record<string, number>).map(
										([cat, count]) => (
											<div
												key={cat}
												title={t(`categoryTooltips.${cat}`, { defaultValue: cat })}
												className="cursor-help border-b border-dotted border-muted-foreground/40"
											>
												<span className="text-muted-foreground">
													{t(`categoryLabels.${cat}`, { defaultValue: cat })}:{" "}
												</span>
												<span className="font-medium">{count as number}</span>
											</div>
										),
									)}
								</div>
							</Card>
						)}

						{/* Memory List Controls */}
						<div className="flex items-center gap-3">
							<Input
								placeholder={t("search")}
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
								<option value="">{t("allCategories")}</option>
								{CATEGORIES.map((cat) => (
									<option key={cat} value={cat}>
										{t(`categoryLabels.${cat}`, { defaultValue: cat })}
									</option>
								))}
							</select>
							<div className="flex-1" />
							<Button
								variant="outline"
								onClick={handleBulkDelete}
								disabled={bulkDelete.isPending || totalMemories === 0}
							>
								{categoryFilter
									? t("clearCategory", {
											category: t(`categoryLabels.${categoryFilter}`, {
												defaultValue: categoryFilter,
											}),
										})
									: t("clearAll")}
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
													{t("save")}
												</Button>
												<Button size="sm" variant="outline" onClick={() => setEditingId(null)}>
													{t("cancel")}
												</Button>
											</div>
										</div>
									) : (
										<div className="flex items-start justify-between gap-4">
											<div className="flex-1">
												<p className="text-sm">{memory.content}</p>
												<div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
													<span className="rounded bg-muted px-1.5 py-0.5">
														{t(`categoryLabels.${memory.category}`, {
															defaultValue: memory.category,
														})}
													</span>
													<span>{memory.source_stage}</span>
													<span>{new Date(memory.created_at).toLocaleDateString()}</span>
												</div>
											</div>
											<div className="flex gap-1">
												<Button size="sm" variant="outline" onClick={() => handleEdit(memory)}>
													{t("edit")}
												</Button>
												<Button
													size="sm"
													variant="outline"
													onClick={() => handleDelete(memory.id)}
													disabled={deleteMemory.isPending}
												>
													{t("delete")}
												</Button>
											</div>
										</div>
									)}
								</Card>
							))}
							{memories.length === 0 && (
								<p className="py-8 text-center text-muted-foreground">
									{searchQuery ? t("noMatch") : t("noMemories")}
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
									{t("pagination.previous")}
								</Button>
								<span className="text-sm text-muted-foreground">
									{t("pagination.page", { page, total: totalPages })}
								</span>
								<Button
									size="sm"
									variant="outline"
									disabled={page >= totalPages}
									onClick={() => setPage((p) => p + 1)}
								>
									{t("pagination.next")}
								</Button>
							</div>
						)}
					</>
				)}
			</main>
		</div>
	);
}
