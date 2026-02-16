import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
	getGetBoardEndpointApiBoardsBoardIdGetQueryKey,
	useCreateColumnEndpointApiBoardsBoardIdColumnsPost,
	useDeleteColumnEndpointApiColumnsColumnIdDelete,
	useUpdateColumnEndpointApiColumnsColumnIdPatch,
} from "@/api/generated/boards/boards";

export function useColumnMutations(boardId: string) {
	const queryClient = useQueryClient();
	const boardQueryKey = getGetBoardEndpointApiBoardsBoardIdGetQueryKey(boardId);

	const invalidateBoard = () => {
		queryClient.invalidateQueries({ queryKey: boardQueryKey });
	};

	const createColumn = useCreateColumnEndpointApiBoardsBoardIdColumnsPost({
		mutation: {
			onSuccess: invalidateBoard,
			onError: () => toast.error("Failed to create column"),
		},
	});

	const updateColumn = useUpdateColumnEndpointApiColumnsColumnIdPatch({
		mutation: {
			onSuccess: invalidateBoard,
			onError: () => toast.error("Failed to update column"),
		},
	});

	const deleteColumn = useDeleteColumnEndpointApiColumnsColumnIdDelete({
		mutation: {
			onSuccess: invalidateBoard,
			onError: () => toast.error("Failed to delete column"),
		},
	});

	return { createColumn, updateColumn, deleteColumn };
}
