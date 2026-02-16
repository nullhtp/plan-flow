import { useNavigate } from "@tanstack/react-router";
import type { BoardResponse, QuestionSchema } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useGenerateBoard } from "@/features/goals/hooks/use-goals";

interface QAPair {
	question: QuestionSchema;
	answer: string | string[] | number;
}

interface GoalSummaryProps {
	goalId: string;
	title: string;
	originalInput: string;
	qaPairs: QAPair[];
}

export function GoalSummary({ goalId, title, originalInput, qaPairs }: GoalSummaryProps) {
	const generateBoard = useGenerateBoard();
	const navigate = useNavigate();

	function formatAnswer(answer: string | string[] | number): string {
		if (Array.isArray(answer)) return answer.join(", ");
		return String(answer);
	}

	function handleGenerateBoard() {
		generateBoard.mutate(
			{ goalId },
			{
				onSuccess: (response) => {
					if (response.status === 201) {
						const board = response.data as BoardResponse;
						navigate({ to: "/boards/$boardId", params: { boardId: board.id } });
					}
				},
			},
		);
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
					{generateBoard.isError && (
						<p className="mb-2 text-center text-sm text-destructive">
							Board generation failed. Please try again.
						</p>
					)}
					<Button
						className="w-full"
						onClick={handleGenerateBoard}
						disabled={generateBoard.isPending}
					>
						{generateBoard.isPending ? (
							<span className="flex items-center gap-2">
								<span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
								Generating your board...
							</span>
						) : generateBoard.isError ? (
							"Try Again"
						) : (
							"Generate Board"
						)}
					</Button>
				</div>
			</CardContent>
		</Card>
	);
}
