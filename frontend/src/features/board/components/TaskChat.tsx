import { useQueryClient } from "@tanstack/react-query";
import { Check, Loader2, MessageSquare, Send, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import {
	confirmPendingActionApiActionsActionIdConfirmPost,
	rejectPendingActionApiActionsActionIdRejectPost,
} from "@/api/generated/ai-actions/ai-actions";
import { getGetBoardEndpointApiBoardsBoardIdGetQueryKey } from "@/api/generated/boards/boards";
import type { ToolAction } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { type ChatMessage, useTaskChat } from "../hooks/use-task-chat";

interface TaskChatProps {
	taskId: string;
	boardId: string;
	initialPrompt?: string | null;
}

function ToolActionCard({ action }: { action: ToolAction }) {
	const statusBadge: Record<string, string> = {
		executed: "bg-green-100 text-green-700",
		pending_confirmation: "bg-yellow-100 text-yellow-700",
		failed: "bg-red-100 text-red-700",
	};

	return (
		<div className="flex items-center gap-2 rounded border px-2 py-1 text-xs">
			<span
				className={`rounded-full px-1.5 py-0.5 ${statusBadge[action.status] ?? "bg-gray-100 text-gray-700"}`}
			>
				{action.status.replace("_", " ")}
			</span>
			<span className="text-muted-foreground">{action.tool_name}</span>
			{action.description && <span className="truncate">{action.description}</span>}
		</div>
	);
}

function PendingActionCard({ actionId, boardId }: { actionId: string; boardId: string }) {
	const [isConfirming, setIsConfirming] = useState(false);
	const [isRejecting, setIsRejecting] = useState(false);
	const [resolved, setResolved] = useState<string | null>(null);
	const queryClient = useQueryClient();

	const handleConfirm = async () => {
		setIsConfirming(true);
		try {
			const res = await confirmPendingActionApiActionsActionIdConfirmPost(actionId);
			if (res.status === 200) {
				setResolved("confirmed");
				const boardQueryKey = getGetBoardEndpointApiBoardsBoardIdGetQueryKey(boardId);
				queryClient.invalidateQueries({ queryKey: boardQueryKey });
				toast.success("Action confirmed");
			}
		} catch {
			toast.error("Failed to confirm action");
		} finally {
			setIsConfirming(false);
		}
	};

	const handleReject = async () => {
		setIsRejecting(true);
		try {
			const res = await rejectPendingActionApiActionsActionIdRejectPost(actionId);
			if (res.status === 200) {
				setResolved("rejected");
				toast.success("Action rejected");
			}
		} catch {
			toast.error("Failed to reject action");
		} finally {
			setIsRejecting(false);
		}
	};

	if (resolved) {
		return (
			<div className="rounded border bg-muted/30 px-2 py-1 text-xs text-muted-foreground">
				Action {resolved}
			</div>
		);
	}

	return (
		<div className="flex items-center gap-2 rounded border border-yellow-300 bg-yellow-50 px-2 py-1.5">
			<span className="text-xs font-medium">Confirm action?</span>
			<Button
				variant="outline"
				size="sm"
				className="h-6 gap-1 px-2 text-xs"
				onClick={handleConfirm}
				disabled={isConfirming || isRejecting}
			>
				{isConfirming ? (
					<Loader2 className="h-3 w-3 animate-spin" />
				) : (
					<Check className="h-3 w-3" />
				)}
				Confirm
			</Button>
			<Button
				variant="ghost"
				size="sm"
				className="h-6 gap-1 px-2 text-xs"
				onClick={handleReject}
				disabled={isConfirming || isRejecting}
			>
				{isRejecting ? <Loader2 className="h-3 w-3 animate-spin" /> : <X className="h-3 w-3" />}
				Reject
			</Button>
		</div>
	);
}

function ChatMessageBubble({ message, boardId }: { message: ChatMessage; boardId: string }) {
	const isUser = message.role === "user";

	return (
		<div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
			<div
				className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
					isUser ? "bg-primary text-primary-foreground" : "bg-muted"
				}`}
			>
				<div className="whitespace-pre-wrap">{message.content}</div>
				{message.actions && message.actions.length > 0 && (
					<div className="mt-2 space-y-1">
						{message.actions.map((action, i) => (
							<ToolActionCard key={`${action.tool_name}-${i}`} action={action} />
						))}
					</div>
				)}
				{message.pendingActionId && (
					<div className="mt-2">
						<PendingActionCard actionId={message.pendingActionId} boardId={boardId} />
					</div>
				)}
			</div>
		</div>
	);
}

export function TaskChat({ taskId, boardId, initialPrompt }: TaskChatProps) {
	const { messages, isLoading, sendMessage } = useTaskChat(taskId, boardId);
	const [input, setInput] = useState("");
	const messagesEndRef = useRef<HTMLDivElement>(null);
	const lastPromptRef = useRef<string | null>(null);

	// Send initial prompt from action button clicks
	useEffect(() => {
		if (initialPrompt && initialPrompt !== lastPromptRef.current && !isLoading) {
			lastPromptRef.current = initialPrompt;
			sendMessage(initialPrompt);
		}
	}, [initialPrompt, isLoading, sendMessage]);
	const chatRef = useRef<{ sendMessage: (msg: string) => void }>({
		sendMessage: () => {},
	});

	// Expose sendMessage for external callers (action buttons)
	chatRef.current.sendMessage = useCallback(
		(msg: string) => {
			sendMessage(msg);
		},
		[sendMessage],
	);

	// Auto-scroll to bottom on new messages - scroll after each render when messages change
	const prevMessageCount = useRef(0);
	useEffect(() => {
		if (messages.length !== prevMessageCount.current) {
			prevMessageCount.current = messages.length;
			messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
		}
	});

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		const trimmed = input.trim();
		if (!trimmed || isLoading) return;
		setInput("");
		sendMessage(trimmed);
	};

	return (
		<div>
			<Label className="flex items-center gap-1.5">
				<MessageSquare className="h-3.5 w-3.5" />
				AI Chat
			</Label>

			<div className="mt-2 rounded-md border">
				{/* Messages area */}
				<div className="max-h-80 min-h-[120px] overflow-y-auto p-3 space-y-3">
					{messages.length === 0 && !isLoading && (
						<p className="text-center text-xs text-muted-foreground py-6">
							Ask AI anything about this task, or click an action above.
						</p>
					)}
					{messages.map((msg) => (
						<ChatMessageBubble key={msg.id} message={msg} boardId={boardId} />
					))}
					{isLoading && (
						<div className="flex justify-start">
							<div className="rounded-lg bg-muted px-3 py-2">
								<Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
							</div>
						</div>
					)}
					<div ref={messagesEndRef} />
				</div>

				{/* Input */}
				<form onSubmit={handleSubmit} className="flex border-t p-2 gap-2">
					<Input
						value={input}
						onChange={(e) => setInput(e.target.value)}
						placeholder="Ask AI..."
						className="h-8 text-sm"
						disabled={isLoading}
					/>
					<Button
						type="submit"
						size="sm"
						disabled={!input.trim() || isLoading}
						className="h-8 px-2"
					>
						<Send className="h-3.5 w-3.5" />
					</Button>
				</form>
			</div>
		</div>
	);
}

// Export ref type for external use
export type TaskChatRef = {
	sendMessage: (message: string) => void;
};
