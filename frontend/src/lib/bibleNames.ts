/**
 * The canon's short book names and abbreviations in each hub locale
 * (BIBLE_LOCALES): what the /bible hub's spines, chapter chips, passage box
 * and story links call a book ("Romans 8", «Romanos 8»).
 *
 * English is the sermon shelf's `CANON` (pythonbible's titles). Spanish is the
 * Spanish edition's own: each name is the one its chapters are titled with
 * (`library/data/owb/<CODE>/es/book.json`, "Génesis 1", "Cantares 1", "Salmo
 * 1"), so a link here reads exactly as the chapter it opens; the
 * abbreviations are the usual Spanish ones (Gn, Éx … Ap). French and
 * Portuguese are their editions' own in the same way (books/<slug>.<lang>.json:
 * "Psaume 23", "Ésaïe 53", "Cântico dos Cânticos 1"), with the abbreviations
 * French Bibles use (Gn, Ex … Es, Hé … Ap) and Portuguese ones (Gn, Êx … Sl,
 * Jo … Ap). Swahili likewise ("Zaburi 23", "Wimbo Ulio Bora 1", "Yohana 3"),
 * with the abbreviations Swahili Bibles use (Mwa, Kut … Zab … Mt, Yn, Mdo …
 * Ufu). Its psalms are "Zaburi" in the singular and the plural alike.
 */
import { CANON } from '$lib/sermonCanon';
import { divisionOf } from '$lib/bible';
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

const CANON_FR: Canon = [
	['Genèse', 'Gn'],
	['Exode', 'Ex'],
	['Lévitique', 'Lv'],
	['Nombres', 'Nb'],
	['Deutéronome', 'Dt'],
	['Josué', 'Jos'],
	['Juges', 'Jg'],
	['Ruth', 'Rt'],
	['1 Samuel', '1 S'],
	['2 Samuel', '2 S'],
	['1 Rois', '1 R'],
	['2 Rois', '2 R'],
	['1 Chroniques', '1 Ch'],
	['2 Chroniques', '2 Ch'],
	['Esdras', 'Esd'],
	['Néhémie', 'Né'],
	['Esther', 'Est'],
	['Job', 'Jb'],
	['Psaumes', 'Ps'],
	['Proverbes', 'Pr'],
	['Ecclésiaste', 'Ec'],
	['Cantique des cantiques', 'Ct'],
	['Ésaïe', 'Es'],
	['Jérémie', 'Jr'],
	['Lamentations', 'Lm'],
	['Ézéchiel', 'Ez'],
	['Daniel', 'Dn'],
	['Osée', 'Os'],
	['Joël', 'Jl'],
	['Amos', 'Am'],
	['Abdias', 'Ab'],
	['Jonas', 'Jon'],
	['Michée', 'Mi'],
	['Nahoum', 'Na'],
	['Habacuc', 'Ha'],
	['Sophonie', 'So'],
	['Aggée', 'Ag'],
	['Zacharie', 'Za'],
	['Malachie', 'Ml'],
	['Matthieu', 'Mt'],
	['Marc', 'Mc'],
	['Luc', 'Lc'],
	['Jean', 'Jn'],
	['Actes', 'Ac'],
	['Romains', 'Rm'],
	['1 Corinthiens', '1 Co'],
	['2 Corinthiens', '2 Co'],
	['Galates', 'Ga'],
	['Éphésiens', 'Ep'],
	['Philippiens', 'Ph'],
	['Colossiens', 'Col'],
	['1 Thessaloniciens', '1 Th'],
	['2 Thessaloniciens', '2 Th'],
	['1 Timothée', '1 Tm'],
	['2 Timothée', '2 Tm'],
	['Tite', 'Tt'],
	['Philémon', 'Phm'],
	['Hébreux', 'Hé'],
	['Jacques', 'Jc'],
	['1 Pierre', '1 P'],
	['2 Pierre', '2 P'],
	['1 Jean', '1 Jn'],
	['2 Jean', '2 Jn'],
	['3 Jean', '3 Jn'],
	['Jude', 'Jd'],
	['Apocalypse', 'Ap']
];

const CANON_PT: Canon = [
	['Gênesis', 'Gn'],
	['Êxodo', 'Êx'],
	['Levítico', 'Lv'],
	['Números', 'Nm'],
	['Deuteronômio', 'Dt'],
	['Josué', 'Js'],
	['Juízes', 'Jz'],
	['Rute', 'Rt'],
	['1 Samuel', '1 Sm'],
	['2 Samuel', '2 Sm'],
	['1 Reis', '1 Rs'],
	['2 Reis', '2 Rs'],
	['1 Crônicas', '1 Cr'],
	['2 Crônicas', '2 Cr'],
	['Esdras', 'Ed'],
	['Neemias', 'Ne'],
	['Ester', 'Et'],
	['Jó', 'Jó'],
	['Salmos', 'Sl'],
	['Provérbios', 'Pv'],
	['Eclesiastes', 'Ec'],
	['Cântico dos Cânticos', 'Ct'],
	['Isaías', 'Is'],
	['Jeremias', 'Jr'],
	['Lamentações', 'Lm'],
	['Ezequiel', 'Ez'],
	['Daniel', 'Dn'],
	['Oseias', 'Os'],
	['Joel', 'Jl'],
	['Amós', 'Am'],
	['Obadias', 'Ob'],
	['Jonas', 'Jn'],
	['Miqueias', 'Mq'],
	['Naum', 'Na'],
	['Habacuque', 'Hc'],
	['Sofonias', 'Sf'],
	['Ageu', 'Ag'],
	['Zacarias', 'Zc'],
	['Malaquias', 'Ml'],
	['Mateus', 'Mt'],
	['Marcos', 'Mc'],
	['Lucas', 'Lc'],
	['João', 'Jo'],
	['Atos', 'At'],
	['Romanos', 'Rm'],
	['1 Coríntios', '1 Co'],
	['2 Coríntios', '2 Co'],
	['Gálatas', 'Gl'],
	['Efésios', 'Ef'],
	['Filipenses', 'Fp'],
	['Colossenses', 'Cl'],
	['1 Tessalonicenses', '1 Ts'],
	['2 Tessalonicenses', '2 Ts'],
	['1 Timóteo', '1 Tm'],
	['2 Timóteo', '2 Tm'],
	['Tito', 'Tt'],
	['Filemom', 'Fm'],
	['Hebreus', 'Hb'],
	['Tiago', 'Tg'],
	['1 Pedro', '1 Pe'],
	['2 Pedro', '2 Pe'],
	['1 João', '1 Jo'],
	['2 João', '2 Jo'],
	['3 João', '3 Jo'],
	['Judas', 'Jd'],
	['Apocalipse', 'Ap']
];

const CANON_SW: Canon = [
	['Mwanzo', 'Mwa'],
	['Kutoka', 'Kut'],
	['Mambo ya Walawi', 'Law'],
	['Hesabu', 'Hes'],
	['Kumbukumbu la Torati', 'Kum'],
	['Yoshua', 'Yos'],
	['Waamuzi', 'Amu'],
	['Ruthu', 'Rut'],
	['1 Samweli', '1 Sam'],
	['2 Samweli', '2 Sam'],
	['1 Wafalme', '1 Fal'],
	['2 Wafalme', '2 Fal'],
	['1 Mambo ya Nyakati', '1 Nya'],
	['2 Mambo ya Nyakati', '2 Nya'],
	['Ezra', 'Ezr'],
	['Nehemia', 'Neh'],
	['Esta', 'Est'],
	['Ayubu', 'Ayu'],
	['Zaburi', 'Zab'],
	['Mithali', 'Mit'],
	['Mhubiri', 'Mhu'],
	['Wimbo Ulio Bora', 'Wim'],
	['Isaya', 'Isa'],
	['Yeremia', 'Yer'],
	['Maombolezo', 'Omb'],
	['Ezekieli', 'Eze'],
	['Danieli', 'Dan'],
	['Hosea', 'Hos'],
	['Yoeli', 'Yoe'],
	['Amosi', 'Amo'],
	['Obadia', 'Oba'],
	['Yona', 'Yon'],
	['Mika', 'Mik'],
	['Nahumu', 'Nah'],
	['Habakuki', 'Hab'],
	['Sefania', 'Sef'],
	['Hagai', 'Hag'],
	['Zekaria', 'Zek'],
	['Malaki', 'Mal'],
	['Mathayo', 'Mt'],
	['Marko', 'Mk'],
	['Luka', 'Lk'],
	['Yohana', 'Yn'],
	['Matendo', 'Mdo'],
	['Warumi', 'Rum'],
	['1 Wakorintho', '1 Kor'],
	['2 Wakorintho', '2 Kor'],
	['Wagalatia', 'Gal'],
	['Waefeso', 'Efe'],
	['Wafilipi', 'Flp'],
	['Wakolosai', 'Kol'],
	['1 Wathesalonike', '1 The'],
	['2 Wathesalonike', '2 The'],
	['1 Timotheo', '1 Tim'],
	['2 Timotheo', '2 Tim'],
	['Tito', 'Tit'],
	['Filemoni', 'Flm'],
	['Waebrania', 'Ebr'],
	['Yakobo', 'Yak'],
	['1 Petro', '1 Pet'],
	['2 Petro', '2 Pet'],
	['1 Yohana', '1 Yn'],
	['2 Yohana', '2 Yn'],
	['3 Yohana', '3 Yn'],
	['Yuda', 'Yud'],
	['Ufunuo', 'Ufu']
];

/** Each hub locale's canon, 1 Genesis … 66 Revelation (index + 1). */
export const CANON_NAMES: Readonly<Record<BibleLocale, Canon>> = {
	en: CANON,
	es: CANON_ES,
	fr: CANON_FR,
	pt: CANON_PT,
	sw: CANON_SW
};

/** What a single psalm is called ("Psalm 23", «Salmo 23»): the one book whose
 *  chapters are titled in the singular. */
export const PSALM: Readonly<Record<BibleLocale, string>> = {
	en: 'Psalm',
	es: 'Salmo',
	fr: 'Psaume',
	pt: 'Salmo',
	sw: 'Zaburi'
};

/** The canon in `locale`: a hub locale's own, else English (the pure helpers'
 *  callers outside the hub; a hub page only ever asks for its own). */
export const canonIn = (locale: string): Canon =>
	(CANON_NAMES as Record<string, Canon>)[locale] ?? CANON;

/** `PSALM` in `locale`, English outside the hub (as `canonIn`). */
export const psalmIn = (locale: string): string =>
	(PSALM as Record<string, string>)[locale] ?? PSALM.en;

/** The Psalms' place in the canon. */
const PSALMS = 19;

/**
 * How a Bible chapter is named in `lang` ("Romans 8", «Romanos 8»), or null off
 * the canon. Psalms is the one book whose chapters are titled in the singular
 * ("Psalm 23", «Salmo 23», as `build_owb_book` titles them).
 */
export function chapterLabel(position: number | null | undefined, n: number, lang: string): string | null {
	const name = position === PSALMS ? psalmIn(lang) : canonName(position, lang);
	return name ? `${name} ${n}` : null;
}

/** The canon's short name for a position (1 Genesis … 66 Revelation) in
 *  `lang`, or null off the canon. */
export const canonName = (position: number | null | undefined, lang: string): string | null =>
	divisionOf(position) ? canonIn(lang)[position! - 1][0] : null;
