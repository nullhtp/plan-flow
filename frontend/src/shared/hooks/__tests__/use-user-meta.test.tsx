import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useUserMeta } from "../use-user-meta";

describe("useUserMeta", () => {
	it("returns timezone from Intl API", () => {
		const { result } = renderHook(() => useUserMeta());
		expect(result.current.meta.timezone).toBe(Intl.DateTimeFormat().resolvedOptions().timeZone);
		expect(result.current.meta.timezone.length).toBeGreaterThan(0);
	});

	it("returns locale from navigator.language", () => {
		const { result } = renderHook(() => useUserMeta());
		expect(result.current.meta.locale).toBe(navigator.language);
	});

	it("returns empty current_datetime (set server-side)", () => {
		const { result } = renderHook(() => useUserMeta());
		expect(result.current.meta.current_datetime).toBe("");
	});

	it("returns null location initially when geolocation unavailable", () => {
		const { result } = renderHook(() => useUserMeta());
		expect(result.current.meta.location).toBeNull();
	});

	it("returns desktop device_type for default jsdom viewport", () => {
		const { result } = renderHook(() => useUserMeta());
		expect(result.current.meta.device_type).toBe("desktop");
	});

	it("returns mobile device_type for narrow viewport", () => {
		const original = window.innerWidth;
		Object.defineProperty(window, "innerWidth", {
			value: 375,
			writable: true,
			configurable: true,
		});

		const { result } = renderHook(() => useUserMeta());
		expect(result.current.meta.device_type).toBe("mobile");

		Object.defineProperty(window, "innerWidth", {
			value: original,
			writable: true,
			configurable: true,
		});
	});

	it("returns tablet device_type for medium viewport", () => {
		const original = window.innerWidth;
		Object.defineProperty(window, "innerWidth", {
			value: 800,
			writable: true,
			configurable: true,
		});

		const { result } = renderHook(() => useUserMeta());
		expect(result.current.meta.device_type).toBe("tablet");

		Object.defineProperty(window, "innerWidth", {
			value: original,
			writable: true,
			configurable: true,
		});
	});

	it("has the expected shape with meta and resolveLocation", () => {
		const { result } = renderHook(() => useUserMeta());
		expect(result.current.meta).toEqual(
			expect.objectContaining({
				timezone: expect.any(String),
				locale: expect.any(String),
				current_datetime: expect.any(String),
				device_type: expect.any(String),
			}),
		);
		expect(result.current.meta).toHaveProperty("location");
		expect(typeof result.current.resolveLocation).toBe("function");
	});

	describe("with browser geolocation", () => {
		let mockGetCurrentPosition: ReturnType<typeof vi.fn>;

		beforeEach(() => {
			mockGetCurrentPosition = vi.fn();
			Object.defineProperty(navigator, "geolocation", {
				value: { getCurrentPosition: mockGetCurrentPosition },
				writable: true,
				configurable: true,
			});
		});

		afterEach(() => {
			Object.defineProperty(navigator, "geolocation", {
				value: undefined,
				writable: true,
				configurable: true,
			});
			vi.restoreAllMocks();
		});

		it("resolves location when geolocation and reverse geocoding succeed", async () => {
			mockGetCurrentPosition.mockImplementation((success: PositionCallback) => {
				success({
					coords: { latitude: 52.52, longitude: 13.405 },
				} as GeolocationPosition);
			});

			const mockResponse = {
				ok: true,
				json: () =>
					Promise.resolve({
						address: { city: "Berlin", country: "Germany" },
					}),
			};
			vi.spyOn(globalThis, "fetch").mockResolvedValue(mockResponse as Response);

			const { result } = renderHook(() => useUserMeta());

			await waitFor(() => {
				expect(result.current.meta.location).toEqual({
					city: "Berlin",
					country: "Germany",
				});
			});

			expect(globalThis.fetch).toHaveBeenCalledWith(
				expect.stringContaining("nominatim.openstreetmap.org/reverse"),
				expect.any(Object),
			);
		});

		it("keeps location null when geolocation is denied", async () => {
			mockGetCurrentPosition.mockImplementation(
				(_success: PositionCallback, error: PositionErrorCallback) => {
					error({
						code: 1,
						message: "User denied",
					} as GeolocationPositionError);
				},
			);

			const { result } = renderHook(() => useUserMeta());

			await act(async () => {
				await new Promise((r) => setTimeout(r, 10));
			});

			expect(result.current.meta.location).toBeNull();
		});

		it("keeps location null when reverse geocoding fails", async () => {
			mockGetCurrentPosition.mockImplementation((success: PositionCallback) => {
				success({
					coords: { latitude: 0, longitude: 0 },
				} as GeolocationPosition);
			});

			vi.spyOn(globalThis, "fetch").mockResolvedValue({
				ok: false,
				status: 500,
			} as Response);

			const { result } = renderHook(() => useUserMeta());

			await act(async () => {
				await new Promise((r) => setTimeout(r, 10));
			});

			expect(result.current.meta.location).toBeNull();
		});

		it("uses town fallback when city is not in address", async () => {
			mockGetCurrentPosition.mockImplementation((success: PositionCallback) => {
				success({
					coords: { latitude: 51.5, longitude: -0.1 },
				} as GeolocationPosition);
			});

			vi.spyOn(globalThis, "fetch").mockResolvedValue({
				ok: true,
				json: () =>
					Promise.resolve({
						address: { town: "Smallville", country: "UK" },
					}),
			} as Response);

			const { result } = renderHook(() => useUserMeta());

			await waitFor(() => {
				expect(result.current.meta.location).toEqual({
					city: "Smallville",
					country: "UK",
				});
			});
		});

		it("resolveLocation triggers geolocation and returns updated meta", async () => {
			mockGetCurrentPosition.mockImplementation((success: PositionCallback) => {
				success({
					coords: { latitude: 48.86, longitude: 2.35 },
				} as GeolocationPosition);
			});

			vi.spyOn(globalThis, "fetch").mockResolvedValue({
				ok: true,
				json: () =>
					Promise.resolve({
						address: { city: "Paris", country: "France" },
					}),
			} as Response);

			const { result } = renderHook(() => useUserMeta());

			let resolved = result.current.meta;
			await act(async () => {
				resolved = await result.current.resolveLocation();
			});

			expect(resolved.location).toEqual({
				city: "Paris",
				country: "France",
			});
			expect(resolved.timezone).toBe(Intl.DateTimeFormat().resolvedOptions().timeZone);
		});

		it("resolveLocation returns cached location if already resolved", async () => {
			mockGetCurrentPosition.mockImplementation((success: PositionCallback) => {
				success({
					coords: { latitude: 52.52, longitude: 13.405 },
				} as GeolocationPosition);
			});

			vi.spyOn(globalThis, "fetch").mockResolvedValue({
				ok: true,
				json: () =>
					Promise.resolve({
						address: { city: "Berlin", country: "Germany" },
					}),
			} as Response);

			const { result } = renderHook(() => useUserMeta());

			// Wait for eager fetch to complete
			await waitFor(() => {
				expect(result.current.meta.location).not.toBeNull();
			});

			// Clear mock call count
			vi.mocked(globalThis.fetch).mockClear();
			mockGetCurrentPosition.mockClear();

			let resolved = result.current.meta;
			await act(async () => {
				resolved = await result.current.resolveLocation();
			});

			// Should return cached location without new geolocation or fetch calls
			expect(resolved.location).toEqual({
				city: "Berlin",
				country: "Germany",
			});
			expect(mockGetCurrentPosition).not.toHaveBeenCalled();
		});
	});
});
