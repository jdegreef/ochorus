/**
 * Presence flags: an attribute on <html> or <body> that says "a component of
 * kind X is mounted", for the few rules that restyle the page around a piece
 * of chrome (the tab bar sheds the top bar's controls, the read bar pads the
 * body's foot, a reading footer hides the floating "+").
 *
 * Those rules used to be `:root:has(.tabbar) …` / `body:has(.read-bar)`. A
 * `:has()` anchored at the document root makes every insertion or removal of
 * a matching element anywhere re-check the root and restyle the whole page —
 * the read bar toggles on scroll — which is style-recalc time on the very
 * interactions INP measures. An attribute changes only when the component
 * mounts or unmounts, and the rules keyed on it are ordinary selectors.
 *
 * Reference-counted, so two holders of one flag (a bar torn down while its
 * replacement mounts) never clear it under each other.
 */
const holders = new Map<string, number>();

function key(el: Element, attr: string): string {
	return `${el === document.documentElement ? 'html' : 'body'}|${attr}`;
}

/** Set `attr` on `el` while held; call the returned function to release. */
export function holdFlag(el: HTMLElement, attr: string): () => void {
	const k = key(el, attr);
	holders.set(k, (holders.get(k) ?? 0) + 1);
	el.setAttribute(attr, '');
	let released = false;
	return () => {
		if (released) return;
		released = true;
		const left = (holders.get(k) ?? 1) - 1;
		if (left > 0) holders.set(k, left);
		else {
			holders.delete(k);
			el.removeAttribute(attr);
		}
	};
}

/** The <html> attribute that stands for "a page of reading text is open" — a
 *  chapter, a sermon, a life — held by those routes (app.css CANDLELIGHT). */
export const READING_FLAG = 'data-reading';

/** The <html> attribute that stands for "the phone tab bar is in the DOM". */
export const TABBAR_FLAG = 'data-tabbar';

/**
 * Bake the tab-bar flag into a prerendered page (hooks.server), so a phone's
 * first paint — before any JavaScript — already hides the controls the bar
 * carries, as `:root:has(.tabbar)` did. Keyed on the bar's own markup, so it
 * says exactly what the old `:has()` said: the bar was rendered.
 */
export function markTabBar(html: string): string {
	if (!/<nav class="tabbar[\s"]/.test(html)) return html;
	return html.replace(/<html(?=[\s>])/, `<html ${TABBAR_FLAG}`);
}
