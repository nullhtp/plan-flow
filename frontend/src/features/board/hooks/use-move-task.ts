import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
	getGetBoardEndpointApiBoardsBoardIdGetQueryKey,
	useUpdateTaskEndpointApiTasksTaskIdPatch,
} from "@/api/generated/boards/boards";

export function useMoveTask(boardId: string) {
	const queryClient = useQueryClient();
	const boardQueryKey = getGetBoardEndpointApiBoardsBoardIdGetQueryKey(boardId);

	const mutation = useUpdateTaskEndpointApiTasksTaskIdPatch({
		mutation: {
			onSettled: () => {
				queryClient.invalidateQueries({ queryKey: boardQueryKey });
			},
			onError: () => toast.error("Failed to move task"),
		},
	});

	return mutation;
}
