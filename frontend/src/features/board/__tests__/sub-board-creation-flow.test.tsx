import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { act, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Capture the mutation callbacks so tests can trigger them
let questionsOnSuccess: ((data: unknown) => void) | undefined;
let questionsOnError: (() => void) | undefined;
let generateOnSuccess: ((data: unknown) => void) | undefined;
let generateOnError: (() => void) | undefined;

const mockQuestionsMutate = vi.fn();
const mockGenerateMutate = vi.fn();

vi.mock("@/api/generated/boards/boards", () => ({
	getGetBoardEndpointApiBoardsBoardIdGetQueryKey: (id: string) => [`/api/boards/${id}`],
	useSubBoardQuestionsEndpointApiTasksTaskIdSubBoardQuestionsPost: (opts: {
		mutation: { onSuccess: (data: unknown) => void; onError: () => void };
	}) => {
		questionsOnSuccess = opts.mutation.onSuccess;
		questionsOnError = opts.mutation.onError;
		return { mutate: mockQuestionsMutate };
	},
	useGenerateSubBoardEndpointApiTasksTaskIdGenerateSubBoardPost: (opts: {
		mutation: { onSuccess: (data: unknown) => void; onError: () => void };
	}) => {
		generateOnSuccess = opts.mutation.onSuccess;
		generateOnError = opts.mutation.onError;
		return { mutate: mockGenerateMutate };
	},
}));

vi.mock("sonner", () => ({
	toast: { error: vi.fn(), success: vi.fn() },
}));

import { SubBoardCreationFlow } from "../components/SubBoardCreationFlow";

function createWrapper() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	return function Wrapper({ children }: { children: ReactNode }) {
		return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
	};
}

const mockQuestions = [
	{
		id: "sbq-1",
		text: "What approach?",
		type: "text",
		options: null,
		rationale: "Helps determine strategy",
		required: true,
	},
	{
		id: "sbq-2",
		text: "Priority level?",
		type: "select",
		options: ["High", "Medium", "Low"],
		rationale: "Sets urgency",
		required: true,
	},
];

describe("SubBoardCreationFlow", () => {
	beforeEach(() => {
		mockQuestionsMutate.mockClear();
		mockGenerateMutate.mockClear();
		questionsOnSuccess = undefined;
		questionsOnError = undefined;
		generateOnSuccess = undefined;
		generateOnError = undefined;
	});

	it("shows loading state initially and calls question API", () => {
		const onComplete = vi.fn();
		const onCancel = vi.fn();

		render(
			<SubBoardCreationFlow
				taskId="task-1"
				boardId="board-1"
				onComplete={onComplete}
				onCancel={onCancel}
			/>,
			{ wrapper: createWrapper() },
		);

		expect(screen.getByText("Preparing questions...")).toBeInTheDocument();
		expect(mockQuestionsMutate).toHaveBeenCalledWith({ taskId: "task-1" });
	});

	it("transitions to question form when questions load successfully", () => {
		const onComplete = vi.fn();
		const onCancel = vi.fn();

		render(
			<SubBoardCreationFlow
				taskId="task-1"
				boardId="board-1"
				onComplete={onComplete}
				onCancel={onCancel}
			/>,
			{ wrapper: createWrapper() },
		);

		// Simulate successful question load
		act(() => {
			questionsOnSuccess?.({ status: 200, data: { questions: mockQuestions } });
		});

		expect(screen.getByText("What approach?")).toBeInTheDocument();
		expect(screen.getByText("Priority level?")).toBeInTheDocument();
		expect(screen.getByText("Generate Board")).toBeInTheDocument();
	});

	it("calls onCancel when question loading fails", () => {
		const onComplete = vi.fn();
		const onCancel = vi.fn();

		render(
			<SubBoardCreationFlow
				taskId="task-1"
				boardId="board-1"
				onComplete={onComplete}
				onCancel={onCancel}
			/>,
			{ wrapper: createWrapper() },
		);

		act(() => {
			questionsOnError?.();
		});

		expect(onCancel).toHaveBeenCalled();
	});

	it("disables Generate Board button when required fields are empty", () => {
		const onComplete = vi.fn();
		const onCancel = vi.fn();

		render(
			<SubBoardCreationFlow
				taskId="task-1"
				boardId="board-1"
				onComplete={onComplete}
				onCancel={onCancel}
			/>,
			{ wrapper: createWrapper() },
		);

		act(() => {
			questionsOnSuccess?.({ status: 200, data: { questions: mockQuestions } });
		});

		const generateButton = screen.getByText("Generate Board");
		expect(generateButton).toBeDisabled();
	});

	it("enables Generate Board when required fields are filled and submits answers", () => {
		const onComplete = vi.fn();
		const onCancel = vi.fn();

		render(
			<SubBoardCreationFlow
				taskId="task-1"
				boardId="board-1"
				onComplete={onComplete}
				onCancel={onCancel}
			/>,
			{ wrapper: createWrapper() },
		);

		act(() => {
			questionsOnSuccess?.({ status: 200, data: { questions: mockQuestions } });
		});

		// Fill in text field
		const textInput = screen.getByPlaceholderText("Type your answer...");
		fireEvent.change(textInput, { target: { value: "Incremental approach" } });

		// Select a radio option
		const highOption = screen.getByText("High");
		fireEvent.click(highOption);

		const generateButton = screen.getByText("Generate Board");
		expect(generateButton).not.toBeDisabled();

		// Submit the form
		fireEvent.click(generateButton);

		expect(mockGenerateMutate).toHaveBeenCalledWith({
			taskId: "task-1",
			data: {
				answers: expect.arrayContaining([
					{ question_id: "sbq-1", value: "Incremental approach" },
					{ question_id: "sbq-2", value: "High" },
				]),
			},
		});
	});

	it("shows generating state after form submission", () => {
		const onComplete = vi.fn();
		const onCancel = vi.fn();

		render(
			<SubBoardCreationFlow
				taskId="task-1"
				boardId="board-1"
				onComplete={onComplete}
				onCancel={onCancel}
			/>,
			{ wrapper: createWrapper() },
		);

		act(() => {
			questionsOnSuccess?.({ status: 200, data: { questions: mockQuestions } });
		});

		// Fill in fields
		fireEvent.change(screen.getByPlaceholderText("Type your answer..."), {
			target: { value: "Test" },
		});
		fireEvent.click(screen.getByText("High"));
		fireEvent.click(screen.getByText("Generate Board"));

		expect(screen.getByText("Generating your board...")).toBeInTheDocument();
	});

	it("shows complete state after generation succeeds", async () => {
		const onComplete = vi.fn();
		const onCancel = vi.fn();

		render(
			<SubBoardCreationFlow
				taskId="task-1"
				boardId="board-1"
				onComplete={onComplete}
				onCancel={onCancel}
			/>,
			{ wrapper: createWrapper() },
		);

		act(() => {
			questionsOnSuccess?.({ status: 200, data: { questions: mockQuestions } });
		});

		fireEvent.change(screen.getByPlaceholderText("Type your answer..."), {
			target: { value: "Test" },
		});
		fireEvent.click(screen.getByText("High"));
		fireEvent.click(screen.getByText("Generate Board"));

		// Simulate generation success
		act(() => {
			generateOnSuccess?.({ status: 200 });
		});

		await waitFor(() => {
			expect(screen.getByText("Board created!")).toBeInTheDocument();
		});

		// Click Done button
		fireEvent.click(screen.getByText("Done"));
		expect(onComplete).toHaveBeenCalled();
	});

	it("reverts to question form on generation failure", () => {
		const onComplete = vi.fn();
		const onCancel = vi.fn();

		render(
			<SubBoardCreationFlow
				taskId="task-1"
				boardId="board-1"
				onComplete={onComplete}
				onCancel={onCancel}
			/>,
			{ wrapper: createWrapper() },
		);

		act(() => {
			questionsOnSuccess?.({ status: 200, data: { questions: mockQuestions } });
		});

		fireEvent.change(screen.getByPlaceholderText("Type your answer..."), {
			target: { value: "Test" },
		});
		fireEvent.click(screen.getByText("High"));
		fireEvent.click(screen.getByText("Generate Board"));

		// Simulate generation failure
		act(() => {
			generateOnError?.();
		});

		// Should revert to question form
		expect(screen.getByText("What approach?")).toBeInTheDocument();
		expect(screen.getByText("Generate Board")).toBeInTheDocument();
	});

	it("calls onCancel when cancel button is clicked during questions", () => {
		const onComplete = vi.fn();
		const onCancel = vi.fn();

		render(
			<SubBoardCreationFlow
				taskId="task-1"
				boardId="board-1"
				onComplete={onComplete}
				onCancel={onCancel}
			/>,
			{ wrapper: createWrapper() },
		);

		act(() => {
			questionsOnSuccess?.({ status: 200, data: { questions: mockQuestions } });
		});

		fireEvent.click(screen.getByText("Cancel"));
		expect(onCancel).toHaveBeenCalled();
	});
});
