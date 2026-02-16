import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
	getGetBoardEndpointApiBoardsBoardIdGetQueryKey,
	useCreateSubtaskEndpointApiTasksTaskIdSubtasksPost,
	useDeleteSubtaskEndpointApiSubtasksSubtaskIdDelete,
	useUpdateSubtaskEndpointApiSubtasksSubtaskIdPatch,
} from "@/api/generated/boards/boards";

export function useSubtaskMutations(boardId: string) {
	const queryClient = useQueryClient();
	const boardQueryKey = getGetBoardEndpointApiBoardsBoardIdGetQueryKey(boardId);

	const invalidateBoard = () => {
		queryClient.invalidateQueries({ queryKey: boardQueryKey });
	};

	const createSubtask = useCreateSubtaskEndpointApiTasksTaskIdSubtasksPost({
		mutation: {
			onSuccess: invalidateBoard,
			onError: () => toast.error("Failed to create subtask"),
		},
	});

	const updateSubtask = useUpdateSubtaskEndpointApiSubtasksSubtaskIdPatch({
		mutation: {
			onSuccess: invalidateBoard,
			onError: () => toast.error("Failed to update subtask"),
		},
	});

	const deleteSubtask = useDeleteSubtaskEndpointApiSubtasksSubtaskIdDelete({
		mutation: {
			onSuccess: invalidateBoard,
			onError: () => toast.error("Failed to delete subtask"),
		},
	});

	return { createSubtask, updateSubtask, deleteSubtask };
}
