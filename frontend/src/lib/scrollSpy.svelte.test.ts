import { describe, it, expect, vi, afterEach } from 'vitest';
import { scrollSpy } from './scrollSpy.svelte';

// `scrollSpy` registers an $effect, so these run inside an effect root.
const click = (over: Partial<MouseEvent> = {}) =>
	({
		button: 0,
		metaKey: false,
		ctrlKey: false,
		shiftKey: false,
		altKey: false,
		preventDefault: vi.fn(),
		...over
	}) as unknown as MouseEvent;

function withSpy(run: (spy: ReturnType<typeof scrollSpy>) => void) {
	const cleanup = $effect.root(() => run(scrollSpy(() => [])));
	cleanup();
}

describe('spy.jump — the sticky sub-nav click handler', () => {
	afterEach(() => vi.restoreAllMocks());

	it("keeps SvelteKit's history state, lights the tab and writes the hash", () => {
		// A null state here erased the router's index and broke Back (#4900).
		history.replaceState({ 'sveltekit:history': 3 }, '', '/scripture/');
		withSpy((spy) => {
			const e = click();
			spy.jump(e, 'section-paul');
			expect(e.preventDefault).toHaveBeenCalled();
			expect(history.state).toEqual({ 'sveltekit:history': 3 });
			expect(location.hash).toBe('#section-paul');
			expect(spy.active).toBe('section-paul');
		});
	});

	it('leaves a modified or non-primary click to the browser (new tab)', () => {
		for (const over of [{ metaKey: true }, { ctrlKey: true }, { shiftKey: true }, { button: 1 }]) {
			withSpy((spy) => {
				const e = click(over);
				spy.jump(e, 'books');
				expect(e.preventDefault).not.toHaveBeenCalled();
				expect(spy.active).toBe('');
			});
		}
	});

	it('does not light a target that is not a tab', () => {
		withSpy((spy) => {
			spy.jump(click(), 'languages', { track: false });
			expect(spy.active).toBe('');
		});
	});

	it('still jumps when the browser refuses replaceState', () => {
		const target = document.createElement('section');
		target.id = 'faq';
		target.scrollIntoView = vi.fn();
		document.body.append(target);
		vi.spyOn(history, 'replaceState').mockImplementation(() => {
			throw new DOMException('too many calls', 'SecurityError');
		});
		withSpy((spy) => {
			expect(() => spy.jump(click(), 'faq')).not.toThrow();
			expect(target.scrollIntoView).toHaveBeenCalled();
		});
		target.remove();
	});
});
