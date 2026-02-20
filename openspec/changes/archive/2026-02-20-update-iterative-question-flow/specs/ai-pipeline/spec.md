## MODIFIED Requirements
### Requirement: Adaptive Follow-up Question Generation
The system SHALL support generating unlimited rounds of follow-up questions after the user submits initial answers. Each round SHALL generate 2-4 progressively deeper questions based on the full history of previous Q&A rounds. The follow-up generation SHALL reuse the question generation node with additional context: the original classification, all previous rounds of questions and answers (ordered), and the formatted `user_meta` context (when available). The AI SHALL always generate a new batch of questions after each answer submission — the user decides when to stop by clicking "Generate Board". Follow-up questions SHALL have IDs prefixed with the round number (e.g., round 2: "r2q1", "r2q2"; round 3: "r3q1", "r3q2") to distinguish them from initial questions and maintain uniqueness across rounds. The question generation prompt SHALL include explicit instructions to: (a) not repeat topics already covered in previous rounds, (b) drill deeper into partially covered dimensions based on previous answers, (c) explore new dimensions if all current ones are sufficiently covered, and (d) generate 2-4 questions per follow-up round (fewer than the initial 3-7). When the Q&A history exceeds 5 rounds, the system SHALL summarize earlier rounds in the prompt to manage prompt size while preserving essential context.

#### Scenario: Follow-up questions generated after each round
- **WHEN** a user submits answers for any round (including round 1, 2, 3, etc.)
- **THEN** the follow-up generation produces 2-4 new questions that deepen understanding of the goal

#### Scenario: Progressive deepening avoids repetition
- **WHEN** the user has already answered questions about budget and timeline in previous rounds
- **THEN** the new round's questions do NOT ask about budget or timeline again, instead drilling into uncovered dimensions or asking more specific follow-ups on covered topics

#### Scenario: Questions become more specific over rounds
- **WHEN** round 1 asked "What is your budget range?" and the user answered "$5,000-$15,000"
- **AND** round 3 is being generated
- **THEN** the AI MAY ask a more specific question like "How do you want to split the $5,000-$15,000 between housing deposit, moving costs, and initial living expenses?"

#### Scenario: Round-specific question ID prefixes
- **WHEN** follow-up questions are generated for round 4
- **THEN** question IDs are "r4q1", "r4q2", etc.

#### Scenario: Large history summarized in prompt
- **WHEN** the user has completed 6 rounds of Q&A and round 7 is being generated
- **THEN** rounds 1-4 are summarized into a concise context block while rounds 5-6 are included in full detail

#### Scenario: Follow-up generation uses user meta context
- **WHEN** follow-up questions are generated for a goal with `user_meta`
- **THEN** the follow-up generation prompt includes the formatted user context block

## ADDED Requirements
### Requirement: Readiness Assessment
The system SHALL return a readiness assessment alongside each batch of generated questions (both initial and follow-up rounds). The readiness assessment SHALL conform to a Pydantic schema (`ReadinessAssessment`) containing: `score` (float 0.0-1.0 representing overall board generation readiness), `covered_dimensions` (list of strings — dimensions from the classification that are sufficiently covered by collected answers), `uncovered_dimensions` (list of strings — dimensions that still lack information), and `summary` (string — one sentence describing the current readiness state in the detected language). The readiness assessment SHALL be computed as part of the question generation LLM call (not a separate call) by extending the question generation structured output schema to include a `readiness` field. The `score` SHALL reflect the proportion of identified dimensions covered and the quality/specificity of answers. A score of 0.8+ indicates the AI has enough context for a high-quality board. A score below 0.4 indicates significant gaps remain. The assessment SHALL be in the same language as the goal.

#### Scenario: Readiness returned with initial questions
- **WHEN** the question generation node produces initial questions for a relocation goal with dimensions ["timeline", "budget", "housing", "logistics"]
- **THEN** the output includes a readiness assessment with score near 0.0, all dimensions in `uncovered_dimensions`, empty `covered_dimensions`, and a summary like "No answers collected yet. Answer the questions below to improve board quality."

#### Scenario: Readiness improves after answering initial questions
- **WHEN** the follow-up generation runs after the user answered questions about budget and timeline
- **THEN** the readiness assessment includes "budget" and "timeline" in `covered_dimensions`, "housing" and "logistics" in `uncovered_dimensions`, and a score around 0.4-0.6

#### Scenario: High readiness after multiple rounds
- **WHEN** the user has completed 4 rounds covering all classification dimensions thoroughly
- **THEN** the readiness assessment has a score of 0.85+, most dimensions in `covered_dimensions`, and a summary encouraging the user to generate

#### Scenario: Readiness in detected language
- **WHEN** the goal was classified with language "ru"
- **THEN** the readiness `summary` is in Russian

### Requirement: Iterative Question Generation Prompt
The question generation prompt in `app/domains/ai/prompts/questions.py` SHALL be updated to support iterative deepening. The prompt SHALL accept: the classification output, the full Q&A history (all previous rounds), the current round number, the formatted `user_meta` context, and the memory context. The prompt SHALL instruct the AI to: generate 2-4 questions for follow-up rounds (3-7 for the initial round), avoid repeating topics covered in previous rounds, progressively deepen questions based on accumulated answers, include a readiness assessment evaluating dimension coverage, and produce all content in the detected language. The prompt SHALL include a structured section listing which dimensions are covered vs. uncovered based on the Q&A history.

#### Scenario: Initial round prompt generates 3-7 questions
- **WHEN** the question generation prompt is invoked for round 1 (no previous Q&A history)
- **THEN** the prompt instructs the AI to generate 3-7 questions and an initial readiness assessment

#### Scenario: Follow-up round prompt generates 2-4 questions
- **WHEN** the question generation prompt is invoked for round 3 with 2 previous rounds of Q&A
- **THEN** the prompt instructs the AI to generate 2-4 questions that deepen understanding, and the full Q&A history is included in the prompt

#### Scenario: Prompt includes dimension coverage analysis
- **WHEN** the question generation prompt is invoked for any follow-up round
- **THEN** the prompt includes a section listing which classification dimensions are covered by previous answers and which remain uncovered
