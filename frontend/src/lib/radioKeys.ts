/**
 * Arrow-key movement for a radio group of buttons: the arrows step the
 * choice (wrapping at the ends), Left/Right swap in a right-to-left context,
 * and focus follows the new choice. Each option carries `[attr]="<value>"`.
 * The current value is read at the keypress, so one handler serves for the
 * component's lifetime. PalettePicker and QuickSettings both use it.
 */
export function radioKeys<T extends string>(
	all: readonly T[],
	current: () => T,
	set: (v: T) => void,
	attr: string
): (e: KeyboardEvent) => void {
	return (e) => {
		const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
		if (!step) return;
		e.preventDefault();
		const host = e.currentTarget as HTMLElement;
		const rtl = getComputedStyle(host).direction === 'rtl';
		const horizontal = e.key === 'ArrowLeft' || e.key === 'ArrowRight';
		const i = all.indexOf(current());
		const next = all[(i + (rtl && horizontal ? -step : step) + all.length) % all.length];
		set(next);
		host.querySelector<HTMLElement>(`[${attr}='${next}']`)?.focus();
	};
}
