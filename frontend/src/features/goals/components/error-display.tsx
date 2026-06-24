import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface ErrorDisplayProps {
	message?: string;
	onRetry: () => void;
	isRetrying?: boolean;
}

export function ErrorDisplay({ message, onRetry, isRetrying = false }: ErrorDisplayProps) {
	const { t } = useTranslation("goals");
	return (
		<Card className="w-full max-w-2xl">
			<CardContent className="flex flex-col items-center gap-4 py-12">
				<div className="rounded-full bg-destructive/10 p-3">
					<svg
						className="h-6 w-6 text-destructive"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						role="img"
						aria-label={t("errorDisplay.iconLabel")}
					>
						<title>{t("errorDisplay.iconLabel")}</title>
						<path
							strokeLinecap="round"
							strokeLinejoin="round"
							strokeWidth={2}
							d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
						/>
					</svg>
				</div>
				<p className="text-center text-sm text-muted-foreground">
					{message ?? t("errorDisplay.defaultMessage")}
				</p>
				<Button onClick={onRetry} disabled={isRetrying}>
					{isRetrying ? t("errorDisplay.retrying") : t("errorDisplay.tryAgain")}
				</Button>
			</CardContent>
		</Card>
	);
}
