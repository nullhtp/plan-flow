export interface TemplateCategoryResponse {
	id: string;
	name: string;
	slug: string;
	description: string | null;
	icon: string | null;
	template_count: number;
}

export interface TemplateCreatorResponse {
	id: string;
	email: string;
}

export interface TemplateCategoryBrief {
	id: string;
	name: string;
	slug: string;
}

export interface TemplateSubtaskResponse {
	id: string;
	title: string;
	position: string;
}

export interface TemplateEdgeResponse {
	source: string;
	target: string;
}

export interface TemplateTaskResponse {
	id: string;
	title: string;
	description: string;
	is_goal_node: boolean;
	priority: string | null;
	estimated_minutes: number | null;
	subtasks: TemplateSubtaskResponse[];
}

export interface TemplateListItemResponse {
	id: string;
	title: string;
	description: string | null;
	visibility: string;
	category: TemplateCategoryBrief | null;
	task_count: number;
	creator: TemplateCreatorResponse;
	created_at: string;
}

export interface TemplateListResponse {
	items: TemplateListItemResponse[];
	total: number;
	page: number;
	per_page: number;
	total_pages: number;
}

export interface TemplateDetailResponse {
	id: string;
	title: string;
	description: string | null;
	visibility: string;
	category: TemplateCategoryBrief | null;
	task_count: number;
	creator: TemplateCreatorResponse;
	tasks: TemplateTaskResponse[];
	edges: TemplateEdgeResponse[];
	created_at: string;
}

export interface CreateBoardFromTemplateResponse {
	board_id: string;
	goal_id: string;
	title: string;
}

export interface TemplateCreateRequest {
	board_id: string;
	title: string;
	description?: string | null;
	category_id?: string | null;
	visibility?: string;
}

export interface TemplateUpdateRequest {
	title?: string | null;
	description?: string | null;
	category_id?: string | null;
	visibility?: string | null;
}

export interface CreateBoardFromTemplateRequest {
	title?: string | null;
}
