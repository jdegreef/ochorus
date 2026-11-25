/**
 * Where a work's admin page lives, for the public surfaces that link an admin
 * to it (the command palette, the book and sermon pages).
 *
 * Its own small module on purpose: `library-admin.ts` is ~2,500 lines of admin
 * API helpers, and the palette and the reader pages must not pull it into the
 * public bundle just to build a URL. `adminBookHref` there stays the admin's own
 * copy; `adminLinks.test.ts` holds the two to the same shape.
 */
import type { CatalogKind } from './adminCatalog';

export type AdminWorkKind = 'book' | 'sermon';

export const adminWorkHref = (kind: AdminWorkKind, slug: string): string =>
	`/admin/${kind}s/${encodeURIComponent(slug)}`;

/** One admin inventory list (`/admin/books`, `/admin/authors`, …), searched
 *  for `q` — the palette's way to an item whose kind has no admin page of its
 *  own. (A type-only import: erased at build, so the bundle point above holds.) */
export const adminListHref = (kind: CatalogKind, q: string): string =>
	`/admin/${kind}?q=${encodeURIComponent(q)}`;

/** One translation open in the review queue, its side-by-side panel showing
 *  (the queue opens the item `slug` names). */
export const adminReviewHref = (
	kind: 'book' | 'sermon' | 'bio',
	slug: string,
	language: string
): string => `/admin/review?${new URLSearchParams({ kind, language, slug })}`;
