import type { ReactNode } from "react";
import type { UserResponse } from "@/api/generated/model";
import { AuthContext, useAuthQuery } from "../hooks/use-auth";

export function AuthProvider({ children }: { children: ReactNode }) {
	const { data, isLoading, isError } = useAuthQuery();

	let user: UserResponse | null = null;
	if (!isLoading && !isError && data?.status === 200) {
		user = data.data;
	}

	return (
		<AuthContext
			value={{
				user,
				isAuthenticated: user !== null,
				isLoading,
			}}
		>
			{children}
		</AuthContext>
	);
}
