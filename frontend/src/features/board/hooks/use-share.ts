import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { customFetch } from "@/api/fetcher";
import type { BoardMemberResponse, ShareLinkResponse } from "@/features/board/types";

export function useShareLink(boardId: string) {
	return useQuery({
		queryKey: ["board-share", boardId],
		queryFn: async () => {
			try {
				const res = await customFetch<{ data: ShareLinkResponse }>(`/api/boards/${boardId}/share`, {
					method: "GET",
				});
				return res.data;
			} catch (err: unknown) {
				if (typeof err === "object" && err !== null && "status" in err && (err as { status: number }).status === 404) {
					return null;
				}
				throw err;
			}
		},
	});
}

export function useCreateShareLink(boardId: string) {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: async () => {
			const res = await customFetch<{ data: ShareLinkResponse }>(`/api/boards/${boardId}/share`, {
				method: "POST",
			});
			return res.data;
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["board-share", boardId] });
		},
	});
}

export function useDeleteShareLink(boardId: string) {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: async () => {
			await customFetch(`/api/boards/${boardId}/share`, { method: "DELETE" });
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["board-share", boardId] });
		},
	});
}

export function useBoardMembers(boardId: string) {
	return useQuery({
		queryKey: ["board-members", boardId],
		queryFn: async () => {
			const res = await customFetch<{ data: BoardMemberResponse[] }>(`/api/boards/${boardId}/members`, {
				method: "GET",
			});
			return res.data;
		},
	});
}

export function useRevokeMember(boardId: string) {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: async (userId: string) => {
			await customFetch(`/api/boards/${boardId}/members/${userId}`, { method: "DELETE" });
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["board-members", boardId] });
		},
	});
}

export function useJoinBoard() {
	return useMutation({
		mutationFn: async (token: string) => {
			const res = await customFetch<{ data: { board_id: string; board_title: string; role: string } }>("/api/boards/join", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ token }),
			});
			return res.data;
		},
	});
}
