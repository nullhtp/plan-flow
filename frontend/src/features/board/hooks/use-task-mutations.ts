import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
	getGetBoardEndpointApiBoardsBoardIdGetQueryKey,
	useCreateTaskEndpointApiColumnsColumnIdTasksPost,
	useDeleteTaskEndpointApiTasksTaskIdDelete,
	useUpdateTaskEndpointApiTasksTaskIdPatch,
} from "@/api/generated/boards/boards";

export function useTaskMutations(boardId: string) {
	const queryClient = useQueryClient();
	const boardQueryKey = getGetBoardEndpointApiBoardsBoardIdGetQueryKey(boardId);

	const invalidateBoard = () => {
		queryClient.invalidateQueries({ queryKey: boardQueryKey });
	};

	const createTask = useCreateTaskEndpointApiColumnsColumnIdTasksPost({
		mutation: {
			onSuccess: invalidateBoard,
			onError: () => toast.error("Failed to create task"),
		},
	});

	const updateTask = useUpdateTaskEndpointApiTasksTaskIdPatch({
		mutation: {
			onSuccess: invalidateBoard,
			onError: () => toast.error("Failed to update task"),
		},
	});

	const deleteTask = useDeleteTaskEndpointApiTasksTaskIdDelete({
		mutation: {
			onSuccess: invalidateBoard,
			onError: () => toast.error("Failed to delete task"),
		},
	});

	return { createTask, updateTask, deleteTask };
}
