const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const REFRESH_URL = `${API_BASE_URL}/api/auth/refresh`;

/**
 * Module-level refresh lock.
 * When a 401 triggers a refresh, all subsequent 401s wait on the same
 * promise instead of firing parallel refresh requests.
 * This is critical because the backend rotates the refresh token on each
 * call — concurrent refresh attempts would invalidate each other.
 */
let refreshPromise: Promise<boolean> | null = null;

async function attemptTokenRefresh(): Promise<boolean> {
	try {
		const res = await fetch(REFRESH_URL, {
			method: "POST",
			credentials: "include",
		});
		return res.ok;
	} catch {
		return false;
	}
}

/**
 * Acquire a token refresh, deduplicating concurrent callers.
 * Returns true if the refresh succeeded and the original request
 * should be retried, false if the session is truly expired.
 */
export async function refreshTokens(): Promise<boolean> {
	if (refreshPromise) {
		return refreshPromise;
	}

	refreshPromise = attemptTokenRefresh().finally(() => {
		refreshPromise = null;
	});

	return refreshPromise;
}

/**
 * Custom fetcher for Orval-generated API hooks.
 * - Prepends the backend base URL to all requests
 * - Includes credentials (cookies) for httpOnly cookie auth
 * - On 401, transparently refreshes tokens and retries once
 */
export async function customFetch<T>(url: string, options: RequestInit): Promise<T> {
	const fullUrl = `${API_BASE_URL}${url}`;

	const response = await fetch(fullUrl, {
		...options,
		credentials: "include",
	});

	// If we get a 401 and this is NOT already a refresh request, try to refresh
	if (response.status === 401 && !fullUrl.includes("/auth/refresh")) {
		const refreshed = await refreshTokens();

		if (refreshed) {
			// Retry the original request with the fresh access token cookie
			const retryResponse = await fetch(fullUrl, {
				...options,
				credentials: "include",
			});

			const retryBody = [204, 205, 304].includes(retryResponse.status)
				? null
				: await retryResponse.text();
			const retryData = retryBody ? JSON.parse(retryBody) : {};

			if (!retryResponse.ok) {
				throw { status: retryResponse.status, data: retryData, headers: retryResponse.headers };
			}

			return { data: retryData, status: retryResponse.status, headers: retryResponse.headers } as T;
		}

		// Refresh failed — session is truly expired, throw the original 401
	}

	const body = [204, 205, 304].includes(response.status) ? null : await response.text();
	const data = body ? JSON.parse(body) : {};

	if (!response.ok) {
		throw { status: response.status, data, headers: response.headers };
	}

	return { data, status: response.status, headers: response.headers } as T;
}
