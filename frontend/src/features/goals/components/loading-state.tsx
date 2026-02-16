import { Card, CardContent } from "@/components/ui/card";

interface LoadingStateProps {
	message?: string;
}

export function LoadingState({ message = "Understanding your goal..." }: LoadingStateProps) {
	return (
		<Card className="w-full max-w-2xl">
			<CardContent className="flex flex-col items-center gap-4 py-12">
				<div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-primary" />
				<p className="text-sm text-muted-foreground">{message}</p>
			</CardContent>
		</Card>
	);
}
