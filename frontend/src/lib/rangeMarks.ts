import type { Mark, Segment } from './marks.svelte';

/**
 * DOM plumbing for text-range marks.
 *
 * Offsets are character positions in a paragraph's `textContent`, so they are
 * independent of layout AND of any <mark> wrappers we insert — computing and
 * applying both work on text nodes. Rendering is destructive-but-reversible:
 * each paragraph's pristine HTML is stashed in `dataset.pristine` the first
 * time we decorate it, and every render starts from that.
 */

/** Character offset of (node, nodeOffset) within `root`'s text content. */
function textOffset(root: Node, node: Node, nodeOffset: number): number {
	const range = document.createRange();
	range.selectNodeContents(root);
	range.setEnd(node, nodeOffset);
	return range.toString().length;
}

/**
 * Convert the current selection into per-paragraph segments relative to
 * `container`'s top-level blocks. Returns [] when the selection is collapsed
 * or outside the container.
 */
export function segmentsFromSelection(container: HTMLElement, sel: Selection): Segment[] {
	if (sel.rangeCount === 0 || sel.isCollapsed) return [];
	const range = sel.getRangeAt(0);
	const blocks = Array.from(container.children) as HTMLElement[];
	const out: Segment[] = [];
	for (let p = 0; p < blocks.length; p++) {
		const block = blocks[p];
		if (!range.intersectsNode(block)) continue;
		const textLen = (block.textContent ?? '').length;
		const s = block.contains(range.startContainer)
			? textOffset(block, range.startContainer, range.startOffset)
			: 0;
		const e = block.contains(range.endContainer)
			? textOffset(block, range.endContainer, range.endOffset)
			: textLen;
		if (e - s >= 1 && s < textLen) out.push({ p, s, e: Math.min(e, textLen) });
	}
	return out;
}

/** Walk text nodes and wrap [s, e) in <mark> elements. */
function wrapRange(block: HTMLElement, s: number, e: number, mark: Mark) {
	const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
	let pos = 0;
	const targets: { node: Text; from: number; to: number }[] = [];
	for (let node = walker.nextNode() as Text | null; node; node = walker.nextNode() as Text | null) {
		const len = node.data.length;
		const from = Math.max(s - pos, 0);
		const to = Math.min(e - pos, len);
		if (from < to) targets.push({ node, from, to });
		pos += len;
		if (pos >= e) break;
	}
	for (const { node, from, to } of targets) {
		const target = from > 0 ? node.splitText(from) : node;
		if (to - from < target.data.length) target.splitText(to - from);
		const el = document.createElement('mark');
		el.className = 'range-mark';
		el.dataset.markId = mark.id;
		if (mark.color) el.dataset.color = mark.color;
		if (mark.note) el.classList.add('has-note');
		target.parentNode?.replaceChild(el, target);
		el.appendChild(target);
	}
}

/**
 * Render `marks` into the container: restore each touched paragraph to its
 * pristine HTML, then wrap every segment. `onMarkClick` fires when a rendered
 * mark is clicked (used to open the note editor / removal UI).
 */
export function renderMarks(
	container: HTMLElement,
	list: Mark[],
	onMarkClick: (id: string, event: MouseEvent) => void
) {
	const blocks = Array.from(container.children) as HTMLElement[];
	// Restore pristine state everywhere we previously decorated.
	for (const block of blocks) {
		if (block.dataset.pristine !== undefined) {
			block.innerHTML = block.dataset.pristine;
		}
	}
	const byParagraph = new Map<number, Mark[]>();
	for (const m of list) {
		if (m.p >= 0 && m.p < blocks.length) {
			(byParagraph.get(m.p) ?? byParagraph.set(m.p, []).get(m.p))!.push(m);
		}
	}
	for (const [p, ms] of byParagraph) {
		const block = blocks[p];
		if (block.dataset.pristine === undefined) {
			block.dataset.pristine = block.innerHTML;
		}
		const textLen = (block.textContent ?? '').length;
		// Apply back-to-front so earlier offsets stay valid as nodes split.
		const ordered = [...ms].sort((a, b) => b.s - a.s);
		for (const m of ordered) {
			const end = m.e === -1 ? textLen : Math.min(m.e, textLen);
			if (m.s >= end) continue; // text changed since the mark was made
			wrapRange(block, m.s, end, m);
		}
	}
	// One delegated listener; replaced on each render via property assignment.
	container.onclick = (ev: MouseEvent) => {
		const el = (ev.target as HTMLElement).closest?.('mark.range-mark') as HTMLElement | null;
		if (el?.dataset.markId) {
			ev.preventDefault();
			onMarkClick(el.dataset.markId, ev);
		}
	};
}
