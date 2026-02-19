import { useNavigate } from "@tanstack/react-router";
import type { QuestionSchema } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useBoardListData } from "@/features/board/hooks/use-board-list";

interface QAPair {
	question: QuestionSchema;
	answer: string | string[] | number;
}

interface GoalSummaryProps {
	goalId: string;
	title: string;
	originalInput: string;
	qaPairs: QAPair[];
	onGenerateBoard: () => void;
}

export function GoalSummary({
	goalId,
	title,
	originalInput,
	qaPairs,
	onGenerateBoard,
}: GoalSummaryProps) {
	const navigate = useNavigate();
	const boards = useBoardListData();

	function formatAnswer(answer: string | string[] | number): string {
		if (Array.isArray(answer)) return answer.join(", ");
		return String(answer);
	}

	function handleGenerateBoard() {
		// Check if a board already exists for this goal
		const existingBoard = boards.find((b) => b.goal_id === goalId);
		if (existingBoard) {
			navigate({ to: "/boards/$boardId", params: { boardId: existingBoard.id } });
			return;
		}

		onGenerateBoard();
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
				<Button className="w-full" onClick={handleGenerateBoard}>
					Generate Board
				</Button>
			</CardContent>
		</Card>
	);
}
