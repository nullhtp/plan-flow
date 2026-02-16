import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
	getGetBoardEndpointApiBoardsBoardIdGetQueryKey,
	useDeleteTaskEndpointApiTasksTaskIdDelete,
	useUpdateTaskEndpointApiTasksTaskIdPatch,
} from "@/api/generated/boards/boards";

export function useTaskMutations(boardId: string) {
	const queryClient = useQueryClient();
	const boardQueryKey = getGetBoardEndpointApiBoardsBoardIdGetQueryKey(boardId);

	const invalidateBoard = () => {
		queryClient.invalidateQueries({ queryKey: boardQueryKey });
	};

	const updateTask = useUpdateTaskEndpointApiTasksTaskIdPatch({
		mutation: {
			onSuccess: invalidateBoard,
			onError: (error: unknown) => {
				const message =
					error && typeof error === "object" && "response" in error
						? ((error as { response?: { data?: { detail?: string } } }).response?.data?.detail ??
							"Failed to update task")
						: "Failed to update task";
				toast.error(message);
				invalidateBoard();
			},
		},
	});

	const deleteTask = useDeleteTaskEndpointApiTasksTaskIdDelete({
		mutation: {
			onSuccess: invalidateBoard,
			onError: () => {
				toast.error("Failed to delete task");
				invalidateBoard();
			},
		},
	});

	return { updateTask, deleteTask };
}
