/**
 * Small display-string helpers shared across the reader UI.
 *
 * Both had been copy-pasted into many components (initials into the author
 * cards, sermon and author pages and the account avatar; unslug into the data
 * export, reading stats and the favorites surfaces). A change to either rule —
 * how a two-word name abbreviates, how a slug is humanised — has to be made in
 * one place, so single-source them here.
 */

/**
 * A name's initials, up to two letters, uppercased — "Andrew Murray" → "AM",
 * "Spurgeon" → "S". Used for the avatar fallback when an author has no portrait.
 */
export function initials(name: string): string {
	return name
		.split(' ')
		.filter(Boolean)
		.map((w) => w[0])
		.slice(0, 2)
		.join('')
		.toUpperCase();
}

/**
 * A slug rendered as a human label — "gleanings-among-the-sheaves" → "Gleanings
 * Among The Sheaves". The last-resort title for a favorite whose work can't be
 * resolved from the catalog (e.g. no row in the current language), so nothing
 * saved is ever shown as a bare slug.
 */
export function unslug(slug: string): string {
	return slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
