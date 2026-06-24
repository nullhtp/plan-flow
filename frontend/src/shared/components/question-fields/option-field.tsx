import { useTranslation } from "react-i18next";
import type { QuestionSchema } from "@/api/generated/model";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { cn } from "@/lib/utils";

const OTHER_PREFIX = "other: ";
const OTHER_VALUE = "__other__";

/**
 * Single-select option field rendered as radio buttons + an "Other" option with text input.
 * Used for `select`, `text`, and `number` question types.
 * Selecting a radio deselects all others; choosing "Other" enables the text field.
 */
export function OptionField({
	question,
	value,
	otherText,
	onSelectOption,
	onOtherChange,
	disabled,
	compact,
}: {
	question: QuestionSchema;
	value: string;
	otherText: string;
	onSelectOption: (option: string) => void;
	onOtherChange: (text: string) => void;
	disabled: boolean;
	compact?: boolean;
}) {
	const { t } = useTranslation("common");
	const options = question.options ?? [];
	const allowOther = question.allow_other !== false;
	const isOtherActive =
		value.startsWith(OTHER_PREFIX) || (otherText !== "" && !options.includes(value));

	const radioValue = isOtherActive ? OTHER_VALUE : value;

	return (
		<RadioGroup
			value={radioValue}
			onValueChange={(val) => {
				if (val === OTHER_VALUE) {
					// Switch to "other" mode — keep existing otherText
					onOtherChange(otherText);
				} else {
					onSelectOption(val);
				}
			}}
			disabled={disabled}
			className={cn("space-y-2", compact && "space-y-1.5")}
		>
			{options.map((option: any) => (
				<div key={option} className="flex items-center gap-2">
					<RadioGroupItem
						value={option}
						id={`${question.id}-${option}`}
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
					<RadioGroupItem
						value={OTHER_VALUE}
						id={`${question.id}-other`}
						className={cn(compact && "size-3.5")}
					/>
					<Input
						placeholder={t("fields.other")}
						value={otherText}
						onChange={(e) => onOtherChange(e.target.value)}
						onFocus={() => {
							if (!isOtherActive) {
								onOtherChange(otherText);
							}
						}}
						disabled={disabled}
						className={cn("flex-1", compact && "h-7 text-xs")}
					/>
				</div>
			)}
		</RadioGroup>
	);
}

/**
 * Extract the selected option or "other" text from a serialized answer value.
 */
export function parseOptionValue(
	value: string | undefined,
	options: string[],
): { selectedOption: string; otherText: string } {
	if (!value) return { selectedOption: "", otherText: "" };
	if (value.startsWith(OTHER_PREFIX)) {
		return { selectedOption: "", otherText: value.slice(OTHER_PREFIX.length) };
	}
	if (options.includes(value)) {
		return { selectedOption: value, otherText: "" };
	}
	// Legacy: plain text that isn't an option — treat as "other"
	return { selectedOption: "", otherText: value };
}

/**
 * Serialize an option selection or "other" text into a single answer value.
 */
export function serializeOptionValue(selectedOption: string, otherText: string): string {
	if (selectedOption) return selectedOption;
	if (otherText) return `${OTHER_PREFIX}${otherText}`;
	return "";
}

export { OTHER_PREFIX };
