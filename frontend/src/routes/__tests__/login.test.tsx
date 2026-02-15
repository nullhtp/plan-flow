import { describe, expect, it } from "vitest";

describe("Login validation logic", () => {
	function validateLogin(email: string, password: string): Record<string, string> {
		const errors: Record<string, string> = {};
		if (!email.trim()) {
			errors.email = "Email is required";
		}
		if (!password) {
			errors.password = "Password is required";
		}
		return errors;
	}

	it("returns errors for empty email and password", () => {
		const errors = validateLogin("", "");
		expect(errors.email).toBe("Email is required");
		expect(errors.password).toBe("Password is required");
	});

	it("returns error for empty email only", () => {
		const errors = validateLogin("", "password123");
		expect(errors.email).toBe("Email is required");
		expect(errors.password).toBeUndefined();
	});

	it("returns error for empty password only", () => {
		const errors = validateLogin("user@example.com", "");
		expect(errors.password).toBe("Password is required");
		expect(errors.email).toBeUndefined();
	});

	it("returns no errors for valid input", () => {
		const errors = validateLogin("user@example.com", "password123");
		expect(Object.keys(errors)).toHaveLength(0);
	});
});
