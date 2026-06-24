import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { Brain } from "lucide-react";
import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import {
	getGetMemoryByIdApiMemoriesMemoryIdGetQueryKey,
	getMemoryByIdApiMemoriesMemoryIdGet,
} from "@/api/generated/memories/memories";
import type { MemoryResponse } from "@/api/generated/model";
import { Button } from "@/components/ui/button";

const CATEGORY_COLORS: Record<string, string> = {
	preference: "bg-blue-100 text-blue-700",
	fact: "bg-green-100 text-green-700",
	pattern: "bg-purple-100 text-purple-700",
	context: "bg-orange-100 text-orange-700",
};

interface MemoryBadgeProps {
	memoryId: string;
}

function MemoryBadge({ memoryId }: MemoryBadgeProps) {
	const { t } = useTranslation("memory");
	const navigate = useNavigate();
	const queryClient = useQueryClient();
	const [expanded, setExpanded] = useState(false);
	const [memory, setMemory] = useState<MemoryResponse | null>(null);
	const [isDeleted, setIsDeleted] = useState(false);
	const [loading, setLoading] = useState(false);

	const resolveMemory = useCallback(async () => {
		if (memory || isDeleted) return;

		// Try cache first
		const queryKey = getGetMemoryByIdApiMemoriesMemoryIdGetQueryKey(memoryId);
		const cached = queryClient.getQueryData(queryKey) as { data: MemoryResponse } | undefined;
		if (cached?.data) {
			setMemory(cached.data);
			return;
		}

		// Fetch on miss
		setLoading(true);
		try {
			const res = await getMemoryByIdApiMemoriesMemoryIdGet(memoryId);
			if (res.status === 200) {
				setMemory(res.data as MemoryResponse);
			}
		} catch {
			setIsDeleted(true);
		} finally {
			setLoading(false);
		}
	}, [memoryId, memory, isDeleted, queryClient]);

	const handleClick = () => {
		if (!expanded) {
			resolveMemory();
		}
		setExpanded((v) => !v);
	};

	if (isDeleted) {
		return (
			<span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground line-through">
				<Brain className="h-3 w-3" />
				{t("memoryRemoved")}
			</span>
		);
	}

	return (
		<span className="inline-block">
			<button
				type="button"
				onClick={handleClick}
				className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs transition-colors ${
					memory
						? (CATEGORY_COLORS[memory.category] ?? "bg-muted text-muted-foreground")
						: "bg-muted text-muted-foreground"
				} hover:opacity-80`}
			>
				<Brain className="h-3 w-3" />
				{memory ? (
					<span className="max-w-[120px] truncate">{memory.content}</span>
				) : loading ? (
					<span>{t("loading")}</span>
				) : (
					<span className="max-w-[80px] truncate">{t("memory")}</span>
				)}
			</button>

			{expanded && memory && (
				<span className="mt-1 block rounded border bg-background p-2 text-xs shadow-sm">
					<span className="block text-foreground">{memory.content}</span>
					<span className="mt-1 flex items-center gap-2 text-muted-foreground">
						<span
							className={`rounded px-1 py-0.5 ${CATEGORY_COLORS[memory.category] ?? "bg-muted"}`}
						>
							{memory.category}
						</span>
						<Button
							variant="link"
							className="h-auto p-0 text-xs"
							onClick={(e) => {
								e.stopPropagation();
								navigate({ to: "/settings" });
							}}
						>
							{t("viewInSettings")}
						</Button>
					</span>
				</span>
			)}
		</span>
	);
}

interface MemoryBadgesProps {
	memoryIds: string[];
}

export function MemoryBadges({ memoryIds }: MemoryBadgesProps) {
	if (!memoryIds || memoryIds.length === 0) return null;

	return (
		<div className="mt-1.5 flex flex-wrap gap-1">
			{memoryIds.map((id) => (
				<MemoryBadge key={id} memoryId={id} />
			))}
		</div>
	);
}
