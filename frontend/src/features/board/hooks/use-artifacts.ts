import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
	getListArtifactsEndpointApiTasksTaskIdArtifactsGetQueryKey,
	useDeleteArtifactEndpointApiTasksTaskIdArtifactsArtifactIdDelete,
	useListArtifactsEndpointApiTasksTaskIdArtifactsGet,
} from "@/api/generated/boards/boards";
import type { ArtifactResponse } from "@/api/generated/model";

export function useArtifacts(taskId: string) {
	const queryClient = useQueryClient();
	const artifactsQueryKey = getListArtifactsEndpointApiTasksTaskIdArtifactsGetQueryKey(taskId);

	const { data, isLoading, error } = useListArtifactsEndpointApiTasksTaskIdArtifactsGet(taskId);

	const artifacts: ArtifactResponse[] =
		data && "status" in data && data.status === 200
			? (data as { data: { artifacts: ArtifactResponse[] } }).data.artifacts
			: [];

	const invalidateArtifacts = () => {
		queryClient.invalidateQueries({ queryKey: artifactsQueryKey });
	};

	const deleteMutation = useDeleteArtifactEndpointApiTasksTaskIdArtifactsArtifactIdDelete({
		mutation: {
			onSuccess: () => {
				invalidateArtifacts();
				toast.success("Artifact deleted");
			},
			onError: () => {
				toast.error("Failed to delete artifact");
			},
		},
	});

	const deleteArtifact = (artifactId: string) => {
		deleteMutation.mutate({ taskId, artifactId });
	};

	return {
		artifacts,
		isLoading,
		error,
		deleteArtifact,
		invalidateArtifacts,
	};
}
