import type { ForLocale } from './forLinks';

/**
 * The words the "Ochorus for …" template draws around each page's copy — its
 * section headings and their lines, the numbers strip, the invite kit — in
 * every language the pages are written in ($lib/forLinks `FOR_LOCALES`). Kept
 * with the copy rather than in the catalogues for the copy's own reason
 * ($lib/forPages): two languages, not every catalogue.
 */
export interface ForChrome {
	/** The group switcher's first chip and its label. */
	all: string;
	switcherLabel: string;
	/** The numbers strip's tile names. */
	counts: { books: string; sermons: string; plans: string; languages: string };
	plansHeading: string;
	plansBody: string;
	plansMore: string;
	seriesHeading: string;
	seriesBody: string;
	week: (n: number) => string;
	studyQuestions: (n: number) => string;
	shelvesHeading: string;
	levelsHeading: string;
	levelsBody: string;
	writersHeading: string;
	writersBody: string;
	writersMore: string;
	guidesHeading: string;
	guidesBody: string;
	offlineHeading: string;
	offlineSaveAll: string;
	/** "PDF of {title}", for a screen reader. */
	fileOf: string;
	languagesHeading: string;
	languagesBody: string;
	openLibrary: (language: string) => string;
	inviteHeading: string;
	inviteBody: string;
	inviteSubject: string;
	invite: { copy: string; copied: string; selected: string; announced: string; email: string };
	questions: string;
	contact: string;
	/** The /for/ index's lead, and its meta description from the groups' phrases. */
	indexLead: string;
	indexDescription: (phrases: string[]) => string;
	/** "61 books · 59 sermons": singular and plural of each count. */
	countWords: { book: [string, string]; sermon: [string, string]; plan: [string, string] };
}

/** "a, b and c" in the language's own "and". */
export const listOf = (xs: string[], and: string): string =>
	xs.length < 2 ? xs.join('') : `${xs.slice(0, -1).join(', ')} ${and} ${xs.at(-1)}`;

const NAMERS = new Map<ForLocale, Intl.DisplayNames>();

/** A language's name in the page's language (lower case in French, as French
 *  writes it mid-sentence). ICU calls Luganda "Ganda"; Ochorus uses the name
 *  its readers use. */
export function languageName(code: string, locale: ForLocale): string {
	if (code === 'lg') return locale === 'en' ? 'Luganda' : 'luganda';
	let namer = NAMERS.get(locale);
	if (!namer) NAMERS.set(locale, (namer = new Intl.DisplayNames([locale], { type: 'language' })));
	return namer.of(code) ?? code;
}

export const FOR_CHROME: Record<ForLocale, ForChrome> = {
	en: {
		all: 'All',
		switcherLabel: 'Who Ochorus is for',
		counts: { books: 'books', sermons: 'sermons', plans: 'reading plans', languages: 'languages' },
		plansHeading: 'Plans to read together',
		plansBody:
			'One short reading a day. Start on the same day and everyone reaches the same chapter together, each reader ticking off their own progress as they go.',
		plansMore: 'See every reading plan',
		seriesHeading: 'A sermon series for your group',
		seriesBody:
			'Read one sermon at home each week, then talk it through together. Every sermon here comes with study questions and their answers, at the foot of the sermon.',
		week: (n) => `Week ${n}`,
		studyQuestions: (n) => `${n} study ${n === 1 ? 'question' : 'questions'}`,
		shelvesHeading: 'Good places to start',
		levelsHeading: 'One story, three reading levels',
		levelsBody:
			'Many classics come as a children’s edition, a teens edition and the full text, so readers of every age can read the same book, and a child can grow into the original.',
		writersHeading: 'Meet the writers',
		writersBody: 'The lives behind the books: each one has a full biography, with the books and sermons they left.',
		writersMore: 'See every biography',
		guidesHeading: 'Printable leader’s guides',
		guidesBody:
			'A week-by-week guide to each of these books for children and teens: a summary for the leader, a memory verse, questions with their answers and an activity, one chapter a week. Print it, or lead from the screen.',
		offlineHeading: 'Take them offline',
		offlineSaveAll: 'Save all to this device',
		fileOf: 'of',
		languagesHeading: 'In the languages you serve',
		languagesBody:
			'Each language has its own library of full editions. Send someone straight to theirs, and the whole site reads in that language.',
		openLibrary: (language) => `Open the ${language} library`,
		inviteHeading: 'Pass it on',
		inviteBody: 'A message ready for a bulletin, a group chat or an email. Copy it as it is, or make it your own.',
		inviteSubject: 'Free Christian classics on Ochorus',
		invite: {
			copy: 'Copy the message',
			copied: 'Copied',
			selected: 'Selected: press Ctrl+C, or long-press and Copy.',
			announced: 'Message copied',
			email: 'Email'
		},
		questions: 'Questions',
		contact: 'Contact us',
		indexLead:
			'A free library of the great Christian classics, with no ads, no paywall and no account needed. Here is what it offers each of the people who use it: plans to read together, books to start with, printable guides and books to take offline.',
		indexDescription: (phrases) => `Free Christian classics for ${listOf(phrases, 'and')}.`,
		countWords: { book: ['book', 'books'], sermon: ['sermon', 'sermons'], plan: ['reading plan', 'reading plans'] }
	},
	fr: {
		all: 'Tous',
		switcherLabel: 'Pour qui est Ochorus',
		counts: { books: 'livres', sermons: 'sermons', plans: 'plans de lecture', languages: 'langues' },
		plansHeading: 'Des plans pour lire ensemble',
		plansBody:
			'Une courte lecture par jour. Commencez le même jour, et chacun arrive au même chapitre en même temps, en cochant sa propre progression au fil des jours.',
		plansMore: 'Voir tous les plans de lecture',
		seriesHeading: 'Une série de sermons pour votre groupe',
		seriesBody:
			'Lisez un sermon chez vous chaque semaine, puis parlez-en ensemble. Chaque sermon proposé ici est suivi de questions d’étude et de leurs réponses.',
		week: (n) => `Semaine ${n}`,
		studyQuestions: (n) => `${n} ${n === 1 ? 'question' : 'questions'} d’étude`,
		shelvesHeading: 'Par où commencer',
		levelsHeading: 'Une histoire, trois niveaux de lecture',
		levelsBody:
			'Certains classiques existent en édition pour enfants, en édition pour adolescents et en texte intégral : chacun lit le même livre à son âge, et l’enfant peut grandir jusqu’à l’original.',
		writersHeading: 'Rencontrez les auteurs',
		writersBody: 'Les vies derrière les livres : chacun a sa biographie complète, avec les livres et les sermons qu’il a laissés.',
		writersMore: 'Voir toutes les biographies',
		guidesHeading: 'Guides imprimables pour les responsables',
		guidesBody:
			'Un guide semaine après semaine pour chacun de ces livres pour enfants et adolescents : un résumé pour le responsable, un verset à mémoriser, des questions avec leurs réponses et une activité, un chapitre par semaine.',
		offlineHeading: 'À emporter hors ligne',
		offlineSaveAll: 'Tout enregistrer sur cet appareil',
		fileOf: 'de',
		languagesHeading: 'Dans les langues de ceux que vous servez',
		languagesBody:
			'Chaque langue a sa propre bibliothèque d’éditions complètes. Envoyez chacun directement vers la sienne : tout le site s’affiche alors dans cette langue.',
		openLibrary: (language) => `Ouvrir la bibliothèque en ${language}`,
		inviteHeading: 'Faites passer le mot',
		inviteBody:
			'Un message prêt pour un bulletin, une discussion de groupe ou un e-mail. Copiez-le tel quel, ou faites-le vôtre.',
		inviteSubject: 'Des classiques chrétiens gratuits sur Ochorus',
		invite: {
			copy: 'Copier le message',
			copied: 'Copié',
			selected: 'Sélectionné : appuyez sur Ctrl+C, ou faites un appui long puis Copier.',
			announced: 'Message copié',
			email: 'E-mail'
		},
		questions: 'Questions',
		contact: 'Nous contacter',
		indexLead:
			'Une bibliothèque gratuite des grands classiques chrétiens, sans publicité, sans abonnement et sans compte à créer. Voici ce qu’elle offre à chacun de ceux qui l’utilisent : des plans pour lire ensemble et des livres par où commencer.',
		indexDescription: (phrases) => `Des classiques chrétiens gratuits pour ${listOf(phrases, 'et')}.`,
		countWords: { book: ['livre', 'livres'], sermon: ['sermon', 'sermons'], plan: ['plan de lecture', 'plans de lecture'] }
	}
};
