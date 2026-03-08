import type { EdgeResponse, TaskResponse } from "../types";

/**
 * Determines whether a task should be visible in Focus view.
 *
 * Visible tasks:
 *  - All `done` tasks
 *  - All `in_progress` tasks
 *  - `not_started` tasks that are NOT locked (all dependencies met)
 *  - The goal node (always visible regardless of status/lock)
 *
 * Hidden tasks:
 *  - `not_started` tasks that ARE locked (except goal node)
 */
function isTaskVisibleInFocus(task: TaskResponse): boolean {
	if (task.is_goal_node) return true;
	if (task.status === "done") return true;
	if (task.status === "in_progress") return true;
	if (task.status === "not_started" && !task.is_locked) return true;
	return false;
}

/**
 * Filters a board's tasks and edges for Focus view.
 *
 * Returns only the visible tasks and edges where both source and target
 * are visible. The full board data is unchanged — this produces a
 * filtered subset for layout computation.
 */
export function filterBoardForFocusView(
	tasks: TaskResponse[],
	edges: EdgeResponse[],
): { tasks: TaskResponse[]; edges: EdgeResponse[] } {
	const visibleTasks = tasks.filter(isTaskVisibleInFocus);
	const visibleTaskIds = new Set(visibleTasks.map((t) => t.id));

	const visibleEdges = edges.filter(
		(edge) => visibleTaskIds.has(edge.source) && visibleTaskIds.has(edge.target),
	);

	return { tasks: visibleTasks, edges: visibleEdges };
}

/**
 * Checks whether a specific task would be hidden in Focus view.
 */
export function isTaskHiddenInFocus(task: TaskResponse): boolean {
	return !isTaskVisibleInFocus(task);
}
