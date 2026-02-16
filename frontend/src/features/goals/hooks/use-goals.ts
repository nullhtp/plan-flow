import { useGenerateBoardEndpointApiGoalsGoalIdGenerateBoardPost } from "@/api/generated/boards/boards";
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

// Re-export useBoard from its new location for backward compatibility
export { useBoard } from "@/features/board/hooks/use-board";
