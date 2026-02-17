import { CalendarDays, MapPin } from "lucide-react";
import type { UserMetaResponse } from "../types";

interface BoardMetaInfoProps {
	userMeta: UserMetaResponse;
}

function formatDate(isoDatetime: string): string {
	try {
		const date = new Date(isoDatetime);
		return date.toLocaleDateString(undefined, {
			year: "numeric",
			month: "short",
			day: "numeric",
		});
	} catch {
		return isoDatetime.slice(0, 10);
	}
}

function formatLocation(
	location: { city: string | null; country: string | null } | null,
): string | null {
	if (!location) return null;
	const parts = [location.city, location.country].filter(Boolean);
	return parts.length > 0 ? parts.join(", ") : null;
}

/**
 * Displays board generation context (date + location).
 * Non-intrusive informational element shown on the board detail page.
 */
export function BoardMetaInfo({ userMeta }: BoardMetaInfoProps) {
	const formattedDate = userMeta.current_datetime ? formatDate(userMeta.current_datetime) : null;
	const locationText = formatLocation(userMeta.location);

	if (!formattedDate && !locationText) return null;

	return (
		<div className="flex items-center gap-3 text-xs text-muted-foreground">
			{formattedDate && (
				<span className="flex items-center gap-1">
					<CalendarDays className="h-3 w-3" />
					Generated on {formattedDate}
				</span>
			)}
			{locationText && (
				<span className="flex items-center gap-1">
					<MapPin className="h-3 w-3" />
					{locationText}
				</span>
			)}
		</div>
	);
}
