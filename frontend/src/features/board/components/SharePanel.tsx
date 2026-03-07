import { Copy, Link, RefreshCw, Trash2, UserMinus, Users, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
	useBoardMembers,
	useCreateShareLink,
	useDeleteShareLink,
	useRevokeMember,
	useShareLink,
} from "@/features/board/hooks/use-share";

interface SharePanelProps {
	boardId: string;
	onClose: () => void;
}

export function SharePanel({ boardId, onClose }: SharePanelProps) {
	const shareQuery = useShareLink(boardId);
	const membersQuery = useBoardMembers(boardId);
	const createShare = useCreateShareLink(boardId);
	const deleteShare = useDeleteShareLink(boardId);
	const revokeMember = useRevokeMember(boardId);
	const [copied, setCopied] = useState(false);

	const shareLink = shareQuery.data;
	const members = membersQuery.data ?? [];

	const handleCopy = async () => {
		if (!shareLink) return;
		await navigator.clipboard.writeText(shareLink.url);
		setCopied(true);
		setTimeout(() => setCopied(false), 2000);
	};

	return (
		// biome-ignore lint/a11y/useKeyWithClickEvents: backdrop dismiss pattern
		// biome-ignore lint/a11y/noStaticElementInteractions: backdrop dismiss pattern
		<div
			className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/30"
			onClick={onClose}
		>
			{/* biome-ignore lint/a11y/noStaticElementInteractions: stop propagation to backdrop */}
			{/* biome-ignore lint/a11y/useKeyWithClickEvents: stop propagation to backdrop */}
			<div
				className="w-full max-w-md rounded-lg border bg-background p-5 shadow-lg"
				onClick={(e) => e.stopPropagation()}
			>
				<div className="flex items-center justify-between mb-4">
					<h2 className="text-lg font-semibold flex items-center gap-2">
						<Users className="h-5 w-5" />
						Share Board
					</h2>
					<button
						type="button"
						onClick={onClose}
						className="text-muted-foreground hover:text-foreground"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				{/* Share Link Section */}
				<div className="space-y-3 mb-5">
					<h3 className="text-sm font-medium">Share Link</h3>
					{shareLink ? (
						<div className="space-y-2">
							<div className="flex items-center gap-2 rounded border px-3 py-2 text-sm bg-muted/50">
								<Link className="h-4 w-4 shrink-0 text-muted-foreground" />
								<span className="truncate flex-1 select-all">{shareLink.url}</span>
								<Button
									variant="outline"
									size="sm"
									className="shrink-0 h-7 gap-1"
									onClick={handleCopy}
								>
									<Copy className="h-3 w-3" />
									{copied ? "Copied" : "Copy"}
								</Button>
							</div>
							<div className="flex gap-2">
								<Button
									variant="outline"
									size="sm"
									className="gap-1"
									onClick={() => createShare.mutate()}
									disabled={createShare.isPending}
								>
									<RefreshCw className="h-3 w-3" />
									Regenerate
								</Button>
								<Button
									variant="outline"
									size="sm"
									className="gap-1 text-destructive"
									onClick={() => deleteShare.mutate()}
									disabled={deleteShare.isPending}
								>
									<Trash2 className="h-3 w-3" />
									Remove Link
								</Button>
							</div>
						</div>
					) : (
						<Button
							size="sm"
							className="gap-1"
							onClick={() => createShare.mutate()}
							disabled={createShare.isPending}
						>
							<Link className="h-3 w-3" />
							{createShare.isPending ? "Creating..." : "Create Share Link"}
						</Button>
					)}
				</div>

				{/* Members Section */}
				<div className="space-y-3">
					<h3 className="text-sm font-medium">Members ({members.length})</h3>
					{membersQuery.isLoading ? (
						<p className="text-sm text-muted-foreground">Loading...</p>
					) : (
						<ul className="space-y-2">
							{members.map((m) => (
								<li key={m.user_id} className="flex items-center justify-between text-sm">
									<div className="flex items-center gap-2 min-w-0">
										<span className="truncate">{m.email}</span>
										<span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
											{m.role}
										</span>
									</div>
									{m.role !== "owner" && (
										<button
											type="button"
											className="shrink-0 p-1 text-muted-foreground hover:text-destructive"
											onClick={() => revokeMember.mutate(m.user_id)}
											title="Remove member"
										>
											<UserMinus className="h-4 w-4" />
										</button>
									)}
								</li>
							))}
						</ul>
					)}
				</div>
			</div>
		</div>
	);
}
