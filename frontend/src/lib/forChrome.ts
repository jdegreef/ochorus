import type { ForLocale } from './forLinks';
import type { ForGoal } from './forPicker';
import type { ForSection } from './forSections';
import type { ReadingDays } from './planSchedule';

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
	/** The jump bar: its label, and each section's name on it. */
	jumpLabel: string;
	nav: Record<Exclude<ForSection, 'quote'>, string>;
	/** "Start a reading group", the plans section's tool ($lib/planTogether). */
	together: {
		heading: string;
		body: string;
		plan: string;
		start: string;
		days: string;
		dayLabels: Record<ReadingDays, string>;
		link: string;
		share: string;
		/** The message the link is shared with: the plan, and its first day. */
		message: (plan: string, date: string) => string;
		totalsAdd: string;
		totalsAdded: string;
		totalsSignIn: string;
		totalsFailed: string;
		totalsNote: (min: number) => string;
	};
	/** A link's QR code: show it, save it, and what it reads as. */
	qr: {
		show: string;
		hide: string;
		download: string;
		alt: (what: string) => string;
	};
	/** The printable bulletin insert: two to a page, to cut in half. */
	flyer: {
		print: string;
		eyebrow: string;
		/** "A short reading a day · from Monday 20 October · weekdays". */
		schedule: (date: string, days: string) => string;
		scan: string;
		free: string;
	};
	/** A sermon series on the group's calendar. */
	seriesCalendar: { first: string; add: string; note: string };
	/** The /for/ index's two questions. */
	picker: {
		heading: string;
		who: string;
		what: string;
		roles: Record<string, string>;
		goals: Record<ForGoal, string>;
		go: (phrase: string) => string;
	};
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
		countWords: { book: ['book', 'books'], sermon: ['sermon', 'sermons'], plan: ['reading plan', 'reading plans'] },
		jumpLabel: 'On this page',
		nav: {
			why: 'Why Ochorus',
			plans: 'Plans',
			series: 'Sermon series',
			ideas: 'Ideas',
			shelves: 'Books',
			levels: 'Reading levels',
			writers: 'Writers',
			guides: 'Leader’s guides',
			offline: 'Offline',
			languages: 'Languages',
			invite: 'Pass it on',
			questions: 'Questions'
		},
		together: {
			heading: 'Start a reading group',
			body: 'Choose a plan and the day you begin, then pass on the link. Everyone who opens it is on the same day of the plan. Nobody needs an account, and nothing about anyone is collected.',
			plan: 'Plan',
			start: 'Start on',
			days: 'Read on',
			dayLabels: {
				daily: 'Every day',
				weekdays: 'Weekdays',
				monsat: 'Monday to Saturday'
			},
			link: 'Your group’s link',
			share: 'Share the link',
			message: (plan, date) => `Let’s read ${plan} together, one short reading a day, starting ${date}. Open this link to join:`,
			totalsAdd: 'Also show how many have read',
			totalsAdded: 'The link now shows how many have read each day',
			totalsSignIn: 'Sign in to show how many have read',
			totalsFailed: 'That didn’t work. Please try again.',
			totalsNote: (min) =>
				`Numbers only, never names, and only for readers who choose to be counted. They show once ${min} have joined.`
		},
		qr: {
			show: 'QR code',
			hide: 'Hide QR code',
			download: 'Download QR code',
			alt: (what) => `QR code: ${what}`
		},
		flyer: {
			print: 'Print a bulletin insert',
			eyebrow: 'Read together',
			schedule: (date, days) => `One short reading a day · from ${date} · ${days.toLowerCase()}`,
			scan: 'Scan with your phone’s camera, or open',
			free: 'Free to read on any phone or computer. No ads, and no sign-up needed.'
		},
		seriesCalendar: {
			first: 'First meeting',
			add: 'Add to calendar',
			note: 'One event a week naming the sermon to read, with a reminder that morning. Send the file to your group so their calendars have it too.'
		},
		picker: {
			heading: 'Find what you need',
			who: 'Who are you reading with?',
			what: 'What would you like to do?',
			roles: {
				churches: 'My congregation',
				'small-groups': 'A small group or Bible study',
				youth: 'A youth group',
				missionaries: 'People I serve on the mission field',
				chaplains: 'Patients, inmates or service members',
				'bible-colleges': 'Bible college students',
				schools: 'A class at school',
				homeschool: 'My homeschool',
				parents: 'My children',
				pastors: 'The people I preach to',
				'new-believers': 'Someone new to the faith',
				'prison-ministry': 'People in prison',
				'prayer-groups': 'A prayer group',
				'womens-ministry': 'A women’s group',
				'mens-ministry': 'A men’s group',
				evangelism: 'People I’m reaching with the gospel',
				'african-churches': 'A church in Africa',
				campus: 'Students'
			},
			goals: {
				together: 'Read a plan together',
				series: 'Run a sermon series',
				young: 'Find books for each age',
				guides: 'Print a leader’s guide',
				offline: 'Read without the internet',
				languages: 'Read in other languages',
				books: 'Find books to start with'
			},
			go: (phrase) => `Go to Ochorus for ${phrase}`
		}
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
		countWords: { book: ['livre', 'livres'], sermon: ['sermon', 'sermons'], plan: ['plan de lecture', 'plans de lecture'] },
		jumpLabel: 'Sur cette page',
		nav: {
			why: 'Pourquoi Ochorus',
			plans: 'Plans',
			series: 'Série de sermons',
			ideas: 'Idées',
			shelves: 'Livres',
			levels: 'Niveaux de lecture',
			writers: 'Auteurs',
			guides: 'Guides',
			offline: 'Hors ligne',
			languages: 'Langues',
			invite: 'Faire passer le mot',
			questions: 'Questions'
		},
		together: {
			heading: 'Lancer un groupe de lecture',
			body: 'Choisissez un plan et le jour où vous commencez, puis transmettez le lien. Tous ceux qui l’ouvrent en sont au même jour du plan. Aucun compte n’est nécessaire, et rien n’est collecté sur personne.',
			plan: 'Plan',
			start: 'Commencer le',
			days: 'Lire',
			dayLabels: {
				daily: 'Tous les jours',
				weekdays: 'En semaine',
				monsat: 'Du lundi au samedi'
			},
			link: 'Le lien de votre groupe',
			share: 'Partager le lien',
			message: (plan, date) =>
				`Lisons ensemble ${plan}, une courte lecture par jour, à partir du ${date}. Ouvrez ce lien pour nous rejoindre :`,
			totalsAdd: 'Afficher aussi combien ont lu',
			totalsAdded: 'Le lien affiche maintenant combien ont lu chaque jour',
			totalsSignIn: 'Connectez-vous pour afficher combien ont lu',
			totalsFailed: 'Cela n’a pas fonctionné. Veuillez réessayer.',
			totalsNote: (min) =>
				`Des chiffres seulement, jamais de noms, et uniquement pour les lecteurs qui choisissent d’être comptés. Ils s’affichent dès que ${min} personnes ont rejoint le groupe.`
		},
		qr: {
			show: 'Code QR',
			hide: 'Masquer le code QR',
			download: 'Télécharger le code QR',
			alt: (what) => `Code QR : ${what}`
		},
		flyer: {
			print: 'Imprimer un encart pour le bulletin',
			eyebrow: 'Lisons ensemble',
			schedule: (date, days) => `Une courte lecture par jour · à partir du ${date} · ${days.toLowerCase()}`,
			scan: 'Scannez avec l’appareil photo de votre téléphone, ou ouvrez',
			free: 'Gratuit, sur tout téléphone ou ordinateur. Sans publicité et sans inscription.'
		},
		seriesCalendar: {
			first: 'Première rencontre',
			add: 'Ajouter au calendrier',
			note: 'Un événement par semaine avec le sermon à lire, et un rappel le matin même. Envoyez le fichier à votre groupe pour que chacun l’ait aussi dans son calendrier.'
		},
		picker: {
			heading: 'Trouvez ce qu’il vous faut',
			who: 'Avec qui lisez-vous ?',
			what: 'Que voulez-vous faire ?',
			roles: {
				churches: 'Mon Église',
				'small-groups': 'Un petit groupe ou une étude biblique',
				youth: 'Un groupe de jeunes',
				missionaries: 'Ceux que je sers en mission',
				chaplains: 'Des patients, des détenus ou des militaires',
				'bible-colleges': 'Des étudiants d’institut biblique',
				schools: 'Une classe',
				homeschool: 'L’école à la maison',
				parents: 'Mes enfants',
				pastors: 'Ceux à qui je prêche',
				'new-believers': 'Quelqu’un de nouveau dans la foi',
				'prison-ministry': 'Des personnes en prison',
				'prayer-groups': 'Un groupe de prière',
				'womens-ministry': 'Un groupe de femmes',
				'mens-ministry': 'Un groupe d’hommes',
				evangelism: 'Ceux à qui j’annonce l’Évangile',
				'african-churches': 'Une Église en Afrique',
				campus: 'Des étudiants'
			},
			goals: {
				together: 'Lire un plan ensemble',
				series: 'Suivre une série de sermons',
				young: 'Trouver des livres pour chaque âge',
				guides: 'Imprimer un guide',
				offline: 'Lire sans internet',
				languages: 'Lire dans d’autres langues',
				books: 'Trouver par où commencer'
			},
			go: (phrase) => `Aller à Ochorus pour ${phrase}`
		}
	}
};
