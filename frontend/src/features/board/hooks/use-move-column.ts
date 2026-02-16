import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
	getGetBoardEndpointApiBoardsBoardIdGetQueryKey,
	useUpdateColumnEndpointApiColumnsColumnIdPatch,
} from "@/api/generated/boards/boards";

export function useMoveColumn(boardId: string) {
	const queryClient = useQueryClient();
	const boardQueryKey = getGetBoardEndpointApiBoardsBoardIdGetQueryKey(boardId);

	const mutation = useUpdateColumnEndpointApiColumnsColumnIdPatch({
		mutation: {
			onSettled: () => {
				queryClient.invalidateQueries({ queryKey: boardQueryKey });
			},
			onError: () => toast.error("Failed to move column"),
		},
	});

	return mutation;
}
