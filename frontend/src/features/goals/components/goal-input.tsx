import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const EXAMPLE_GOAL_KEYS = ["move", "mvp", "japanese", "marathon", "trip", "novel"] as const;

interface GoalInputProps {
	onSubmit: (input: string) => void;
	isPending: boolean;
	defaultValue?: string;
}

export function GoalInput({ onSubmit, isPending, defaultValue = "" }: GoalInputProps) {
	const { t } = useTranslation("goals");
	const [input, setInput] = useState(defaultValue);

	function handleSubmit(e: FormEvent) {
		e.preventDefault();
		const trimmed = input.trim();
		if (!trimmed) return;
		onSubmit(trimmed);
	}

	return (
		<Card className="w-full max-w-2xl">
			<CardHeader>
				<CardTitle className="text-2xl">{t("goalInput.title")}</CardTitle>
				<CardDescription>{t("goalInput.description")}</CardDescription>
			</CardHeader>
			<form onSubmit={handleSubmit}>
				<CardContent className="space-y-6">
					<div className="space-y-2">
						<Label htmlFor="goal-input">{t("goalInput.goalLabel")}</Label>
						<Input
							id="goal-input"
							placeholder={t("goalInput.placeholder")}
							value={input}
							onChange={(e) => setInput(e.target.value)}
							disabled={isPending}
							maxLength={2000}
						/>
					</div>
					<Button type="submit" className="w-full" disabled={isPending || !input.trim()}>
						{isPending ? t("goalInput.submitting") : t("goalInput.submit")}
					</Button>
					<div className="space-y-3">
						<p className="text-sm text-muted-foreground">{t("goalInput.examplesLabel")}</p>
						<div className="flex flex-wrap gap-2">
							{EXAMPLE_GOAL_KEYS.map((key) => {
								const example = t(`goalInput.examples.${key}`);
								return (
									<button
										key={key}
										type="button"
										className="rounded-full border px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:border-primary hover:text-primary"
										onClick={() => setInput(example)}
										disabled={isPending}
									>
										{example}
									</button>
								);
							})}
						</div>
					</div>
				</CardContent>
			</form>
		</Card>
	);
}
