import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BoardMetaInfo } from "../components/BoardMetaInfo";
import type { UserMetaResponse } from "../types";

const fullMeta: UserMetaResponse = {
	timezone: "America/New_York",
	locale: "en-US",
	current_datetime: "2025-07-15T14:30:00Z",
	location: { city: "New York", country: "US" },
	device_type: "desktop",
};

describe("BoardMetaInfo", () => {
	it("renders date and location when both are present", () => {
		render(<BoardMetaInfo userMeta={fullMeta} />);
		expect(screen.getByText(/Generated on/)).toBeInTheDocument();
		expect(screen.getByText(/Jul 15, 2025|15 Jul 2025/)).toBeInTheDocument();
		expect(screen.getByText("New York, US")).toBeInTheDocument();
	});

	it("renders only date when location is null", () => {
		const meta: UserMetaResponse = { ...fullMeta, location: null };
		render(<BoardMetaInfo userMeta={meta} />);
		expect(screen.getByText(/Generated on/)).toBeInTheDocument();
		expect(screen.queryByText(/New York/)).not.toBeInTheDocument();
	});

	it("renders only date when location has all null fields", () => {
		const meta: UserMetaResponse = {
			...fullMeta,
			location: { city: null, country: null },
		};
		render(<BoardMetaInfo userMeta={meta} />);
		expect(screen.getByText(/Generated on/)).toBeInTheDocument();
		// Location span with MapPin icon should not be rendered
		expect(screen.queryByText("New York, US")).not.toBeInTheDocument();
	});

	it("renders location with only city", () => {
		const meta: UserMetaResponse = {
			...fullMeta,
			location: { city: "London", country: null },
		};
		render(<BoardMetaInfo userMeta={meta} />);
		expect(screen.getByText("London")).toBeInTheDocument();
	});

	it("renders location with only country", () => {
		const meta: UserMetaResponse = {
			...fullMeta,
			location: { city: null, country: "GB" },
		};
		render(<BoardMetaInfo userMeta={meta} />);
		expect(screen.getByText("GB")).toBeInTheDocument();
	});

	it("returns null when no date and no location", () => {
		const meta: UserMetaResponse = {
			...fullMeta,
			current_datetime: "",
			location: null,
		};
		const { container } = render(<BoardMetaInfo userMeta={meta} />);
		expect(container.firstChild).toBeNull();
	});

	it("still renders when given an invalid datetime string", () => {
		const meta: UserMetaResponse = {
			...fullMeta,
			current_datetime: "not-a-date",
			location: null,
		};
		render(<BoardMetaInfo userMeta={meta} />);
		// new Date("not-a-date") produces "Invalid Date" from toLocaleDateString
		expect(screen.getByText(/Generated on/)).toBeInTheDocument();
	});
});
