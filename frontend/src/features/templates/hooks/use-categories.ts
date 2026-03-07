import { useQuery } from "@tanstack/react-query";
import { customFetch } from "@/api/fetcher";
import type { TemplateCategoryResponse } from "../types";

export function useCategories() {
	return useQuery({
		queryKey: ["templateCategories"],
		queryFn: async () => {
			const res = await customFetch<{ data: TemplateCategoryResponse[] }>(
				"/api/templates/categories",
				{ method: "GET" },
			);
			return res.data;
		},
		staleTime: 5 * 60 * 1000,
	});
}

export function useCategoriesData(): TemplateCategoryResponse[] {
	const query = useCategories();
	return query.data ?? [];
}
