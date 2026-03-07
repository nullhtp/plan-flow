import { useMutation, useQueryClient } from "@tanstack/react-query";
import { customFetch } from "@/api/fetcher";
import type {
	CreateBoardFromTemplateRequest,
	CreateBoardFromTemplateResponse,
	TemplateCreateRequest,
	TemplateDetailResponse,
	TemplateUpdateRequest,
} from "../types";

export function useCreateTemplate() {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: async (body: TemplateCreateRequest) => {
			const res = await customFetch<{ data: TemplateDetailResponse }>(
				"/api/templates",
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(body),
				},
			);
			return res.data;
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["templates"] });
		},
	});
}

export function useUpdateTemplate(templateId: string) {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: async (body: TemplateUpdateRequest) => {
			const res = await customFetch<{ data: TemplateDetailResponse }>(
				`/api/templates/${templateId}`,
				{
					method: "PATCH",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(body),
				},
			);
			return res.data;
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["templates"] });
			queryClient.invalidateQueries({ queryKey: ["template", templateId] });
		},
	});
}

export function useDeleteTemplate() {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: async (templateId: string) => {
			await customFetch<{ data: unknown }>(
				`/api/templates/${templateId}`,
				{ method: "DELETE" },
			);
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["templates"] });
		},
	});
}

export function useCreateBoardFromTemplate(templateId: string) {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: async (body: CreateBoardFromTemplateRequest) => {
			const res = await customFetch<{ data: CreateBoardFromTemplateResponse }>(
				`/api/templates/${templateId}/create-board`,
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(body),
				},
			);
			return res.data;
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["boards"] });
		},
	});
}
