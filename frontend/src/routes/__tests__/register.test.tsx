import { describe, expect, it } from "vitest";

describe("Register validation logic", () => {
	function validateRegister(
		email: string,
		password: string,
		confirmPassword: string,
	): Record<string, string> {
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
		return errors;
	}

	it("returns errors for empty fields", () => {
		const errors = validateRegister("", "", "");
		expect(errors.email).toBe("Email is required");
		expect(errors.password).toBe("Password must be at least 8 characters");
	});

	it("returns error for short password", () => {
		const errors = validateRegister("user@example.com", "short", "short");
		expect(errors.password).toBe("Password must be at least 8 characters");
		expect(errors.email).toBeUndefined();
	});

	it("returns error for mismatched passwords", () => {
		const errors = validateRegister("user@example.com", "password123", "password456");
		expect(errors.confirmPassword).toBe("Passwords do not match");
	});

	it("returns no errors for valid input", () => {
		const errors = validateRegister("user@example.com", "password123", "password123");
		expect(Object.keys(errors)).toHaveLength(0);
	});

	it("catches both short password and mismatch", () => {
		const errors = validateRegister("user@example.com", "short", "different");
		expect(errors.password).toBeDefined();
		expect(errors.confirmPassword).toBeDefined();
	});
});
