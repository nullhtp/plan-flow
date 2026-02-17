import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export interface UserLocationMeta {
	city: string | null;
	country: string | null;
}

export interface UserMeta {
	timezone: string;
	locale: string;
	current_datetime: string;
	location: UserLocationMeta | null;
	device_type: string;
}

export interface UseUserMetaResult {
	/** Current metadata snapshot (location may still be resolving). */
	meta: UserMeta;
	/** Request geolocation (best called from a user gesture). Returns updated meta. */
	resolveLocation: () => Promise<UserMeta>;
}

function getDeviceType(): string {
	const width = window.innerWidth;
	if (width < 768) return "mobile";
	if (width < 1024) return "tablet";
	return "desktop";
}

async function reverseGeocode(lat: number, lng: number): Promise<UserLocationMeta | null> {
	try {
		const url = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json&zoom=10`;
		const response = await fetch(url, {
			headers: { "Accept-Language": navigator.language },
		});
		if (!response.ok) return null;
		const data = await response.json();
		const address = data.address;
		if (!address) return null;
		return {
			city: address.city || address.town || address.village || null,
			country: address.country || null,
		};
	} catch {
		return null;
	}
}

function requestGeolocation(): Promise<UserLocationMeta | null> {
	if (!navigator.geolocation) return Promise.resolve(null);

	return new Promise((resolve) => {
		navigator.geolocation.getCurrentPosition(
			async (position) => {
				const location = await reverseGeocode(position.coords.latitude, position.coords.longitude);
				resolve(location);
			},
			() => {
				resolve(null);
			},
			{ timeout: 5000, maximumAge: 300_000 },
		);
	});
}

/**
 * Collects user environment metadata for AI context.
 *
 * Timezone, locale, and device type are available immediately.
 * Location is resolved asynchronously via browser Geolocation API + Nominatim.
 *
 * Returns `meta` (current snapshot) and `resolveLocation()` which triggers
 * a geolocation request — best called from a user gesture (e.g. form submit)
 * so the browser shows the permission prompt.
 *
 * `current_datetime` is always empty — overridden server-side.
 */
export function useUserMeta(): UseUserMetaResult {
	const [location, setLocation] = useState<UserLocationMeta | null>(null);
	const locationRef = useRef<UserLocationMeta | null>(null);

	// Best-effort eager fetch (works if permission is already granted)
	useEffect(() => {
		let cancelled = false;
		requestGeolocation().then((result) => {
			if (!cancelled && result) {
				locationRef.current = result;
				setLocation(result);
			}
		});
		return () => {
			cancelled = true;
		};
	}, []);

	const stableFields = useMemo(
		() => ({
			timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
			locale: navigator.language,
			current_datetime: "",
			device_type: getDeviceType(),
		}),
		[],
	);

	const meta = useMemo(
		() => ({
			...stableFields,
			location,
		}),
		[stableFields, location],
	);

	const resolveLocation = useCallback(async (): Promise<UserMeta> => {
		// If we already have location, return immediately
		if (locationRef.current) {
			return { ...stableFields, location: locationRef.current };
		}
		const result = await requestGeolocation();
		if (result) {
			locationRef.current = result;
			setLocation(result);
		}
		return { ...stableFields, location: result };
	}, [stableFields]);

	return { meta, resolveLocation };
}
