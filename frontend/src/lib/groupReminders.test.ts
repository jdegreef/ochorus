import { beforeEach, describe, expect, it } from 'vitest';
import { GROUP_REMIND_KEY, groupReminders } from './groupReminders.svelte';

beforeEach(() => {
	localStorage.clear();
	groupReminders.all = {};
});

describe('group reminders', () => {
	it('records a list reminder on the device, and forgets it on removal', () => {
		groupReminders.set('missions', 'weekly-0@09:00');
		groupReminders.set('', 'daily@07:00');
		expect(groupReminders.get('missions')).toBe('weekly-0@09:00');
		expect(groupReminders.get('')).toBe('daily@07:00');
		expect(JSON.parse(localStorage.getItem(GROUP_REMIND_KEY)!)).toEqual({
			missions: 'weekly-0@09:00',
			other: 'daily@07:00'
		});
		groupReminders.set('missions', '');
		expect(groupReminders.get('missions')).toBe('');
		expect(groupReminders.get('family')).toBe('');
	});
});
