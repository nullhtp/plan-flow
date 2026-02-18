import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { generateSubtaskActionApiTasksTaskIdSubtasksSubtaskIdActionsGeneratePost } from "@/api/generated/ai/ai";
import {
	getGetBoardEndpointApiBoardsBoardIdGetQueryKey,
	useCreateSubtaskEndpointApiTasksTaskIdSubtasksPost,
	useDeleteSubtaskEndpointApiSubtasksSubtaskIdDelete,
	useUpdateSubtaskEndpointApiSubtasksSubtaskIdPatch,
} from "@/api/generated/boards/boards";
import type { BoardResponse } from "../types";

export function useSubtaskMutations(boardId: string) {
	const queryClient = useQueryClient();
	const boardQueryKey = getGetBoardEndpointApiBoardsBoardIdGetQueryKey(boardId);

	const invalidateBoard = () => {
		queryClient.invalidateQueries({ queryKey: boardQueryKey });
	};

	const createSubtask = useCreateSubtaskEndpointApiTasksTaskIdSubtasksPost({
		mutation: {
			onSuccess: (response, variables) => {
				invalidateBoard();

				// Fire-and-forget action generation for the newly created subtask
				if (response.status === 201) {
					const board = response.data as BoardResponse;
					const taskId = variables.taskId;
					const task = board.tasks.find((t) => t.id === taskId);
					if (task && task.subtasks.length > 0) {
						// The newest subtask is the one most recently created
						// (last by position or created_at)
						const newest = [...task.subtasks].sort(
							(a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
						)[0];
						if (newest && newest.action_prompt == null) {
							generateSubtaskActionApiTasksTaskIdSubtasksSubtaskIdActionsGeneratePost(
								taskId,
								newest.id,
							)
								.then(() => invalidateBoard())
								.catch(() => {
									// Graceful degradation — subtask exists without action
								});
						}
					}
				}
			},
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
