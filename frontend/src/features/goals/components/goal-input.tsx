import { type FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const EXAMPLE_GOALS = [
	"Move from Berlin to Lisbon within 6 months",
	"Launch an MVP for my SaaS product",
	"Learn conversational Japanese in 6 months",
	"Train for and complete a half marathon",
	"Plan a 2-week trip to Japan on a budget",
	"Write and self-publish a fiction novel",
];

interface GoalInputProps {
	onSubmit: (input: string) => void;
	isPending: boolean;
	defaultValue?: string;
}

export function GoalInput({ onSubmit, isPending, defaultValue = "" }: GoalInputProps) {
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
				<CardTitle className="text-2xl">What do you want to achieve?</CardTitle>
				<CardDescription>
					Describe your goal and our AI will help you break it down into an actionable plan.
				</CardDescription>
			</CardHeader>
			<form onSubmit={handleSubmit}>
				<CardContent className="space-y-6">
					<div className="space-y-2">
						<Label htmlFor="goal-input">Your goal</Label>
						<Input
							id="goal-input"
							placeholder="e.g., Move from Berlin to Lisbon within 6 months"
							value={input}
							onChange={(e) => setInput(e.target.value)}
							disabled={isPending}
							maxLength={2000}
						/>
					</div>
					<Button type="submit" className="w-full" disabled={isPending || !input.trim()}>
						{isPending ? "Understanding your goal..." : "Get started"}
					</Button>
					<div className="space-y-3">
						<p className="text-sm text-muted-foreground">Or try one of these examples:</p>
						<div className="flex flex-wrap gap-2">
							{EXAMPLE_GOALS.map((example) => (
								<button
									key={example}
									type="button"
									className="rounded-full border px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:border-primary hover:text-primary"
									onClick={() => setInput(example)}
									disabled={isPending}
								>
									{example}
								</button>
							))}
						</div>
					</div>
				</CardContent>
			</form>
		</Card>
	);
}
