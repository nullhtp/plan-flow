import { useNavigate, useSearch } from "@tanstack/react-router";
import { useCallback } from "react";

export function useTaskDetailPanel() {
	const navigate = useNavigate();
	// Read search parameters (preserving all existing params like 'view')
	const search = useSearch({ strict: false }) as Record<string, unknown>;
	const selectedTaskId = (search.task as string) ?? null;

	const openTask = useCallback(
		(taskId: string) => {
			navigate({ to: ".", search: { ...search, task: taskId } as never });
		},
		[navigate, search],
	);

	const closeTask = useCallback(() => {
		const { task: _, ...rest } = search;
		navigate({ to: ".", search: rest as never });
	}, [navigate, search]);

	return { selectedTaskId, openTask, closeTask };
}
