import { createRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BoardCard } from "@/features/board/components/BoardCard";
import { useBoardListData } from "@/features/board/hooks/use-board-list";
import { TemplatesGallery } from "@/features/templates/components/TemplatesGallery";
import { CreationCard } from "@/shared/components/creation-card";
import { UserDropdown } from "@/shared/components/user-dropdown";
import { authenticatedRoute } from "./_authenticated";

type IndexSearchParams = {
	tab?: "boards" | "templates";
};

export const indexRoute = createRoute({
	getParentRoute: () => authenticatedRoute,
	path: "/",
	validateSearch: (search: Record<string, unknown>): IndexSearchParams => ({
		tab: search.tab === "boards" || search.tab === "templates" ? search.tab : undefined,
	}),
	component: IndexPage,
});

function IndexPage() {
	const navigate = useNavigate();
	const { tab } = indexRoute.useSearch();
	const activeTab = tab ?? "boards";

	return (
		<div className="flex min-h-screen flex-col">
			{/* Header */}
			<header className="flex items-center justify-between border-b px-6 py-4">
				<h1 className="text-2xl font-bold">PlanFlow</h1>
				<UserDropdown />
			</header>

			{/* Tabbed Content */}
			<main className="flex-1 p-6">
				<Tabs
					value={activeTab}
					onValueChange={(value) =>
						navigate({
							to: "/",
							search: value === "boards" ? {} : { tab: value as "templates" },
							replace: true,
						})
					}
				>
					<TabsList className="mb-6">
						<TabsTrigger value="boards">Boards</TabsTrigger>
						<TabsTrigger value="templates">Templates</TabsTrigger>
					</TabsList>

					<TabsContent value="boards">
						<BoardsTabContent />
					</TabsContent>

					<TabsContent value="templates">
						<TemplatesGallery />
					</TabsContent>
				</Tabs>
			</main>
		</div>
	);
}

function BoardsTabContent() {
	const [view, setView] = useState<"mine" | "shared">("mine");
	const boards = useBoardListData();
	const sharedBoards = useBoardListData(true);

	return (
		<div>
			{/* Secondary toggle */}
			<div className="mb-4 flex gap-2">
				<Button
					variant={view === "mine" ? "default" : "outline"}
					size="sm"
					onClick={() => setView("mine")}
				>
					My Boards
				</Button>
				<Button
					variant={view === "shared" ? "default" : "outline"}
					size="sm"
					onClick={() => setView("shared")}
				>
					Shared with Me
				</Button>
			</div>

			{view === "mine" ? (
				<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
					<CreationCard label="New Board" href="/goals/new" />
					{boards.map((board) => (
						<BoardCard key={board.id} board={board} />
					))}
				</div>
			) : sharedBoards.length > 0 ? (
				<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
					{sharedBoards.map((board) => (
						<BoardCard key={board.id} board={board} />
					))}
				</div>
			) : (
				<div className="flex flex-col items-center justify-center py-20">
					<p className="text-muted-foreground">No shared boards yet.</p>
				</div>
			)}
		</div>
	);
}
