import { readJSON, writeJSON } from './persisted';
import { REMOVALS_KEY } from './reading-schema';

/**
 * Removals the account hasn't confirmed yet — a heart taken off, a work
 * removed from the Bookshelf, or a bookmark — kept until the server has them.
 *
 * The server keeps a tombstone per removal (reading.models.Removal), so a
 * device still holding the thing can't merge it back. But a removal only gets
 * there if its live DELETE lands; offline, or on a failed request, it used to
 * be lost, and the next merge brought the thing straight back. So every
 * removal is written here first, the live DELETE clears it on success, and
 * `mergeOnSignIn` carries whatever is left (`removed`) — dropping only what
 * the server acknowledges applying.
 *
 * `at` is this device's clock at the removal: the server compares it with the
 * incoming positions / hearts / bookmarks to tell a stale copy from a newer
 * act. Stored as `"domain:kind:target" -> at`. The target is the slug, except
 * for a bookmark, which is a spot in a work: `bookmarkTarget` makes it
 * `slug:order:p` (slugs never contain ':'), and the merge row splits it back
 * into the `chapter_order` / `paragraph_index` the API expects.
 */
export type RemovalDomain = 'progress' | 'favorite' | 'bookmark';

export interface PendingRemoval {
	domain: RemovalDomain;
	kind: string;
	slug: string;
	/** Bookmarks only: the spot. */
	chapter_order?: number;
	paragraph_index?: number;
	at: number;
}

/** The removal target for a bookmark at (order, p) in a work. */
export const bookmarkTarget = (slug: string, order: number, p: number) => `${slug}:${order}:${p}`;

type Store = Record<string, number>;

const keyOf = (domain: RemovalDomain, kind: string, slug: string) => `${domain}:${kind}:${slug}`;
const read = (): Store => readJSON<Store>(REMOVALS_KEY, {});

export function addPending(domain: RemovalDomain, kind: string, slug: string, at = Date.now()): number {
	const store = read();
	store[keyOf(domain, kind, slug)] = at;
	writeJSON(REMOVALS_KEY, store);
	return at;
}

export function pendingAt(domain: RemovalDomain, kind: string, slug: string): number | null {
	return read()[keyOf(domain, kind, slug)] ?? null;
}

/** Forget one pending removal — it landed, or the reader took it back. With
 *  `onlyAt`, only if it is still that removal (a newer one made meanwhile, e.g.
 *  remove → undo → remove, must survive the older one's acknowledgement). */
export function clearPending(
	domain: RemovalDomain,
	kind: string,
	slug: string,
	onlyAt?: number
): void {
	const store = read();
	const key = keyOf(domain, kind, slug);
	if (!(key in store) || (onlyAt !== undefined && store[key] !== onlyAt)) return;
	delete store[key];
	writeJSON(REMOVALS_KEY, store);
}

export function pendingRemovals(): PendingRemoval[] {
	return Object.entries(read()).flatMap(([key, at]): PendingRemoval[] => {
		const [domain, kind, slug, ...spot] = key.split(':');
		if (!kind || !slug) return [];
		if (domain === 'bookmark') {
			const [order, p] = spot.map(Number);
			if (spot.length !== 2 || !Number.isInteger(order) || !Number.isInteger(p)) return [];
			return [{ domain, kind, slug, chapter_order: order, paragraph_index: p, at }];
		}
		if ((domain !== 'progress' && domain !== 'favorite') || spot.length) return [];
		return [{ domain, kind, slug, at }];
	});
}

/** Drop the removals a merge just delivered — each only if unchanged since. */
export function clearSent(sent: PendingRemoval[]): void {
	for (const r of sent) {
		const target =
			r.domain === 'bookmark'
				? bookmarkTarget(r.slug, r.chapter_order ?? 0, r.paragraph_index ?? 0)
				: r.slug;
		clearPending(r.domain, r.kind, target, r.at);
	}
}
