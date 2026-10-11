/**
 * The footer's closing word: the Aaronic blessing (Numbers 6:24–26), in each
 * locale's own Bible — the same Bible `library/language_seed.py` names as that
 * language's authority, fetched verbatim from the Take Root API
 * (`/api/bible/<bible>/NUM/6/`). Scripture is never ours to write: this text
 * was generated from the API's JSON, not typed, and only two things were done
 * to it — the speech marks that open and close Moses' quotation in some
 * editions were trimmed (the blessing stands alone here), and the French
 * mirror's stray spaces around apostrophes ("qu’ il") were closed up.
 *
 * Kept as a build-time constant, not fetched: the reader is a prerendered
 * static site and the footer is on every page, so a runtime call would be one
 * more request per page for a text that never changes.
 *
 * A locale absent from the map (vi and ko — Take Root carries no Numbers for
 * either) shows no blessing at all. There is no English fallback: a Vietnamese
 * page closing on an English verse is the cross-language leak the library
 * refuses everywhere else. The licensed texts here (hi IRV, lg OLCB, am ULB)
 * are already credited by the footer's Bible-credit line, which renders on
 * exactly those locales (bibleCredit.ts).
 */
export type Benediction = {
	/** The Take Root translation code the lines were fetched from. */
	bible: string;
	/** "Numbers", as that Bible names the book (the verses are PASSAGE). */
	book: string;
	/** One line per verse, 24–26. */
	lines: readonly [string, string, string];
};

/** The chapter and verses — the same in every Bible here. */
export const PASSAGE = '6:24–26';

export const BENEDICTION: Readonly<Record<string, Benediction>> = {
	en: {
		bible: "kjv",
		book: "Numbers",
		lines: [
			"The Lord bless thee, and keep thee:",
			"The Lord make his face shine upon thee, and be gracious unto thee:",
			"The Lord lift up his countenance upon thee, and give thee peace."
		]
	},
	es: {
		bible: "rv1858",
		book: "Números",
		lines: [
			"Jehová te bendiga, y te guarde:",
			"Haga resplandecer Jehová su rostro sobre ti, y haya de ti misericordia:",
			"Jehová alce á ti su rostro, y ponga en ti paz."
		]
	},
	sw: {
		bible: "swhonen",
		book: "Hesabu",
		lines: [
			"Bwana akubariki na kukulinda;",
			"Bwana akuangazie nuru ya uso wake na kukufadhili;",
			"Bwana akugeuzie uso wake na kukupa amani."
		]
	},
	lg: {
		bible: "lug",
		book: "Okubala",
		lines: [
			"Mukama Katonda akuwe omukisa, akukuume;",
			"Mukama Katonda akwakize amaaso ge akukwatirwe ekisa;",
			"Mukama Katonda akwolekeze amaaso ge akuwe emirembe."
		]
	},
	pt: {
		bible: "porbrbsl",
		book: "Números",
		lines: [
			"O SENHOR te abençoe e te guarde.",
			"O SENHOR faça resplandecer o seu rosto sobre ti, e tenha misericórdia de ti.",
			"O SENHOR levante o seu rosto sobre ti, e te dê a paz."
		]
	},
	ar: {
		bible: "arb-vd",
		book: "اَلْعَدَد",
		lines: [
			"يُبَارِكُكَ ٱلرَّبُّ وَيَحْرُسُكَ.",
			"يُضِيءُ ٱلرَّبُّ بِوَجْهِهِ عَلَيْكَ وَيَرْحَمُكَ.",
			"يَرْفَعُ ٱلرَّبُّ وَجْهَهُ عَلَيْكَ وَيَمْنَحُكَ سَلَامًا."
		]
	},
	hi: {
		bible: "irvhin",
		book: "गिनती",
		lines: [
			"यहोवा तुझे आशीष दे और तेरी रक्षा करे:",
			"यहोवा तुझ पर अपने मुख का प्रकाश चमकाए, और तुझ पर अनुग्रह करे:",
			"यहोवा अपना मुख तेरी ओर करे, और तुझे शान्ति दे।"
		]
	},
	uk: {
		bible: "ukr-kul",
		book: "4 Мойсея",
		lines: [
			"Господь благослови тебе, і хорони тебе!",
			"Господь нехай сьвітить лицем своїм над тобою, та милує тебе!",
			"Нехай оберне Господь лице своє на тебе і дасть тобі впокій!"
		]
	},
	fr: {
		bible: "fralsg",
		book: "Nombres",
		lines: [
			"Que l’Éternel te bénisse, et qu’il te garde!",
			"Que l’Éternel fasse luire sa face sur toi, et qu’il t’accorde sa grâce!",
			"Que l’Éternel tourne sa face vers toi, et qu’il te donne la paix!"
		]
	},
	am: {
		bible: "am-ulb",
		book: "ዘኁልቁ",
		lines: [
			"ያህዌ ይባርችሁ ይጠብቃችሁ፡፡",
			"ያህዌ ብርሃኑን በእናንተ ላይ ያብራራ ፊቱን ይመልስላችሁ፣ ይራራላች፡፡",
			"ያህዌ በሞገስ ያጥግባችሁ፣ ሰላምንም ይስጣችሁ፡፡"
		]
	}
};
