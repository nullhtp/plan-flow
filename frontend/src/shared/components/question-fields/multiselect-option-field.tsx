import { useTranslation } from "react-i18next";
import type { QuestionSchema } from "@/api/generated/model";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

const OTHER_PREFIX = "other: ";

/**
 * Multi-select option field rendered as checkboxes + an "Other" option with text input.
 * Used for `multiselect` question types.
 * Options and "Other" text are additive — both contribute to the answer array.
 */
export function MultiselectOptionField({
	question,
	selectedOptions,
	otherText,
	onToggleOption,
	onOtherChange,
	disabled,
	compact,
}: {
	question: QuestionSchema;
	selectedOptions: string[];
	otherText: string;
	onToggleOption: (option: string) => void;
	onOtherChange: (text: string) => void;
	disabled: boolean;
	compact?: boolean;
}) {
	const { t } = useTranslation("common");
	const options = question.options ?? [];
	const allowOther = question.allow_other !== false;
	const hasOtherText = otherText.trim() !== "";

	return (
		<div className={cn("space-y-2", compact && "space-y-1.5")}>
			{options.map((option: any) => (
				<div key={option} className="flex items-center gap-2">
					<Checkbox
						id={`${question.id}-${option}`}
						checked={selectedOptions.includes(option)}
						onCheckedChange={() => onToggleOption(option)}
						disabled={disabled}
						className={cn(compact && "size-3.5")}
					/>
					<Label
						htmlFor={`${question.id}-${option}`}
						className={cn("cursor-pointer font-normal", compact ? "text-xs" : "text-sm")}
					>
						{option}
					</Label>
				</div>
			))}
			{allowOther && (
				<div className="flex items-center gap-2">
					<Checkbox
						id={`${question.id}-other`}
						checked={hasOtherText}
						onCheckedChange={(checked) => {
							if (!checked) {
								onOtherChange("");
							}
						}}
						disabled={disabled}
						className={cn(compact && "size-3.5")}
					/>
					<Input
						placeholder={t("fields.other")}
						value={otherText}
						onChange={(e) => onOtherChange(e.target.value)}
						disabled={disabled}
						className={cn("flex-1", compact && "h-7 text-xs")}
					/>
				</div>
			)}
		</div>
	);
}

/**
 * Parse a serialized multiselect answer value into selected options and "other" text.
 */
export function parseMultiselectValue(
	value: string[] | undefined,
	options: string[],
): { selectedOptions: string[]; otherText: string } {
	if (!value || !Array.isArray(value)) return { selectedOptions: [], otherText: "" };

	const selected: string[] = [];
	let other = "";

	for (const item of value) {
		if (item.startsWith(OTHER_PREFIX)) {
			other = item.slice(OTHER_PREFIX.length);
		} else if (options.includes(item)) {
			selected.push(item);
		} else {
			// Legacy: unknown item — treat as selected anyway
			selected.push(item);
		}
	}

	return { selectedOptions: selected, otherText: other };
}

/**
 * Serialize selected options and "other" text into a multiselect answer array.
 */
export function serializeMultiselectValue(selectedOptions: string[], otherText: string): string[] {
	const result = [...selectedOptions];
	if (otherText.trim()) {
		result.push(`${OTHER_PREFIX}${otherText.trim()}`);
	}
	return result;
}
