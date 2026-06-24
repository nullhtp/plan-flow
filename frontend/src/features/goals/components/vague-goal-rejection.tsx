import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface VagueGoalRejectionProps {
	reason: string;
	suggestions: string[];
	onSuggestionClick: (suggestion: string) => void;
	onTryAgain: () => void;
}

export function VagueGoalRejection({
	reason,
	suggestions,
	onSuggestionClick,
	onTryAgain,
}: VagueGoalRejectionProps) {
	const { t } = useTranslation("goals");
	return (
		<Card className="w-full max-w-2xl">
			<CardHeader>
				<CardTitle className="text-2xl">{t("vagueGoalRejection.title")}</CardTitle>
				<CardDescription>{reason}</CardDescription>
			</CardHeader>
			<CardContent className="space-y-6">
				{suggestions.length > 0 && (
					<div className="space-y-3">
						<p className="text-sm font-medium">{t("vagueGoalRejection.suggestionsLabel")}</p>
						<div className="space-y-2">
							{suggestions.map((suggestion) => (
								<button
									key={suggestion}
									type="button"
									className="block w-full rounded-lg border p-3 text-left text-sm transition-colors hover:border-primary hover:bg-accent"
									onClick={() => onSuggestionClick(suggestion)}
								>
									{suggestion}
								</button>
							))}
						</div>
					</div>
				)}
				<Button variant="outline" className="w-full" onClick={onTryAgain}>
					{t("vagueGoalRejection.tryAgain")}
				</Button>
			</CardContent>
		</Card>
	);
}
