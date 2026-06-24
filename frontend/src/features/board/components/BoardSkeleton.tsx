import { useTranslation } from "react-i18next";

export function BoardSkeleton() {
	const { t } = useTranslation("board");
	return (
		<div className="flex h-full items-center justify-center">
			<div className="flex flex-col items-center gap-3">
				<div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-primary" />
				<p className="text-sm text-muted-foreground">{t("boardSkeleton.loading")}</p>
			</div>
		</div>
	);
}
