import { useTranslation } from "react-i18next";
import type { ReadinessSchema } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { ReadinessIndicator } from "./readiness-indicator";

interface GenerateFooterProps {
	readiness: ReadinessSchema | null;
	onGenerate: () => void;
	isPending: boolean;
	/** Simple mode: hide the readiness gauge/summary and show a plain "Ready to generate" state. */
	simple?: boolean;
}

export function GenerateFooter({
	readiness,
	onGenerate,
	isPending,
	simple = false,
}: GenerateFooterProps) {
	const { t } = useTranslation("goals");
	return (
		<div className="fixed inset-x-0 top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
			<div className="mx-auto max-w-2xl px-4 py-3">
				<div className="flex items-center justify-between gap-4">
					{simple ? (
						<span className="text-sm font-medium text-muted-foreground">
							{t("generateFooter.readyToGenerate")}
						</span>
					) : readiness ? (
						<ReadinessIndicator readiness={readiness} />
					) : (
						<div className="flex-1" />
					)}
					<Button size="lg" onClick={onGenerate} disabled={isPending} className="flex-shrink-0">
						{isPending ? t("generateFooter.generating") : t("generateFooter.generateBoard")}
					</Button>
				</div>
				{!simple && readiness?.summary && (
					<p className="mt-1.5 text-xs leading-normal text-muted-foreground">{readiness.summary}</p>
				)}
			</div>
		</div>
	);
}
