import { readJSON, writeJSON } from './persisted';
import { REMOVALS_KEY } from './reading-schema';

/**
 * Removals the account hasn't confirmed yet — a heart taken off, or a work
 * removed from the Bookshelf — kept until the server has them.
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
 * incoming positions / hearts to tell a stale copy from a newer act.
 * Stored as `"domain:kind:slug" -> at`; none of the three contain ':'.
 */
export type RemovalDomain = 'progress' | 'favorite';

export interface PendingRemoval {
	domain: RemovalDomain;
	kind: string;
	slug: string;
	at: number;
}

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
	return Object.entries(read()).flatMap(([key, at]) => {
		const [domain, kind, ...rest] = key.split(':');
		const slug = rest.join(':');
		if ((domain !== 'progress' && domain !== 'favorite') || !kind || !slug) return [];
		return [{ domain, kind, slug, at }];
	});
}

/** Drop the removals a merge just delivered — each only if unchanged since. */
export function clearSent(sent: PendingRemoval[]): void {
	for (const r of sent) clearPending(r.domain, r.kind, r.slug, r.at);
}
