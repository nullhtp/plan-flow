import { useListBoardsEndpointApiBoardsGet } from "@/api/generated/boards/boards";
import type { BoardListResponse } from "@/api/generated/model";

export function useBoardList() {
	return useListBoardsEndpointApiBoardsGet();
}

export function useBoardListData(): BoardListResponse[] {
	const query = useBoardList();
	return (query.data?.data as BoardListResponse[] | undefined) ?? [];
}
