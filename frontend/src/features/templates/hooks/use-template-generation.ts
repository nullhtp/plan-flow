import { useMutation, useQueryClient } from "@tanstack/react-query";
import { customFetch } from "@/api/fetcher";
import type {
	ContentExtractionResponse,
	GenerateTemplateResponse,
	SaveGeneratedTemplateRequest,
	TemplateAnswerResponse,
	TemplateAnswerSubmission,
	TemplateClassifyRequest,
	TemplateClassifyResponse,
	TemplateDetailResponse,
} from "../types";

export function useExtractContent() {
	return useMutation({
		mutationFn: async (
			input: { file: File } | { url: string },
		): Promise<ContentExtractionResponse> => {
			if ("file" in input) {
				const formData = new FormData();
				formData.append("file", input.file);
				const res = await customFetch<{ data: ContentExtractionResponse }>(
					"/api/templates/extract-content/file",
					{ method: "POST", body: formData },
				);
				return res.data;
			}
			const res = await customFetch<{ data: ContentExtractionResponse }>(
				"/api/templates/extract-content/url",
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ url: input.url }),
				},
			);
			return res.data;
		},
	});
}

export function useGenerateTemplate() {
	return useMutation({
		mutationFn: async (body: {
			content: string;
			title?: string;
		}): Promise<GenerateTemplateResponse> => {
			const res = await customFetch<{ data: GenerateTemplateResponse }>("/api/templates/generate", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(body),
			});
			return res.data;
		},
	});
}

export function useSaveGeneratedTemplate() {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: async (body: SaveGeneratedTemplateRequest): Promise<TemplateDetailResponse> => {
			const res = await customFetch<{ data: TemplateDetailResponse }>(
				"/api/templates/save-generated",
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

export function useTemplateClassify() {
	return useMutation({
		mutationFn: async (body: TemplateClassifyRequest): Promise<TemplateClassifyResponse> => {
			const res = await customFetch<{ data: TemplateClassifyResponse }>("/api/templates/classify", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(body),
			});
			return res.data;
		},
	});
}

export function useTemplateSubmitAnswers() {
	return useMutation({
		mutationFn: async (body: TemplateAnswerSubmission): Promise<TemplateAnswerResponse> => {
			const res = await customFetch<{ data: TemplateAnswerResponse }>("/api/templates/answers", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(body),
			});
			return res.data;
		},
	});
}
