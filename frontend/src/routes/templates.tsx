import { createRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CategoryFilter } from "@/features/templates/components/CategoryFilter";
import { GenerateTemplateDialog } from "@/features/templates/components/GenerateTemplateDialog";
import { TemplateCard } from "@/features/templates/components/TemplateCard";
import { useCategoriesData } from "@/features/templates/hooks/use-categories";
import { useTemplates } from "@/features/templates/hooks/use-templates";
import { authenticatedRoute } from "./_authenticated";

export const templatesRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/templates",
	component: TemplatesPage,
});

function TemplatesPage() {
	const navigate = useNavigate();
	const [tab, setTab] = useState<"public" | "mine">("public");
	const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
	const [search, setSearch] = useState("");
	const [page, setPage] = useState(1);
	const [showGenerate, setShowGenerate] = useState(false);

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
		<div className="flex min-h-screen flex-col">
			<header className="flex items-center justify-between border-b px-6 py-4">
				<h1 className="text-2xl font-bold">Templates</h1>
				<div className="flex gap-2">
					<Button onClick={() => setShowGenerate(true)}>Generate Template</Button>
					<Button variant="outline" onClick={() => navigate({ to: "/" })}>
						Back to Boards
					</Button>
				</div>
			</header>

			<main className="flex-1 p-6">
				{/* Tab toggle */}
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
				) : data && data.items.length > 0 ? (
					<>
						<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
							{data.items.map((template) => (
								<TemplateCard key={template.id} template={template} />
							))}
						</div>

						{/* Pagination */}
						{data.total_pages > 1 && (
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
				) : (
					<div className="flex flex-col items-center justify-center gap-4 py-20">
						<p className="text-muted-foreground">
							{tab === "mine"
								? "You haven't created any templates yet. Save a board as a template to get started."
								: "No templates found."}
						</p>
					</div>
				)}
			</main>

			<GenerateTemplateDialog open={showGenerate} onClose={() => setShowGenerate(false)} />
		</div>
	);
}
