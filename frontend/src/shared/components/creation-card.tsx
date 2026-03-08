import { useNavigate } from "@tanstack/react-router";
import { Plus } from "lucide-react";

interface CreationCardProps {
	label: string;
	href: string;
}

export function CreationCard({ label, href }: CreationCardProps) {
	const navigate = useNavigate();

	return (
		<button
			type="button"
			className="flex min-h-[140px] cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-muted-foreground/25 bg-background transition-colors hover:border-muted-foreground/50 hover:bg-muted/50"
			onClick={() => navigate({ to: href })}
		>
			<Plus className="h-8 w-8 text-muted-foreground/50" />
			<span className="text-sm font-medium text-muted-foreground">{label}</span>
		</button>
	);
}
