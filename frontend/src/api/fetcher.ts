const API_BASE_URL = "http://localhost:8000";

/**
 * Custom fetcher for Orval-generated API hooks.
 * - Prepends the backend base URL to all requests
 * - Includes credentials (cookies) for httpOnly cookie auth
 */
export async function customFetch<T>(url: string, options: RequestInit): Promise<T> {
	const fullUrl = `${API_BASE_URL}${url}`;

	const response = await fetch(fullUrl, {
		...options,
		credentials: "include",
	});

	const body = [204, 205, 304].includes(response.status) ? null : await response.text();
	const data = body ? JSON.parse(body) : {};

	if (!response.ok) {
		throw { status: response.status, data, headers: response.headers };
	}

	return { data, status: response.status, headers: response.headers } as T;
}
