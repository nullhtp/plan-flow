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

// ── Template Generation Types ────────────────────────

export interface ContentExtractionResponse {
	content: string;
	source_type: string;
	source_name: string;
	char_count: number;
	truncated: boolean;
}

export interface GenerateTemplateSubtaskResponse {
	title: string;
}

export interface GenerateTemplateTaskResponse {
	id: string;
	title: string;
	description: string;
	is_goal_node: boolean;
	depends_on: string[];
	subtasks: GenerateTemplateSubtaskResponse[];
}

export interface GenerateTemplateResponse {
	suggested_title: string;
	suggested_description: string;
	suggested_category_slug: string;
	tasks: GenerateTemplateTaskResponse[];
	task_count: number;
}

export interface SaveGeneratedTemplateRequest {
	title: string;
	description?: string | null;
	category_id?: string | null;
	visibility?: string;
	create_board?: boolean;
	tasks: {
		id: string;
		title: string;
		description: string;
		is_goal_node: boolean;
		depends_on: string[];
		subtasks: { title: string }[];
		priority?: string | null;
		estimated_minutes?: number | null;
	}[];
}

// ── Template Classification & Question Types ─────────

export interface TemplateClassificationData {
	domain: string;
	complexity: number;
	confidence: number;
	dimensions: string[];
	suggested_title: string;
	language: string;
}

export interface TemplateQuestionSchema {
	id: string;
	text: string;
	type: string;
	options: string[];
	rationale: string;
	required: boolean;
	allow_other: boolean;
}

export interface TemplateReadinessSchema {
	score: number;
	covered_dimensions: string[];
	uncovered_dimensions: string[];
	summary: string;
}

export interface TemplateClassifyRequest {
	input_type: "describe" | "text" | "file" | "url";
	content: string;
	title?: string;
}

export interface TemplateClassifyResponse {
	classification: TemplateClassificationData;
	questions: TemplateQuestionSchema[];
	readiness: TemplateReadinessSchema | null;
	is_rejected: boolean;
	rejection_reason: string | null;
	refinement_suggestions: string[];
}

export interface TemplateAnswerSubmission {
	answers: Record<string, string>;
	round: number;
	classification: TemplateClassificationData;
	previous_rounds: Record<string, unknown>[];
	content: string | null;
	raw_input: string;
}

export interface TemplateAnswerResponse {
	next_questions: TemplateQuestionSchema[];
	readiness: TemplateReadinessSchema | null;
	next_round: number;
	is_ready: boolean;
}

export interface TemplateGenerateStreamRequest {
	raw_input: string;
	classification: TemplateClassificationData;
	qa_rounds: Record<string, unknown>[];
	content: string | null;
	title: string | null;
}
