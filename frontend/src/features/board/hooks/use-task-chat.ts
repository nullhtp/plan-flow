import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { taskChatApiTasksTaskIdChatPost } from "@/api/generated/ai/ai";
import {
	getGetBoardEndpointApiBoardsBoardIdGetQueryKey,
	getListArtifactsEndpointApiTasksTaskIdArtifactsGetQueryKey,
} from "@/api/generated/boards/boards";
import type { ChatResponse, ToolAction } from "@/api/generated/model";

export interface ChatMessage {
	id: string;
	role: "user" | "assistant";
	content: string;
	actions?: ToolAction[];
	pendingActionId?: string | null;
}

interface UseTaskChatReturn {
	messages: ChatMessage[];
	isLoading: boolean;
	sendMessage: (message: string) => Promise<void>;
}

let messageIdCounter = 0;

export function useTaskChat(taskId: string, boardId: string) {
	const [messages, setMessages] = useState<ChatMessage[]>([]);
	const [isLoading, setIsLoading] = useState(false);
	const queryClient = useQueryClient();

	const sendMessage = useCallback(
		async (message: string) => {
			const userMsg: ChatMessage = {
				id: `msg-${++messageIdCounter}`,
				role: "user",
				content: message,
			};
			setMessages((prev) => [...prev, userMsg]);
			setIsLoading(true);

			try {
				const response = await taskChatApiTasksTaskIdChatPost(taskId, {
					message,
				});

				if (response.status === 200) {
					const data = response.data as ChatResponse;

					const assistantMsg: ChatMessage = {
						id: `msg-${++messageIdCounter}`,
						role: "assistant",
						content: data.response,
						actions: data.actions,
						pendingActionId: data.pending_action_id,
					};
					setMessages((prev) => [...prev, assistantMsg]);

					// Invalidate board query if any tool actions were executed
					const hasExecutedActions = data.actions?.some((a) => a.status === "executed");
					if (hasExecutedActions) {
						const boardQueryKey = getGetBoardEndpointApiBoardsBoardIdGetQueryKey(boardId);
						queryClient.invalidateQueries({ queryKey: boardQueryKey });
					}

					// Invalidate artifacts if save_artifact was called
					const hasSaveArtifact = data.actions?.some(
						(a) => a.tool_name === "save_artifact" && a.status === "executed",
					);
					if (hasSaveArtifact) {
						const artifactsQueryKey =
							getListArtifactsEndpointApiTasksTaskIdArtifactsGetQueryKey(taskId);
						queryClient.invalidateQueries({ queryKey: artifactsQueryKey });
					}
				}
			} catch {
				const errorMsg: ChatMessage = {
					id: `msg-${++messageIdCounter}`,
					role: "assistant",
					content: "Sorry, something went wrong. Please try again.",
				};
				setMessages((prev) => [...prev, errorMsg]);
			} finally {
				setIsLoading(false);
			}
		},
		[taskId, boardId, queryClient],
	);

	return { messages, isLoading, sendMessage } satisfies UseTaskChatReturn;
}
