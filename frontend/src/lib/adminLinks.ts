/**
 * Where a work's admin page lives, for the public surfaces that link an admin
 * to it (the command palette, the book and sermon pages).
 *
 * Its own small module on purpose: `library-admin.ts` is ~2,500 lines of admin
 * API helpers, and the palette and the reader pages must not pull it into the
 * public bundle just to build a URL. `adminBookHref` there stays the admin's own
 * copy; `adminLinks.test.ts` holds the two to the same shape.
 */
export type AdminWorkKind = 'book' | 'sermon';

export const adminWorkHref = (kind: AdminWorkKind, slug: string): string =>
	`/admin/${kind}s/${encodeURIComponent(slug)}`;
