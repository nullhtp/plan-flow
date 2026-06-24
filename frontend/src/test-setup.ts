import "@testing-library/jest-dom/vitest";
import i18n from "@/lib/i18n";

// Tests assert against the original English copy, so force English regardless of
// the persisted language. Resources are bundled synchronously, so this applies
// immediately.
i18n.changeLanguage("en");

// Polyfill APIs missing in jsdom
globalThis.ResizeObserver = class ResizeObserver {
	observe() {}
	unobserve() {}
	disconnect() {}
};
