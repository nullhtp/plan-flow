import type {
	BoardListResponse,
	BoardResponse,
	ColumnResponse,
	SubtaskResponse,
	TaskResponse,
} from "@/api/generated/model";

// Re-export API types for convenience
export type { BoardResponse, BoardListResponse, ColumnResponse, TaskResponse, SubtaskResponse };

// DnD types
export type DragItemType = "column" | "task";

export interface DragData {
	type: DragItemType;
	id: string;
	columnId?: string; // for tasks: which column they belong to
}
