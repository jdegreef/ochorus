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

/**
 * "Find your teacher by need": the burdens a reader arrives with, each with
 * the writers in the series who wrote most for it. Editorial, so a list in
 * code; a teacher whose volume this language lacks is skipped, and a need left
 * with fewer than two teachers is dropped.
 */
export const TEACHER_NEEDS = [
  { id: "pray", k: "series.needPray", teachers: ["e-m-bounds", "andrew-murray", "r-a-torrey", "jeanne-guyon"] },
  { id: "suffer", k: "series.needSuffer", teachers: ["corrie-ten-boom", "elisabeth-elliot", "dietrich-bonhoeffer", "hannah-whitall-smith"] },
  { id: "holy", k: "series.needHoly", teachers: ["john-owen", "a-w-tozer", "john-wesley", "a-b-simpson"] },
  { id: "grace", k: "series.needGrace", teachers: ["martin-luther", "john-bunyan", "charles-h-spurgeon", "john-calvin"] },
  { id: "think", k: "series.needThink", teachers: ["c-s-lewis", "g-k-chesterton", "augustine-of-hippo", "athanasius-of-alexandria"] },
  { id: "mission", k: "series.needMission", teachers: ["hudson-taylor", "dwight-l-moody", "catherine-booth", "watchman-nee"] },
  { id: "revival", k: "series.needRevival", teachers: ["jonathan-edwards", "george-whitefield", "charles-finney", "martyn-lloyd-jones"] },
] as const;

export function teacherNeeds<B extends { slug: string }>(
  books: B[],
): { id: string; k: string; books: B[] }[] {
  const bySubject = new Map(books.map((b) => [subjectSlug(b.slug), b]));
  return TEACHER_NEEDS.map(({ id, k, teachers }) => ({
    id,
    k,
    books: teachers.flatMap((s) => bySubject.get(s) ?? []),
  })).filter((n) => n.books.length >= 2);
}
