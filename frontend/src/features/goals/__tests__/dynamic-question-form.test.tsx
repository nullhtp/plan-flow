import { render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import type { QuestionSchema, ReadinessSchema } from "@/api/generated/model";

// jsdom does not implement scrollIntoView, which the form calls for follow-up rounds.
beforeAll(() => {
	Element.prototype.scrollIntoView = vi.fn();
});

const isSimpleModeMock = vi.fn();
vi.mock("@/shared/hooks/use-simple-mode", () => ({
	useSimpleMode: () => ({ isSimpleMode: isSimpleModeMock(), isLoading: false }),
}));

import { DynamicQuestionForm, type Round } from "../components/dynamic-question-form";

const q1 = {
	id: "q1",
	text: "What is your budget?",
	type: "text",
	required: false,
} as QuestionSchema;
const q2 = {
	id: "q2",
	text: "When do you want to move?",
	type: "text",
	required: false,
} as QuestionSchema;

const rounds: Round[] = [
	{ round: 1, questions: [q1], answers: { q1: "5000 EUR" }, readiness: null },
	{ round: 2, questions: [q2], answers: {}, readiness: null },
];

const readiness = { score: 0.8, summary: "Looking good" } as ReadinessSchema;

function renderForm() {
	return render(
		<DynamicQuestionForm
			goalTitle="Move to Lisbon"
			rounds={rounds}
			activeQuestions={[q2]}
			currentRound={2}
			readiness={readiness}
			hasCompletedRounds
			onSubmitAnswers={vi.fn()}
			onEditRound={vi.fn()}
			onGenerate={vi.fn()}
			isPending={false}
			isLoadingFollowUp={false}
		/>,
	);
}

describe("DynamicQuestionForm Simple mode", () => {
	it("shows readiness, Round labels and editable rounds when Simple mode is off", () => {
		isSimpleModeMock.mockReturnValue(false);
		renderForm();
		expect(screen.getByText("Round 1")).toBeInTheDocument();
		expect(screen.getByText("Round 2")).toBeInTheDocument();
		expect(screen.getByText("Edit")).toBeInTheDocument();
		expect(screen.getByText("Looking good")).toBeInTheDocument();
		expect(screen.queryByText("Ready to generate")).not.toBeInTheDocument();
	});

	it("hides readiness/Edit, shows plain summary and friendly labels in Simple mode", () => {
		isSimpleModeMock.mockReturnValue(true);
		renderForm();
		expect(screen.getByText("Ready to generate")).toBeInTheDocument();
		expect(screen.getByText("Your answers")).toBeInTheDocument();
		expect(screen.getByText("5000 EUR")).toBeInTheDocument();
		expect(screen.getByText("A few more questions")).toBeInTheDocument();
		expect(screen.queryByText("Edit")).not.toBeInTheDocument();
		expect(screen.queryByText("Round 1")).not.toBeInTheDocument();
		expect(screen.queryByText("Looking good")).not.toBeInTheDocument();
	});
});
