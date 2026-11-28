/**
 * "A question for the table": one question per Brave for God story, for a
 * parent to ask at dinner after reading it — shown under the chapter and on
 * the Tonight's story card. Keyed by book slug, then language, then the
 * question for each chapter in order (chapter 1 first). The stories are one
 * chapter each, and chapter order is the same in every language.
 *
 * DRAFTED 2026-11-28 for the founder to check, so English only for now: a
 * language with no list simply shows no question (no English fallback), and
 * the translations follow once the English is settled.
 */
export const TABLE_QUESTIONS: Record<string, Record<string, readonly string[]>> = {
	'brave-for-god': {
		en: [
			'Samuel gave his people God’s words in the language of home. Why do you think that mattered so much?',
			'Mary would rather be afraid and go than be safe and stay. What is something you are afraid to do that God might be asking of you?',
			'Hudson came close and became a friend instead of a stranger. Who could you come close to this week?',
			'George Müller asked no one but God. What could our family pray for, and then watch for God’s answer?',
			'People told Gladys she was not enough. When have you felt not enough, and what does her story say about that?',
			'Amy once wished for different eyes and an easier life. Is there something about you that you wish were different that God might use?'
		]
	},
	'brave-for-god-2': {
		en: [
			'William Carey said he could plod: keep going and not give up. What hard thing do you want to keep going at?',
			'David’s friends carried him more than a thousand miles because they loved him. How can we show love that costs us something?',
			'Festo chose love instead of hate, even for a cruel ruler. Is there someone you find hard to forgive?',
			'Ramabai spent all her learning on people nobody else would help. Who might nobody be helping near us?',
			'Corrie forgave a guard who had been cruel to her. Why do you think that was the hardest part of her story?',
			'Eric gave up his best race, and later his fame, to honour God. What would be hard for you to give up for God?'
		]
	},
	'brave-for-god-3': {
		en: [
			'Ann hid Adoniram’s Bible translation to keep it safe. Why is God’s Word worth so much care?',
			'Elisabeth went back to the Waorani with forgiveness, not revenge. What would going back in love look like after a quarrel?',
			'Sundar kept walking even when his feet were cut and bleeding. Why do you think he kept going?',
			'Lottie gave away nearly everything she had in the famine. What is one thing our family could give this week?',
			'Helen learned that God never wastes our suffering. Can you think of a hard time that God used for good?',
			'Simeon could not keep his joy to himself. Who told you about Jesus, and who could you tell?'
		]
	},
	'brave-for-god-4': {
		en: [
			'John kept digging while the islanders laughed. When is it hard to keep trusting God while others laugh?',
			'Mary saved for years and walked a very long way for a Bible of her own. How can we show we treasure the Bibles we have?',
			'George Liele was never famous, yet his work went on and on after him. Does God need us to be famous to use us?',
			'C.T. traded fame and a fortune for a hut in the forest. Why did that seem a good trade to him?',
			'Lilias gave up being famous to be faithful. What does being faithful look like for you at home or at school?',
			'Three knocks in one night changed Ida’s whole life. What might God want you to notice in the people around you?'
		]
	}
};

/** The question for one chapter in one language, or null where there is none. */
export function tableQuestion(book: string, order: number, language: string): string | null {
	return TABLE_QUESTIONS[book]?.[language]?.[order - 1] ?? null;
}
