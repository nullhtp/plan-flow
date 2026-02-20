import "@testing-library/jest-dom/vitest";

// Polyfill APIs missing in jsdom
globalThis.ResizeObserver = class ResizeObserver {
	observe() {}
	unobserve() {}
	disconnect() {}
};
