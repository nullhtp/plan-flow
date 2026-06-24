import { useNavigate } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TemplateListItemResponse } from "../types";

interface TemplateCardProps {
	template: TemplateListItemResponse;
	/**
	 * Override the default click behavior (open the template editor). In Simple
	 * mode this is used to start the create-board-from-template flow directly.
	 */
	onSelect?: (template: TemplateListItemResponse) => void;
}

export function TemplateCard({ template, onSelect }: TemplateCardProps) {
	const navigate = useNavigate();

	const activate = () => {
		if (onSelect) {
			onSelect(template);
			return;
		}
		navigate({ to: "/templates/$templateId", params: { templateId: template.id } });
	};

	return (
		<Card
			className="cursor-pointer transition-shadow hover:shadow-md"
			onClick={activate}
			role="button"
			tabIndex={0}
			onKeyDown={(e) => {
				if (e.key === "Enter") activate();
			}}
		>
			<CardHeader className="pb-2">
				<CardTitle className="text-base">{template.title}</CardTitle>
				{template.category && (
					<span className="inline-block rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
						{template.category.name}
					</span>
				)}
			</CardHeader>
			<CardContent>
				{template.description && (
					<p className="mb-2 line-clamp-2 text-sm text-muted-foreground">{template.description}</p>
				)}
				<div className="flex items-center justify-between text-xs text-muted-foreground">
					<span>{template.task_count} tasks</span>
					<span>by {template.creator.email}</span>
				</div>
			</CardContent>
		</Card>
	);
}
