import { useCallback, useRef, useState } from "react";
import { suggestTaskActionsApiTasksTaskIdActionsSuggestPost } from "@/api/generated/ai/ai";
import type { ActionSuggestion } from "@/api/generated/model";

interface UseActionSuggestionsReturn {
	actions: ActionSuggestion[];
	isLoading: boolean;
	error: string | null;
	fetchSuggestions: () => Promise<void>;
}

export function useActionSuggestions(taskId: string): UseActionSuggestionsReturn {
	const [actions, setActions] = useState<ActionSuggestion[]>([]);
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const inflightRef = useRef(false);

	const fetchSuggestions = useCallback(async () => {
		if (inflightRef.current) return;
		inflightRef.current = true;
		setIsLoading(true);
		setError(null);
		try {
			const response = await suggestTaskActionsApiTasksTaskIdActionsSuggestPost(taskId);
			if (response.status === 200) {
				setActions(response.data.actions);
			} else {
				setError("Failed to load suggestions");
			}
		} catch {
			setError("Failed to load suggestions");
		} finally {
			setIsLoading(false);
			inflightRef.current = false;
		}
	}, [taskId]);

	return { actions, isLoading, error, fetchSuggestions };
}
