import { useNavigate, useSearch } from "@tanstack/react-router";
import { useCallback } from "react";

export function useTaskDetailPanel() {
	const navigate = useNavigate();
	// Read the 'task' search parameter
	const search = useSearch({ strict: false }) as { task?: string };
	const selectedTaskId = search.task ?? null;

	const openTask = useCallback(
		(taskId: string) => {
			const url = new URL(window.location.href);
			url.searchParams.set("task", taskId);
			window.history.pushState({}, "", url.toString());
			// Force router to pick up the new search params
			navigate({ to: ".", search: { task: taskId } as never });
		},
		[navigate],
	);

	const closeTask = useCallback(() => {
		const url = new URL(window.location.href);
		url.searchParams.delete("task");
		window.history.pushState({}, "", url.toString());
		navigate({ to: ".", search: {} as never });
	}, [navigate]);

	return { selectedTaskId, openTask, closeTask };
}
