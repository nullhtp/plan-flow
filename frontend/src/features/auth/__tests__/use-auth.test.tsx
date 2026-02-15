import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../components/auth-provider";
import { useAuth } from "../hooks/use-auth";

// Mock the generated API hooks
vi.mock("@/api/generated/auth/auth", () => ({
	useMeApiAuthMeGet: vi.fn(),
	useLoginApiAuthLoginPost: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
	useRegisterApiAuthRegisterPost: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
	useLogoutApiAuthLogoutPost: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
	getMeApiAuthMeGetQueryKey: vi.fn(() => ["/api/auth/me"]),
}));

import { useMeApiAuthMeGet } from "@/api/generated/auth/auth";

const mockedUseMeApiAuthMeGet = vi.mocked(useMeApiAuthMeGet);

function createWrapper() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	return function Wrapper({ children }: { children: ReactNode }) {
		return (
			<QueryClientProvider client={queryClient}>
				<AuthProvider>{children}</AuthProvider>
			</QueryClientProvider>
		);
	};
}

describe("useAuth", () => {
	it("provides authenticated state when user data is available", async () => {
		mockedUseMeApiAuthMeGet.mockReturnValue({
			data: {
				data: { id: "1", email: "test@example.com", is_active: true, created_at: "2025-01-01" },
				status: 200,
				headers: new Headers(),
			},
			isLoading: false,
			isError: false,
		} as ReturnType<typeof useMeApiAuthMeGet>);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await waitFor(() => {
			expect(result.current.isAuthenticated).toBe(true);
			expect(result.current.user?.email).toBe("test@example.com");
			expect(result.current.isLoading).toBe(false);
		});
	});

	it("provides unauthenticated state when no user data", async () => {
		mockedUseMeApiAuthMeGet.mockReturnValue({
			data: undefined,
			isLoading: false,
			isError: true,
		} as ReturnType<typeof useMeApiAuthMeGet>);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await waitFor(() => {
			expect(result.current.isAuthenticated).toBe(false);
			expect(result.current.user).toBeNull();
			expect(result.current.isLoading).toBe(false);
		});
	});

	it("provides loading state while query is pending", async () => {
		mockedUseMeApiAuthMeGet.mockReturnValue({
			data: undefined,
			isLoading: true,
			isError: false,
		} as ReturnType<typeof useMeApiAuthMeGet>);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await waitFor(() => {
			expect(result.current.isLoading).toBe(true);
			expect(result.current.isAuthenticated).toBe(false);
			expect(result.current.user).toBeNull();
		});
	});
});
