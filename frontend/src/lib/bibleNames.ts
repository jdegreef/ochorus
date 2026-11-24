/**
 * The canon's short book names and abbreviations in each hub locale
 * (BIBLE_LOCALES): what the /bible hub's spines, chapter chips, passage box
 * and story links call a book ("Romans 8", «Romanos 8»).
 *
 * English is the sermon shelf's `CANON` (pythonbible's titles). Spanish is the
 * Spanish edition's own: each name is the one its chapters are titled with
 * (`library/data/owb/<CODE>/es/book.json`, "Génesis 1", "Cantares 1", "Salmo
 * 1"), so a link here reads exactly as the chapter it opens; the
 * abbreviations are the usual Spanish ones (Gn, Éx … Ap).
 */
import { CANON } from '$lib/sermonCanon';
import type { BibleLocale } from '$lib/bibleLocales';

type Canon = readonly (readonly [name: string, abbr: string])[];

const CANON_ES: Canon = [
	['Génesis', 'Gn'],
	['Éxodo', 'Éx'],
	['Levítico', 'Lv'],
	['Números', 'Nm'],
	['Deuteronomio', 'Dt'],
	['Josué', 'Jos'],
	['Jueces', 'Jue'],
	['Rut', 'Rt'],
	['1 Samuel', '1 S'],
	['2 Samuel', '2 S'],
	['1 Reyes', '1 R'],
	['2 Reyes', '2 R'],
	['1 Crónicas', '1 Cr'],
	['2 Crónicas', '2 Cr'],
	['Esdras', 'Esd'],
	['Nehemías', 'Neh'],
	['Ester', 'Est'],
	['Job', 'Job'],
	['Salmos', 'Sal'],
	['Proverbios', 'Pr'],
	['Eclesiastés', 'Ec'],
	['Cantares', 'Cnt'],
	['Isaías', 'Is'],
	['Jeremías', 'Jer'],
	['Lamentaciones', 'Lm'],
	['Ezequiel', 'Ez'],
	['Daniel', 'Dn'],
	['Oseas', 'Os'],
	['Joel', 'Jl'],
	['Amós', 'Am'],
	['Abdías', 'Abd'],
	['Jonás', 'Jon'],
	['Miqueas', 'Mi'],
	['Nahúm', 'Nah'],
	['Habacuc', 'Hab'],
	['Sofonías', 'Sof'],
	['Hageo', 'Hag'],
	['Zacarías', 'Zac'],
	['Malaquías', 'Mal'],
	['Mateo', 'Mt'],
	['Marcos', 'Mr'],
	['Lucas', 'Lc'],
	['Juan', 'Jn'],
	['Hechos', 'Hch'],
	['Romanos', 'Ro'],
	['1 Corintios', '1 Co'],
	['2 Corintios', '2 Co'],
	['Gálatas', 'Gá'],
	['Efesios', 'Ef'],
	['Filipenses', 'Flp'],
	['Colosenses', 'Col'],
	['1 Tesalonicenses', '1 Ts'],
	['2 Tesalonicenses', '2 Ts'],
	['1 Timoteo', '1 Ti'],
	['2 Timoteo', '2 Ti'],
	['Tito', 'Tit'],
	['Filemón', 'Flm'],
	['Hebreos', 'Heb'],
	['Santiago', 'Stg'],
	['1 Pedro', '1 P'],
	['2 Pedro', '2 P'],
	['1 Juan', '1 Jn'],
	['2 Juan', '2 Jn'],
	['3 Juan', '3 Jn'],
	['Judas', 'Jud'],
	['Apocalipsis', 'Ap']
];

/** Each hub locale's canon, 1 Genesis … 66 Revelation (index + 1). */
export const CANON_NAMES: Readonly<Record<BibleLocale, Canon>> = { en: CANON, es: CANON_ES };

/** What a single psalm is called ("Psalm 23", «Salmo 23»): the one book whose
 *  chapters are titled in the singular. */
export const PSALM: Readonly<Record<BibleLocale, string>> = { en: 'Psalm', es: 'Salmo' };

/** The canon in `locale`: a hub locale's own, else English (the pure helpers'
 *  callers outside the hub; a hub page only ever asks for its own). */
export const canonIn = (locale: string): Canon =>
	(CANON_NAMES as Record<string, Canon>)[locale] ?? CANON;

/** `PSALM` in `locale`, English outside the hub (as `canonIn`). */
export const psalmIn = (locale: string): string =>
	(PSALM as Record<string, string>)[locale] ?? PSALM.en;
