import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import enAuth from "@/locales/en/auth.json";
import enBoard from "@/locales/en/board.json";
import enCommon from "@/locales/en/common.json";
import enGoals from "@/locales/en/goals.json";
import enMemory from "@/locales/en/memory.json";
import enSettings from "@/locales/en/settings.json";
import enTemplates from "@/locales/en/templates.json";
import ruAuth from "@/locales/ru/auth.json";
import ruBoard from "@/locales/ru/board.json";
import ruCommon from "@/locales/ru/common.json";
import ruGoals from "@/locales/ru/goals.json";
import ruMemory from "@/locales/ru/memory.json";
import ruSettings from "@/locales/ru/settings.json";
import ruTemplates from "@/locales/ru/templates.json";

export const defaultNS = "common";

export const resources = {
	en: {
		common: enCommon,
		auth: enAuth,
		board: enBoard,
		goals: enGoals,
		memory: enMemory,
		settings: enSettings,
		templates: enTemplates,
	},
	ru: {
		common: ruCommon,
		auth: ruAuth,
		board: ruBoard,
		goals: ruGoals,
		memory: ruMemory,
		settings: ruSettings,
		templates: ruTemplates,
	},
} as const;

export const SUPPORTED_LANGUAGES = ["ru", "en"] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

const STORAGE_KEY = "lang";

function getInitialLanguage(): SupportedLanguage {
	try {
		const stored = localStorage.getItem(STORAGE_KEY);
		if (stored === "ru" || stored === "en") return stored;
	} catch {
		// localStorage unavailable (e.g. SSR / private mode) — fall through
	}
	return "ru";
}

i18n.use(initReactI18next).init({
	resources,
	lng: getInitialLanguage(),
	fallbackLng: "en",
	defaultNS,
	ns: ["common", "auth", "board", "goals", "memory", "settings", "templates"],
	interpolation: {
		// React already escapes values, so disable i18next's escaping.
		escapeValue: false,
	},
	returnNull: false,
});

i18n.on("languageChanged", (lng) => {
	try {
		localStorage.setItem(STORAGE_KEY, lng);
	} catch {
		// ignore persistence failures
	}
	if (typeof document !== "undefined") {
		document.documentElement.lang = lng;
	}
});

export default i18n;
