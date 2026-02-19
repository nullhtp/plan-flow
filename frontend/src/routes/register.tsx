import { createRoute, Navigate, useNavigate } from "@tanstack/react-router";
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
import { useAuth, useRegister } from "@/features/auth/hooks/use-auth";
import { rootRoute } from "./__root";

export const registerRoute = createRoute({
	getParentRoute: () => rootRoute,
	path: "/register",
	component: RegisterPage,
});

function RegisterPage() {
	const navigate = useNavigate();
	const { isAuthenticated } = useAuth();
	const register = useRegister();

	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [confirmPassword, setConfirmPassword] = useState("");
	const [error, setError] = useState("");
	const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

	// Already logged in — redirect away
	if (isAuthenticated) {
		return <Navigate to="/" />;
	}

	function validate(): boolean {
		const errors: Record<string, string> = {};
		if (!email.trim()) {
			errors.email = "Email is required";
		}
		if (password.length < 8) {
			errors.password = "Password must be at least 8 characters";
		}
		if (password !== confirmPassword) {
			errors.confirmPassword = "Passwords do not match";
		}
		setValidationErrors(errors);
		return Object.keys(errors).length === 0;
	}

	async function handleSubmit(e: FormEvent) {
		e.preventDefault();
		setError("");

		if (!validate()) return;

		try {
			await register.mutateAsync({ data: { email, password } });
			navigate({ to: "/" });
		} catch (err: unknown) {
			const apiError = err as { status?: number };
			if (apiError.status === 409) {
				setError("An account with this email already exists");
			} else {
				setError("Registration failed. Please try again.");
			}
		}
	}

	return (
		<div className="flex min-h-screen items-center justify-center">
			<Card className="w-full max-w-md">
				<CardHeader>
					<CardTitle className="text-2xl">Create account</CardTitle>
					<CardDescription>Enter your details to get started</CardDescription>
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
								placeholder="At least 8 characters"
								value={password}
								onChange={(e) => setPassword(e.target.value)}
								aria-invalid={!!validationErrors.password}
							/>
							{validationErrors.password && (
								<p className="text-sm text-destructive">{validationErrors.password}</p>
							)}
						</div>
						<div className="space-y-2">
							<Label htmlFor="confirmPassword">Confirm password</Label>
							<Input
								id="confirmPassword"
								type="password"
								placeholder="Re-enter your password"
								value={confirmPassword}
								onChange={(e) => setConfirmPassword(e.target.value)}
								aria-invalid={!!validationErrors.confirmPassword}
							/>
							{validationErrors.confirmPassword && (
								<p className="text-sm text-destructive">{validationErrors.confirmPassword}</p>
							)}
						</div>
					</CardContent>
					<CardFooter className="flex flex-col gap-4">
						<Button type="submit" className="w-full" disabled={register.isPending}>
							{register.isPending ? "Creating account..." : "Create account"}
						</Button>
						<p className="text-sm text-muted-foreground">
							Already have an account?{" "}
							<a
								href="/login"
								className="text-primary underline-offset-4 hover:underline"
								onClick={(e) => {
									e.preventDefault();
									navigate({ to: "/login", search: { returnTo: undefined } });
								}}
							>
								Log in
							</a>
						</p>
					</CardFooter>
				</form>
			</Card>
		</div>
	);
}
