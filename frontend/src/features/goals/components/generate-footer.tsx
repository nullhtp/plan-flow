import type { ReadinessSchema } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { ReadinessIndicator } from "./readiness-indicator";

interface GenerateFooterProps {
	readiness: ReadinessSchema | null;
	onGenerate: () => void;
	isPending: boolean;
}

export function GenerateFooter({ readiness, onGenerate, isPending }: GenerateFooterProps) {
	return (
		<div className="fixed inset-x-0 top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
			<div className="mx-auto max-w-2xl px-4 py-3">
				<div className="flex items-center justify-between gap-4">
					{readiness ? <ReadinessIndicator readiness={readiness} /> : <div className="flex-1" />}
					<Button size="lg" onClick={onGenerate} disabled={isPending} className="flex-shrink-0">
						{isPending ? "Generating..." : "Generate Board"}
					</Button>
				</div>
				{readiness?.summary && (
					<p className="mt-1.5 text-xs leading-normal text-muted-foreground">{readiness.summary}</p>
				)}
			</div>
		</div>
	);
}
