import { describe, expect, it } from 'vitest';
import { playableQuiz, quizScore } from './bookQuiz';
import type { QuizQuestion } from './library-public';

const q = (answer_index: number, options = ['a', 'b', 'c', 'd']): QuizQuestion => ({
	question: 'Q?',
	options,
	answer_index,
	explanation: 'Because.',
	chapter: 1
});

describe('quizScore', () => {
	it('counts the right picks and not the unanswered', () => {
		expect(quizScore([q(1), q(2), q(0)], [1, 3])).toBe(1);
		expect(quizScore([q(1), q(2)], [1, 2])).toBe(2);
		expect(quizScore([q(1)], [])).toBe(0);
	});
});

describe('playableQuiz', () => {
	it('drops a question whose answer is not among its options', () => {
		expect(playableQuiz([q(1), q(4), q(-1), q(0, ['only'])])).toEqual([q(1)]);
	});
	it('reads an absent quiz as none', () => {
		expect(playableQuiz(undefined)).toEqual([]);
	});
});
