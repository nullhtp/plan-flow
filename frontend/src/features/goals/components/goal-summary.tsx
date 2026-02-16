import type { QuestionSchema } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface QAPair {
	question: QuestionSchema;
	answer: string | string[] | number;
}

interface GoalSummaryProps {
	title: string;
	originalInput: string;
	qaPairs: QAPair[];
}

export function GoalSummary({ title, originalInput, qaPairs }: GoalSummaryProps) {
	function formatAnswer(answer: string | string[] | number): string {
		if (Array.isArray(answer)) return answer.join(", ");
		return String(answer);
	}

	return (
		<Card className="w-full max-w-2xl">
			<CardHeader>
				<CardTitle className="text-2xl">{title}</CardTitle>
				<p className="text-sm text-muted-foreground">{originalInput}</p>
			</CardHeader>
			<CardContent className="space-y-6">
				<div className="space-y-4">
					<h3 className="text-sm font-medium">Your answers</h3>
					{qaPairs.map(({ question, answer }) => (
						<div key={question.id} className="space-y-1 rounded-lg border p-3">
							<p className="text-sm font-medium">{question.text}</p>
							<p className="text-sm text-muted-foreground">{formatAnswer(answer)}</p>
						</div>
					))}
				</div>
				<div className="relative">
					<Button className="w-full" disabled>
						Generate Board
					</Button>
					<p className="mt-2 text-center text-xs text-muted-foreground">
						Board generation coming soon
					</p>
				</div>
			</CardContent>
		</Card>
	);
}
