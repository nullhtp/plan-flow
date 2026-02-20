import "@testing-library/jest-dom/vitest";

// Polyfill APIs missing in jsdom
global.ResizeObserver = class ResizeObserver {
	observe() {}
	unobserve() {}
	disconnect() {}
};
