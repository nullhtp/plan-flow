import type { ReactNode } from "react";
import type { QuestionSchema } from "@/api/generated/model";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

/**
 * Wrapper around any question field that adds label, required indicator, and rationale.
 */
export function QuestionFieldWrapper({
	question,
	compact,
	children,
}: {
	question: QuestionSchema;
	compact?: boolean;
	children: ReactNode;
}) {
	return (
		<div className={cn("space-y-2", compact && "space-y-1.5")}>
			<Label htmlFor={question.id} className={cn(compact && "text-sm")}>
				{question.text}
				{question.required && <span className="ml-1 text-destructive">*</span>}
			</Label>
			{children}
			{question.rationale && <p className="text-xs text-muted-foreground">{question.rationale}</p>}
		</div>
	);
}
