import { Copy, FileText, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";
import type { ArtifactResponse } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useArtifacts } from "../hooks/use-artifacts";

interface TaskArtifactsProps {
	taskId: string;
}

const markdownStyles =
	"[&_a]:text-blue-600 [&_a]:underline [&_a:hover]:text-blue-800 " +
	"[&_h1]:text-xl [&_h1]:font-bold [&_h1]:mt-6 [&_h1]:mb-2 " +
	"[&_h2]:text-lg [&_h2]:font-bold [&_h2]:mt-5 [&_h2]:mb-2 " +
	"[&_h3]:text-base [&_h3]:font-semibold [&_h3]:mt-4 [&_h3]:mb-1 " +
	"[&_p]:my-2 [&_p]:leading-relaxed " +
	"[&_ul]:list-disc [&_ul]:pl-6 [&_ul]:my-2 " +
	"[&_ol]:list-decimal [&_ol]:pl-6 [&_ol]:my-2 " +
	"[&_li]:my-1 " +
	"[&_blockquote]:border-l-4 [&_blockquote]:pl-4 [&_blockquote]:my-2 [&_blockquote]:text-muted-foreground [&_blockquote]:italic " +
	"[&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-sm " +
	"[&_pre]:bg-muted [&_pre]:p-4 [&_pre]:rounded-md [&_pre]:overflow-x-auto [&_pre]:my-2 " +
	"[&_table]:w-full [&_table]:border-collapse [&_table]:my-3 " +
	"[&_th]:border [&_th]:border-border [&_th]:px-3 [&_th]:py-2 [&_th]:bg-muted [&_th]:font-semibold [&_th]:text-left " +
	"[&_td]:border [&_td]:border-border [&_td]:px-3 [&_td]:py-2 " +
	"[&_hr]:my-4 [&_hr]:border-border";

const markdownComponents = {
	a: ({ href, children }: { href?: string; children?: React.ReactNode }) => (
		<a href={href} target="_blank" rel="noopener noreferrer">
			{children}
		</a>
	),
};

function ArtifactFullscreen({
	artifact,
	onClose,
	onDelete,
}: {
	artifact: ArtifactResponse;
	onClose: () => void;
	onDelete: (id: string) => void;
}) {
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

	useEffect(() => {
		const handler = (e: KeyboardEvent) => {
			if (e.key === "Escape") onClose();
		};
		window.addEventListener("keydown", handler);
		return () => window.removeEventListener("keydown", handler);
	}, [onClose]);

	const copyContent = async () => {
		try {
			await navigator.clipboard.writeText(artifact.content);
			toast.success("Copied to clipboard");
		} catch {
			toast.error("Failed to copy");
		}
	};

	return (
		<div className="fixed inset-0 z-50 flex flex-col bg-background">
			{/* Header */}
			<div className="flex items-center justify-between border-b px-6 py-4 shrink-0">
				<div className="flex items-center gap-3 min-w-0">
					<FileText className="h-5 w-5 shrink-0 text-muted-foreground" />
					<h2 className="text-lg font-semibold truncate">{artifact.title}</h2>
					<span className="text-sm text-muted-foreground shrink-0">
						{new Date(artifact.created_at).toLocaleDateString()}
					</span>
				</div>
				<div className="flex items-center gap-1 shrink-0">
					<Button variant="ghost" size="sm" onClick={copyContent} title="Copy content">
						<Copy className="h-4 w-4" />
					</Button>
					{!showDeleteConfirm ? (
						<Button
							variant="ghost"
							size="sm"
							onClick={() => setShowDeleteConfirm(true)}
							className="text-destructive"
							title="Delete artifact"
						>
							<Trash2 className="h-4 w-4" />
						</Button>
					) : (
						<div className="flex items-center gap-1">
							<Button
								variant="destructive"
								size="sm"
								onClick={() => {
									onDelete(artifact.id);
									onClose();
								}}
							>
								Delete
							</Button>
							<Button variant="ghost" size="sm" onClick={() => setShowDeleteConfirm(false)}>
								Cancel
							</Button>
						</div>
					)}
					<Button variant="ghost" size="sm" onClick={onClose} title="Close">
						<X className="h-4 w-4" />
					</Button>
				</div>
			</div>

			{/* Content */}
			<div className="flex-1 overflow-y-auto">
				<div className={`mx-auto max-w-3xl px-6 py-8 text-sm ${markdownStyles}`}>
					<Markdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
						{artifact.content}
					</Markdown>
				</div>
			</div>
		</div>
	);
}

export function TaskArtifacts({ taskId }: TaskArtifactsProps) {
	const { artifacts, isLoading, deleteArtifact } = useArtifacts(taskId);
	const [openArtifact, setOpenArtifact] = useState<ArtifactResponse | null>(null);

	if (isLoading) {
		return (
			<div>
				<Label className="flex items-center gap-1.5">
					<FileText className="h-3.5 w-3.5" />
					Artifacts
				</Label>
				<div className="mt-2 h-10 animate-pulse rounded-md bg-muted" />
			</div>
		);
	}

	if (artifacts.length === 0) {
		return null;
	}

	return (
		<>
			<div>
				<Label className="flex items-center gap-1.5">
					<FileText className="h-3.5 w-3.5" />
					Artifacts ({artifacts.length})
				</Label>
				<div className="mt-2 space-y-1">
					{artifacts.map((artifact) => (
						<button
							key={artifact.id}
							type="button"
							onClick={() => setOpenArtifact(artifact)}
							className="flex w-full items-center gap-2 rounded-md border px-3 py-2 text-left text-sm hover:bg-muted/50 transition-colors"
						>
							<FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
							<span className="flex-1 truncate font-medium">{artifact.title}</span>
							<span className="text-xs text-muted-foreground">
								{new Date(artifact.created_at).toLocaleDateString()}
							</span>
						</button>
					))}
				</div>
			</div>

			{openArtifact && (
				<ArtifactFullscreen
					artifact={openArtifact}
					onClose={() => setOpenArtifact(null)}
					onDelete={(id) => {
						deleteArtifact(id);
						setOpenArtifact(null);
					}}
				/>
			)}
		</>
	);
}
