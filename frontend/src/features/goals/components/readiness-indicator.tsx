import type { ReadinessSchema } from "@/api/generated/model";

interface ReadinessIndicatorProps {
	readiness: ReadinessSchema;
}

function getColor(score: number): { ring: string; text: string } {
	if (score >= 0.7) return { ring: "stroke-green-500", text: "text-green-600" };
	if (score >= 0.4) return { ring: "stroke-yellow-500", text: "text-yellow-600" };
	return { ring: "stroke-orange-500", text: "text-orange-600" };
}

export function ReadinessIndicator({ readiness }: ReadinessIndicatorProps) {
	const pct = Math.round(readiness.score * 100);
	const color = getColor(readiness.score);

	const radius = 18;
	const circumference = 2 * Math.PI * radius;
	const offset = circumference - readiness.score * circumference;

	return (
		<div className="flex items-center gap-1.5">
			{/* Progress ring */}
			<div className="relative h-10 w-10 flex-shrink-0">
				<svg width="40" height="40" viewBox="0 0 40 40" className="-rotate-90" aria-hidden="true">
					<title>Readiness {pct}%</title>
					<circle
						cx="20"
						cy="20"
						r={radius}
						fill="none"
						stroke="currentColor"
						strokeWidth="3"
						className="text-muted/30"
					/>
					<circle
						cx="20"
						cy="20"
						r={radius}
						fill="none"
						strokeWidth="3"
						strokeLinecap="round"
						strokeDasharray={circumference}
						strokeDashoffset={offset}
						className={`${color.ring} transition-all duration-500`}
					/>
				</svg>
				<span
					className={`absolute inset-0 flex items-center justify-center text-[11px] font-semibold ${color.text}`}
				>
					{pct}%
				</span>
			</div>
			<span className={`text-xs font-medium ${color.text}`}>Ready</span>
		</div>
	);
}
