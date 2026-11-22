/**
 * The Key Teachings: one Ochorus companion per writer, each slugged
 * `key-teachings-of-<writer-slug>`. The slug convention IS the link from a
 * volume to the person it is about (as `-children` / `-teens` link a
 * young-reader edition to its full text) — nothing in the model joins them.
 */
export const KEY_TEACHINGS = "key-teachings";

const PREFIX = "key-teachings-of-";

/** The writer a Key Teachings volume is about, from its slug. */
export const subjectSlug = (bookSlug: string): string =>
  bookSlug.startsWith(PREFIX) ? bookSlug.slice(PREFIX.length) : bookSlug;
