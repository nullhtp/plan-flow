import { useQuery } from "@tanstack/react-query";
import { customFetch } from "@/api/fetcher";
import type { TemplateListResponse } from "../types";

interface UseTemplatesParams {
	visibility?: "public" | "mine";
	category?: string | null;
	search?: string | null;
	page?: number;
	perPage?: number;
}

export function useTemplates({
	visibility = "public",
	category,
	search,
	page = 1,
	perPage = 20,
}: UseTemplatesParams = {}) {
	return useQuery({
		queryKey: ["templates", { visibility, category, search, page, perPage }],
		queryFn: async () => {
			const params = new URLSearchParams();
			params.set("visibility", visibility);
			params.set("page", String(page));
			params.set("per_page", String(perPage));
			if (category) params.set("category", category);
			if (search) params.set("search", search);

			const res = await customFetch<{ data: TemplateListResponse }>(
				`/api/templates?${params.toString()}`,
				{ method: "GET" },
			);
			return res.data;
		},
	});
}
