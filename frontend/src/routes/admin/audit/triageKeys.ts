// Keyboard triage for the content audit: j / k move between findings, Enter or
// Space expands one, a accepts it, o opens its chapter in a new tab. Pure, so
// the key map is tested without rendering the page.

export type TriageAction = 'next' | 'prev' | 'toggle' | 'accept' | 'open';

/** The key legend the page shows — one list, so it can't drift from the map. */
export const TRIAGE_KEYS: { keys: string[]; label: string }[] = [
	{ keys: ['j', 'k'], label: 'next / previous' },
	{ keys: ['Enter', 'Space'], label: 'expand' },
	{ keys: ['a'], label: 'accept' },
	{ keys: ['o'], label: 'open chapter' }
];

const KEY_ACTIONS: Record<string, TriageAction> = {
	j: 'next',
	k: 'prev',
	a: 'accept',
	o: 'open',
	Enter: 'toggle',
	' ': 'toggle'
};

/** True while the user is typing somewhere a letter is text, not a command. */
export function isTypingTarget(target: EventTarget | null): boolean {
	if (!(target instanceof HTMLElement)) return false;
	if (target.isContentEditable) return true;
	return target.matches('input, textarea, select');
}

// Controls whose own Enter / Space must keep their native meaning (follow the
// link, press the button, fold the check).
const NATIVE_ACTIVATION = 'a[href], button, summary, input, select, textarea';

export function triageAction(e: {
	key: string;
	target: EventTarget | null;
	metaKey?: boolean;
	ctrlKey?: boolean;
	altKey?: boolean;
}): TriageAction | null {
	if (e.metaKey || e.ctrlKey || e.altKey) return null;
	if (isTypingTarget(e.target)) return null;
	const action = KEY_ACTIONS[e.key];
	if (!action) return null;
	if (action === 'toggle' && e.target instanceof Element && e.target.matches(NATIVE_ACTIVATION)) {
		return null;
	}
	return action;
}

/** The index focus moves to. From nothing focused (-1), `next` lands on the
 *  first stop and `prev` on the last; otherwise it clamps at either end. */
export function stepIndex(current: number, delta: 1 | -1, count: number): number {
	if (count <= 0) return -1;
	if (current < 0 || current >= count) return delta > 0 ? 0 : count - 1;
	return Math.min(count - 1, Math.max(0, current + delta));
}
