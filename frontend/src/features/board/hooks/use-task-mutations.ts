import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
	getGetBoardEndpointApiBoardsBoardIdGetQueryKey,
	useDeleteTaskEndpointApiTasksTaskIdDelete,
	useUpdateTaskEndpointApiTasksTaskIdPatch,
} from "@/api/generated/boards/boards";

export function useTaskMutations(boardId: string) {
	const { t } = useTranslation("board");
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
							t("taskMutations.failedToUpdate"))
						: t("taskMutations.failedToUpdate");
				toast.error(message);
				invalidateBoard();
			},
		},
	});

	const deleteTask = useDeleteTaskEndpointApiTasksTaskIdDelete({
		mutation: {
			onSuccess: invalidateBoard,
			onError: () => {
				toast.error(t("taskMutations.failedToDelete"));
				invalidateBoard();
			},
		},
	});

	return { updateTask, deleteTask };
}
