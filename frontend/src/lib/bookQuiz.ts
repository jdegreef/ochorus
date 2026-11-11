import type { QuizQuestion } from '$lib/library-public';

/** How many of `picks` (the option chosen per question, by index) are right. */
export function quizScore(questions: QuizQuestion[], picks: (number | undefined)[]): number {
	return questions.reduce((n, q, i) => n + (picks[i] === q.answer_index ? 1 : 0), 0);
}

/** The questions a quiz can actually ask: four options and an answer among
 *  them. A malformed row from an API behind this build is skipped, never shown
 *  as a question with no right answer. */
export function playableQuiz(quiz: QuizQuestion[] | undefined): QuizQuestion[] {
	return (quiz ?? []).filter(
		(q) =>
			q?.question &&
			Array.isArray(q.options) &&
			q.options.length >= 2 &&
			Number.isInteger(q.answer_index) &&
			q.answer_index >= 0 &&
			q.answer_index < q.options.length
	);
}
