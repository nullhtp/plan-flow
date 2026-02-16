import {
	getGetBoardEndpointApiBoardsBoardIdGetQueryKey,
	useGetBoardEndpointApiBoardsBoardIdGet,
} from "@/api/generated/boards/boards";
import type { BoardResponse } from "@/api/generated/model";

export function useBoard(boardId: string) {
	return useGetBoardEndpointApiBoardsBoardIdGet(boardId, {
		query: { enabled: !!boardId },
	});
}

export function useBoardData(boardId: string): BoardResponse | undefined {
	const query = useBoard(boardId);
	return query.data?.data as BoardResponse | undefined;
}

export { getGetBoardEndpointApiBoardsBoardIdGetQueryKey as getBoardQueryKey };
