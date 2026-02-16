import {
	useGenerateBoardEndpointApiGoalsGoalIdGenerateBoardPost,
	useGetBoardEndpointApiBoardsBoardIdGet,
} from "@/api/generated/boards/boards";
import {
	useCreateGoalEndpointApiGoalsPost,
	useGetGoalEndpointApiGoalsGoalIdGet,
	useSubmitAnswersEndpointApiGoalsGoalIdAnswersPost,
} from "@/api/generated/goals/goals";
import type { GoalRejectionResponse } from "@/api/generated/model";

export function useCreateGoal() {
	return useCreateGoalEndpointApiGoalsPost<GoalRejectionResponse>();
}

export function useSubmitAnswers() {
	return useSubmitAnswersEndpointApiGoalsGoalIdAnswersPost();
}

export function useGoal(goalId: string) {
	return useGetGoalEndpointApiGoalsGoalIdGet(goalId, {
		query: {
			enabled: !!goalId,
		},
	});
}

export function useGenerateBoard() {
	return useGenerateBoardEndpointApiGoalsGoalIdGenerateBoardPost();
}

export function useBoard(boardId: string) {
	return useGetBoardEndpointApiBoardsBoardIdGet(boardId, {
		query: {
			enabled: !!boardId,
		},
	});
}
