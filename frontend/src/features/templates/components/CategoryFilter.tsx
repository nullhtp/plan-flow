import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import type { TemplateCategoryResponse } from "../types";

interface CategoryFilterProps {
	categories: TemplateCategoryResponse[];
	selected: string | null;
	onSelect: (slug: string | null) => void;
}

export function CategoryFilter({ categories, selected, onSelect }: CategoryFilterProps) {
	const { t } = useTranslation("templates");
	return (
		<div className="flex flex-wrap gap-2">
			<Button
				variant={selected === null ? "default" : "outline"}
				size="sm"
				onClick={() => onSelect(null)}
			>
				{t("categoryFilter.all")}
			</Button>
			{categories.map((cat) => (
				<Button
					key={cat.id}
					variant={selected === cat.slug ? "default" : "outline"}
					size="sm"
					onClick={() => onSelect(cat.slug)}
				>
					{cat.name}
					{cat.template_count > 0 && (
						<span className="ml-1 text-xs opacity-60">({cat.template_count})</span>
					)}
				</Button>
			))}
		</div>
	);
}
