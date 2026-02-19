import { createRoute, Navigate, useNavigate, useSearch } from "@tanstack/react-router";
import { type FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth, useLogin } from "@/features/auth/hooks/use-auth";
import { rootRoute } from "./__root";

export const loginRoute = createRoute({
	getParentRoute: () => rootRoute,
	path: "/login",
	validateSearch: (search: Record<string, unknown>) => ({
		returnTo: typeof search.returnTo === "string" ? search.returnTo : undefined,
	}),
	component: LoginPage,
});

function LoginPage() {
	const navigate = useNavigate();
	const { returnTo } = useSearch({ from: "/login" });
	const { isAuthenticated } = useAuth();
	const login = useLogin();

	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [error, setError] = useState("");
	const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

	// Already logged in — redirect away
	if (isAuthenticated) {
		return <Navigate to={returnTo ?? "/"} />;
	}

	function validate(): boolean {
		const errors: Record<string, string> = {};
		if (!email.trim()) {
			errors.email = "Email is required";
		}
		if (!password) {
			errors.password = "Password is required";
		}
		setValidationErrors(errors);
		return Object.keys(errors).length === 0;
	}

	async function handleSubmit(e: FormEvent) {
		e.preventDefault();
		setError("");

		if (!validate()) return;

		try {
			await login.mutateAsync({ data: { email, password } });
			navigate({ to: returnTo ?? "/" });
		} catch {
			setError("Invalid email or password");
		}
	}

	return (
		<div className="flex min-h-screen items-center justify-center">
			<Card className="w-full max-w-md">
				<CardHeader>
					<CardTitle className="text-2xl">Log in</CardTitle>
					<CardDescription>Enter your credentials to access your account</CardDescription>
				</CardHeader>
				<form onSubmit={handleSubmit}>
					<CardContent className="space-y-4">
						{error && (
							<div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
								{error}
							</div>
						)}
						<div className="space-y-2">
							<Label htmlFor="email">Email</Label>
							<Input
								id="email"
								type="email"
								placeholder="you@example.com"
								value={email}
								onChange={(e) => setEmail(e.target.value)}
								aria-invalid={!!validationErrors.email}
							/>
							{validationErrors.email && (
								<p className="text-sm text-destructive">{validationErrors.email}</p>
							)}
						</div>
						<div className="space-y-2">
							<Label htmlFor="password">Password</Label>
							<Input
								id="password"
								type="password"
								value={password}
								onChange={(e) => setPassword(e.target.value)}
								aria-invalid={!!validationErrors.password}
							/>
							{validationErrors.password && (
								<p className="text-sm text-destructive">{validationErrors.password}</p>
							)}
						</div>
					</CardContent>
					<CardFooter className="flex flex-col gap-4">
						<Button type="submit" className="w-full" disabled={login.isPending}>
							{login.isPending ? "Logging in..." : "Log in"}
						</Button>
						<p className="text-sm text-muted-foreground">
							Don&apos;t have an account?{" "}
							<a
								href="/register"
								className="text-primary underline-offset-4 hover:underline"
								onClick={(e) => {
									e.preventDefault();
									navigate({ to: "/register" });
								}}
							>
								Register
							</a>
						</p>
					</CardFooter>
				</form>
			</Card>
		</div>
	);
}
