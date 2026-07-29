// Named church-history buckets derived purely from an author's birth year (no
// per-author data). Shared by the biographies index and the per-era landing
// pages (/biographies/era/<id>) so both agree on where a writer falls. The
// label characterises the era; the year range beside it keeps the
// generalisation honest. Undated writers (Ochorus' contemporary contributors)
// fall to a trailing "Contemporary" bucket.

export type EraId = 'early' | 'puritans' | 'awakenings' | 'missionary' | 'modern' | 'contemporary';

export type Era = { id: EraId; k: string; until: number | null; range: string };

// `until` is the exclusive upper bound on birth year and is the single source
// of truth; `range` is only its display form, kept on the same row so the two
// can't drift. `until: null` marks the undated bucket.
//
// The first cut is 1480, not 1500: the Reformers had to land under "Puritans &
// Reformers", and Luther (b. 1483), Zwingli (1484), Cranmer (1489) and Tyndale
// (1494) are all plausible additions here. A 1500 cut would have filed them
// under "The Early Church & Middle Ages" — relocating the very mislabel this
// bucket was added to fix (Augustine, b. 354, reading as a Puritan).
export const ERAS: Era[] = [
	{ id: 'early', k: 'bios.eraEarly', until: 1480, range: '–1479' },
	{ id: 'puritans', k: 'bios.eraPuritans', until: 1700, range: '1480–1699' },
	{ id: 'awakenings', k: 'bios.eraAwakenings', until: 1800, range: '1700–1799' },
	{ id: 'missionary', k: 'bios.eraMissionary', until: 1900, range: '1800–1899' },
	{ id: 'modern', k: 'bios.eraModern', until: Infinity, range: '1900–' },
	{ id: 'contemporary', k: 'bios.eraContemporary', until: null, range: '' }
];

export const eraOf = (birth: number | null): EraId =>
	birth == null ? 'contemporary' : ERAS.find((e) => e.until != null && birth < e.until)!.id;

export const eraById = (id: string): Era | undefined => ERAS.find((e) => e.id === id);
