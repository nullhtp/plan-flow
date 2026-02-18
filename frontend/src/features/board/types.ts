// Board and task types for DAG-based board UI
// Defined locally — will be replaced by Orval-generated types after codegen

export interface SubtaskResponse {
	id: string;
	title: string;
	completed: boolean;
	position: string;
	action_label: string | null;
	action_icon: string | null;
	action_prompt: string | null;
	created_at: string;
}

export interface EdgeResponse {
	source: string; // dependency_task_id (prerequisite)
	target: string; // dependent_task_id (blocked task)
}

export interface SubBoardProgressResponse {
	task_count: number;
	completed_task_count: number;
}

export interface TaskResponse {
	id: string;
	title: string;
	description: string;
	status: string; // "not_started" | "in_progress" | "done"
	is_goal_node: boolean;
	due_date: string | null;
	priority: string | null;
	estimated_minutes: number | null;
	subtasks: SubtaskResponse[];
	dependency_ids: string[];
	dependent_ids: string[];
	is_locked: boolean;
	sub_board_id: string | null;
	sub_board_progress: SubBoardProgressResponse | null;
	created_at: string;
}

export interface UserLocationMeta {
	city: string | null;
	country: string | null;
}

export interface UserMetaResponse {
	timezone: string;
	locale: string;
	current_datetime: string;
	location: UserLocationMeta | null;
	device_type: string;
}

export interface ParentBoardResponse {
	id: string;
	title: string;
}

export interface BoardResponse {
	id: string;
	goal_id: string | null;
	title: string;
	tasks: TaskResponse[];
	edges: EdgeResponse[];
	is_completed: boolean;
	user_meta: UserMetaResponse | null;
	parent_task_id: string | null;
	parent_board: ParentBoardResponse | null;
	created_at: string;
}

export interface BoardListResponse {
	id: string;
	goal_id: string;
	title: string;
	goal_title: string;
	task_count: number;
	completed_task_count: number;
	created_at: string;
}
