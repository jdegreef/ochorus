import type { ParamMatcher } from '@sveltejs/kit';
import { CATALOG, type CatalogKind } from '$lib/adminCatalog';

/** `/admin/<kind>` for the inventory lists `$lib/adminCatalog` defines — one
 *  route for every kind, so adding a kind is a `CATALOG` entry, not a folder. */
export const match = ((param: string): param is CatalogKind =>
	Object.hasOwn(CATALOG, param)) satisfies ParamMatcher;
