/**
 * The shortest shelf that opens with a "Filter …" field (page-design:
 * browse-shelf anatomy, step 5). Below it the row is left out, not drawn
 * empty: a handful of cards is quicker to scan than to search.
 */
export const SHELF_SEARCH_MIN = 12;

/** Whether `q` (already trimmed and lowercased; '' = no filter) occurs in any
 *  of the given fields. */
export const matchesQuery = (q: string, ...fields: (string | null | undefined)[]): boolean =>
	!q || fields.some((f) => f?.toLowerCase().includes(q));
