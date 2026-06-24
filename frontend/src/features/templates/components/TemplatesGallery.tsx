import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CreationCard } from "@/shared/components/creation-card";
import { useSimpleMode } from "@/shared/hooks/use-simple-mode";
import { useCategoriesData } from "../hooks/use-categories";
import { useTemplates } from "../hooks/use-templates";
import type { TemplateListItemResponse } from "../types";
import { CategoryFilter } from "./CategoryFilter";
import { TemplateCard } from "./TemplateCard";
import { UseTemplateDialog } from "./UseTemplateDialog";

export function TemplatesGallery() {
	const { isSimpleMode } = useSimpleMode();
	const [tab, setTab] = useState<"public" | "mine">("public");
	const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
	const [search, setSearch] = useState("");
	const [page, setPage] = useState(1);
	// In Simple mode, selecting a template opens the create-board dialog directly
	// instead of navigating to the (hidden) template editor.
	const [useTemplateTarget, setUseTemplateTarget] = useState<TemplateListItemResponse | null>(null);
	const categories = useCategoriesData();
	const { data, isLoading } = useTemplates({
		visibility: tab,
		category: selectedCategory,
		search: search || undefined,
		page,
		perPage: 20,
	});

	const handleCategoryChange = (slug: string | null) => {
		setSelectedCategory(slug);
		setPage(1);
	};

	const handleSearch = (value: string) => {
		setSearch(value);
		setPage(1);
	};

	return (
		<div>
			{/* Secondary toggle */}
			<div className="mb-4 flex gap-2">
				<Button
					variant={tab === "public" ? "default" : "outline"}
					size="sm"
					onClick={() => {
						setTab("public");
						setPage(1);
					}}
				>
					Public Templates
				</Button>
				<Button
					variant={tab === "mine" ? "default" : "outline"}
					size="sm"
					onClick={() => {
						setTab("mine");
						setPage(1);
					}}
				>
					My Templates
				</Button>
			</div>

			{/* Search */}
			<div className="mb-4">
				<Input
					placeholder="Search templates..."
					value={search}
					onChange={(e) => handleSearch(e.target.value)}
					className="max-w-sm"
				/>
			</div>

			{/* Category filter */}
			<div className="mb-6">
				<CategoryFilter
					categories={categories}
					selected={selectedCategory}
					onSelect={handleCategoryChange}
				/>
			</div>

			{/* Template grid */}
			{isLoading ? (
				<p className="text-muted-foreground">Loading templates...</p>
			) : (
				<>
					<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
						{/* Authoring a template is hidden in Simple mode. */}
						{!isSimpleMode && <CreationCard label="Create Template" href="/templates/generate" />}
						{data?.items.map((template) => (
							<TemplateCard
								key={template.id}
								template={template}
								onSelect={isSimpleMode ? setUseTemplateTarget : undefined}
							/>
						))}
					</div>

					{data && data.items.length === 0 && (
						<p className="mt-8 text-center text-muted-foreground">
							{tab === "mine" ? "You haven't created any templates yet." : "No templates found."}
						</p>
					)}

					{/* Pagination */}
					{data && data.total_pages > 1 && (
						<div className="mt-6 flex items-center justify-center gap-2">
							<Button
								variant="outline"
								size="sm"
								disabled={page <= 1}
								onClick={() => setPage(page - 1)}
							>
								Previous
							</Button>
							<span className="text-sm text-muted-foreground">
								Page {data.page} of {data.total_pages}
							</span>
							<Button
								variant="outline"
								size="sm"
								disabled={page >= data.total_pages}
								onClick={() => setPage(page + 1)}
							>
								Next
							</Button>
						</div>
					)}
				</>
			)}

			{useTemplateTarget && (
				<UseTemplateDialog
					templateId={useTemplateTarget.id}
					templateTitle={useTemplateTarget.title}
					open
					onClose={() => setUseTemplateTarget(null)}
				/>
			)}
		</div>
	);
}
