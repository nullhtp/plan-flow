import { useQueryClient } from "@tanstack/react-query";
import { createContext, useContext } from "react";
import {
	getMeApiAuthMeGetQueryKey,
	useLoginApiAuthLoginPost,
	useLogoutApiAuthLogoutPost,
	useMeApiAuthMeGet,
	useRegisterApiAuthRegisterPost,
} from "@/api/generated/auth/auth";
import type { UserResponse } from "@/api/generated/model";

interface AuthContextValue {
	user: UserResponse | null;
	isAuthenticated: boolean;
	isLoading: boolean;
}

export const AuthContext = createContext<AuthContextValue>({
	user: null,
	isAuthenticated: false,
	isLoading: true,
});

export function useAuth() {
	return useContext(AuthContext);
}

export function useAuthQuery() {
	return useMeApiAuthMeGet({
		query: {
			retry: false,
			staleTime: 1000 * 60 * 5, // 5 min
		},
	});
}

export function useLogin() {
	const queryClient = useQueryClient();
	return useLoginApiAuthLoginPost({
		mutation: {
			onSuccess: () => {
				queryClient.invalidateQueries({
					queryKey: getMeApiAuthMeGetQueryKey(),
				});
			},
		},
	});
}

export function useRegister() {
	const queryClient = useQueryClient();
	return useRegisterApiAuthRegisterPost({
		mutation: {
			onSuccess: () => {
				queryClient.invalidateQueries({
					queryKey: getMeApiAuthMeGetQueryKey(),
				});
			},
		},
	});
}

export function useLogout() {
	const queryClient = useQueryClient();
	return useLogoutApiAuthLogoutPost({
		mutation: {
			onSuccess: () => {
				queryClient.setQueryData(getMeApiAuthMeGetQueryKey(), null);
				queryClient.invalidateQueries({
					queryKey: getMeApiAuthMeGetQueryKey(),
				});
			},
		},
	});
}
