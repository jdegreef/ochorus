import { describe, expect, it } from 'vitest';
import { TEACHER_NEEDS, teacherNeeds } from './keyTeachings';

const vol = (subject: string) => ({ slug: `key-teachings-of-${subject}` });

describe('teacherNeeds', () => {
	it('lists each need with its teachers, in the curated order', () => {
		const all = TEACHER_NEEDS.flatMap((n) => n.teachers.map(vol));
		const needs = teacherNeeds(all);
		expect(needs.map((n) => n.id)).toEqual(TEACHER_NEEDS.map((n) => n.id));
		expect(needs[0].books.map((b) => b.slug)).toEqual(
			TEACHER_NEEDS[0].teachers.map((s) => vol(s).slug)
		);
	});
	it('skips missing volumes and drops a need left with one teacher', () => {
		const needs = teacherNeeds([vol('e-m-bounds'), vol('andrew-murray'), vol('john-owen')]);
		expect(needs.map((n) => n.id)).toEqual(['pray']);
	});
});
