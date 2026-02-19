const API_BASE_URL = "http://localhost:8000";

export interface SSEEvent {
	event: string;
	data: unknown;
}

export type SSEEventHandler = (event: SSEEvent) => void;

export interface SSEOptions {
	url: string;
	body?: unknown;
	onEvent: SSEEventHandler;
	onError?: (error: Error) => void;
	onClose?: () => void;
	signal?: AbortSignal;
}

/**
 * Fetch-based SSE client for POST endpoints with cookie auth.
 *
 * Uses fetch() with streaming response body to parse SSE events.
 * Needed because native EventSource only supports GET requests.
 */
export async function fetchSSE({
	url,
	body,
	onEvent,
	onError,
	onClose,
	signal,
}: SSEOptions): Promise<void> {
	const fullUrl = `${API_BASE_URL}${url}`;

	const headers: Record<string, string> = {
		Accept: "text/event-stream",
	};
	if (body !== undefined) {
		headers["Content-Type"] = "application/json";
	}

	let response: Response;
	try {
		response = await fetch(fullUrl, {
			method: "POST",
			credentials: "include",
			headers,
			body: body !== undefined ? JSON.stringify(body) : undefined,
			signal,
		});
	} catch (error) {
		if (signal?.aborted) return;
		onError?.(error instanceof Error ? error : new Error("Connection failed"));
		return;
	}

	if (!response.ok) {
		const body = await response.text().catch(() => "");
		let detail = "Request failed";
		try {
			const parsed = JSON.parse(body);
			detail = parsed.detail || detail;
		} catch {
			// ignore parse errors
		}
		onError?.(new Error(detail));
		return;
	}

	const reader = response.body?.getReader();
	if (!reader) {
		onError?.(new Error("No response body"));
		return;
	}

	const decoder = new TextDecoder();
	let buffer = "";

	try {
		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			buffer += decoder.decode(value, { stream: true });

			// SSE events are separated by double newlines
			const parts = buffer.split("\n\n");
			// Keep the last incomplete part in the buffer
			buffer = parts.pop() ?? "";

			for (const part of parts) {
				if (!part.trim()) continue;

				let eventType = "message";
				let dataStr = "";

				for (const line of part.split("\n")) {
					if (line.startsWith("event: ")) {
						eventType = line.slice(7);
					} else if (line.startsWith("data: ")) {
						dataStr = line.slice(6);
					}
				}

				if (dataStr) {
					try {
						const data: unknown = JSON.parse(dataStr);
						onEvent({ event: eventType, data });
					} catch {
						// Skip malformed data
					}
				}
			}
		}
	} catch (error) {
		if (signal?.aborted) return;
		onError?.(error instanceof Error ? error : new Error("Stream read failed"));
		return;
	}

	onClose?.();
}
