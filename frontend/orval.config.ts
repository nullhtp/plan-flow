import { defineConfig } from "orval";

export default defineConfig({
	planflow: {
		input: {
			target: "./openapi.json",
		},
		output: {
			mode: "tags-split",
			target: "./src/api/generated",
			schemas: "./src/api/generated/model",
			client: "react-query",
			httpClient: "fetch",
			prettier: false,
			biome: false,
			override: {
				mutator: {
					path: "./src/api/fetcher.ts",
					name: "customFetch",
				},
				query: {
					useQuery: true,
					useMutation: true,
				},
			},
		},
	},
});
