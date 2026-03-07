import { useQuery } from "@tanstack/react-query";
import { customFetch } from "@/api/fetcher";
import type { BoardListResponse } from "@/features/board/types";

export function useBoardList(shared = false) {
	const qs = shared ? "?shared=true" : "";
	return useQuery({
		queryKey: ["boards", { shared }],
		queryFn: async () => {
			const res = await customFetch<{ data: BoardListResponse[] }>(`/api/boards${qs}`, {
				method: "GET",
			});
			return res.data;
		},
	});
}

export function useBoardListData(shared = false): BoardListResponse[] {
	const query = useBoardList(shared);
	return query.data ?? [];
}
