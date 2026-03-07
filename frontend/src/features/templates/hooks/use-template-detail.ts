import { useQuery } from "@tanstack/react-query";
import { customFetch } from "@/api/fetcher";
import type { TemplateDetailResponse } from "../types";

export function useTemplateDetail(templateId: string) {
	return useQuery({
		queryKey: ["template", templateId],
		queryFn: async () => {
			const res = await customFetch<{ data: TemplateDetailResponse }>(
				`/api/templates/${templateId}`,
				{ method: "GET" },
			);
			return res.data;
		},
		enabled: !!templateId,
	});
}
