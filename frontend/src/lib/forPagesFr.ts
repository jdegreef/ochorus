import type { ForPage, ForShelfSpec } from './forPages';
import { LIVE_LOCALES } from './live-locales.generated';

/**
 * The French "Ochorus pour …" pages: one per English page in `FOR_PAGES`, same
 * slugs, same order, same shape. They are written for the French library as it
 * is, not translated word for word — French holds fewer books and sermons, no
 * quotation pages, no printable guides and no downloads, so every shelf, plan,
 * writer and sermon series here is drawn from what French readers can open,
 * and no claim leans on what only the English library has.
 *
 * Imports only types from './forPages' (it imports this module's values).
 * Keep every claim true of the live French site. Nothing here mentions how a
 * translation was made — review state is admin-only (root CLAUDE.md).
 */

/** The live languages besides French and English, by their French names.
 *  ICU calls Luganda "ganda"; Ochorus uses the name its readers use. */
const enFrancais = new Intl.DisplayNames(['fr'], { type: 'language' });
const frenchName = (code: string) => (code === 'lg' ? 'luganda' : (enFrancais.of(code) ?? code));
const OTHER_LANGUAGES = (LIVE_LOCALES as readonly string[]).filter((l) => l !== 'fr' && l !== 'en').map(frenchName);
/** "a, b et c". */
const et = (xs: string[]) => (xs.length < 2 ? xs.join('') : `${xs.slice(0, -1).join(', ')} et ${xs.at(-1)}`);
/** "en français comme en anglais, et aussi en espagnol, en swahili et en portugais". */
const IN_LANGUAGES = `en français comme en anglais${
	OTHER_LANGUAGES.length ? `, et aussi ${et(OTHER_LANGUAGES.map((n) => `en ${n}`))}` : ''
}`;

const FREE_ANSWER =
	'Oui. Chaque livre et chaque sermon d’Ochorus se lit gratuitement, sans abonnement, sans paiement et sans publicité. Les classiques eux-mêmes appartiennent au domaine public, et Ochorus est un ministère, pas une entreprise.';

const ACCOUNT_ANSWER =
	'Non. Tout le monde peut lire sans s’inscrire. Un compte gratuit reste possible : il garde la progression, les notes et les livres enregistrés d’un lecteur à jour sur tous ses appareils.';

/** A sermon series two pages share, so a replaced pick changes both. */
const PRAYER_SPIRIT_SERIES: ForShelfSpec = {
	title: 'Six semaines sur la prière et l’Esprit',
	note: 'Spurgeon, Finney, Simpson et Catherine Booth sur la prière et la vie dans l’Esprit : un sermon par semaine, lu chez soi et discuté ensemble.',
	picks: [
		'the-golden-key-of-prayer',
		'order-and-argument-in-prayer',
		'prevailing-prayer',
		'the-ravens-cry',
		'filled-with-the-spirit',
		'the-holy-ghost',
		'god-glorified-in-mans-dependence',
		'walking-with-god'
	]
};

const CHRIST_GRACE_SERIES: ForShelfSpec = {
	title: 'Six semaines sur Christ et sa grâce',
	note: 'Le cœur de l’Évangile, de Luther à Moody : qui est Christ, et ce que fait sa grâce.',
	picks: [
		'the-appearing-of-the-grace-of-god',
		'behold-the-lamb-of-god',
		'the-dying-thief',
		'christ-the-believers-wisdom',
		'the-excellency-of-christ',
		'the-resurrection-of-jesus',
		'every-mans-need-of-a-refuge',
		'rest'
	]
};

export const FOR_PAGES_FR: ForPage[] = [
	{
		slug: 'churches',
		title: 'Une bibliothèque chrétienne gratuite pour toute votre Église',
		lead: 'Ochorus met les grands classiques de la foi dans la poche de chaque membre : Murray, Spurgeon, Bunyan, Augustin, Moody et bien d’autres, en livres et en sermons, gratuits sur n’importe quel téléphone ou ordinateur. Sans abonnement, sans licence, sans budget.',
		seoTitle: 'Livres chrétiens gratuits pour les Églises',
		seoDescription:
			'Classiques chrétiens, sermons et plans de lecture pour toute votre Église, gratuits sur téléphone ou ordinateur. Sans abonnement et sans inscription.',
		primary: { href: '#plans', label: 'Choisir un plan à lire ensemble' },
		secondary: { href: '/books', label: 'Explorer la bibliothèque' },
		pointsHeading: 'Pourquoi les Églises utilisent Ochorus',
		points: [
			{
				icon: 'book',
				title: 'Gratuit pour chaque membre',
				body: 'Chaque livre et chaque sermon se lit gratuitement, et personne n’a besoin de compte. Partagez un seul lien depuis la chaire ou dans la lettre d’information de l’Église : chacun peut commencer à lire le jour même.',
				link: { href: '/books', label: 'Parcourir les livres' }
			},
			{
				icon: 'calendar',
				title: 'Lire ensemble, un chapitre par jour',
				body: 'Les plans de lecture font parcourir un livre à toute une assemblée, une courte lecture par jour. Ils conviennent à une série de prédications, au Carême, à une saison de prière ou à un parcours pour nouveaux croyants.',
				link: { href: '/plans', label: 'Voir les plans de lecture' }
			},
			{
				icon: 'mic',
				title: 'Les sermons des grands prédicateurs',
				body: 'Des sermons de Spurgeon, Moody, Wesley, Whitefield, Edwards et d’autres, souvent accompagnés de questions d’étude. Une aide pour préparer une prédication, et assez courts pour une semaine d’étude.',
				link: { href: '/sermons', label: 'Lire les sermons' }
			},
			{
				icon: 'globe',
				title: 'Dans les langues de votre assemblée',
				body: `Les livres paraissent en éditions complètes ${IN_LANGUAGES}. D’autres langues suivront, pour que chacun puisse lire dans sa propre langue.`
			}
		],
		ideasHeading: 'Des idées pour votre Église',
		ideas: [
			{
				title: 'Un plan de lecture pour toute l’Église',
				body: 'Choisissez un plan, annoncez-le le dimanche, et lisez le même chapitre ensemble toute la semaine. Les petits groupes reprennent la conversation en milieu de semaine.'
			},
			{
				title: 'Un livre pour vos petits groupes',
				body: 'Choisissez un classique pour le trimestre. Il ne coûte rien : personne n’est laissé de côté faute d’exemplaire.'
			},
			{
				title: 'Aider les nouveaux croyants à grandir',
				body: 'Commencez avec des livres clairs et chaleureux comme Le chemin vers Dieu de Moody et Tout par grâce de Spurgeon, puis un court plan de lecture.'
			},
			{
				title: 'Les enfants et les jeunes aussi',
				body: 'Des éditions pour jeunes lecteurs racontent les grands classiques aux enfants et aux adolescents : l’école du dimanche et le groupe de jeunes lisent les mêmes histoires, chacun à son niveau.'
			}
		],
		shelves: [
			{
				title: 'Pour toute l’assemblée',
				note: 'Des classiques qui nourrissent les Églises depuis des générations.',
				picks: [
					'school-of-prayer',
					'the-way-to-god',
					'all-of-grace',
					'pilgrims-progress',
					'absolute-surrender',
					'the-imitation-of-christ',
					'power-through-prayer'
				]
			},
			{
				title: 'Pour les pasteurs et les responsables',
				note: 'Pour le bureau : le soin des âmes, la prédication et la prière du serviteur.',
				picks: [
					'the-reformed-pastor',
					'men-who-tended-the-flock-2',
					'how-to-bring-men-to-christ',
					'key-teachings-of-richard-baxter',
					'men-of-prayer-2',
					'rise-up-men-of-god-2',
					'the-fundamental-doctrines-of-the-christian-faith'
				]
			},
			{
				title: 'Pour l’école du dimanche et les jeunes',
				note: 'Les mêmes classiques, racontés aux enfants et aux adolescents.',
				picks: [
					'pilgrims-progress-children',
					'brave-for-god',
					'the-life-of-trust-children',
					'all-of-grace-teens',
					'rooted-1',
					'brave-for-god-2',
					'pilgrims-progress-teens'
				]
			}
		],
		plans: [
			'school-of-prayer-31-days',
			'deeper-life-in-christ',
			'humility-12-days',
			'praying-men',
			'power-from-on-high'
		],
		authors: [
			'charles-h-spurgeon',
			'dwight-l-moody',
			'andrew-murray',
			'richard-baxter',
			'john-wesley',
			'george-whitefield',
			'e-m-bounds'
		],
		series: [PRAYER_SPIRIT_SERIES],
		invite: {
			text: 'Notre Église lit ensemble les grands classiques chrétiens sur Ochorus : livres, sermons et plans de lecture gratuits sur téléphone, sans publicité ni inscription.',
			href: '/plans'
		},
		questions: [
			{ q: 'Ochorus est-il vraiment gratuit ?', a: FREE_ANSWER },
			{ q: 'Nos membres doivent-ils créer un compte ?', a: ACCOUNT_ANSWER },
			{
				q: 'Quels auteurs trouve-t-on dans la bibliothèque ?',
				a: 'La bibliothèque traverse l’histoire de l’Église : des Pères comme Clément de Rome, Ignace d’Antioche, Athanase et saint Augustin, des puritains comme Owen, Baxter et Sibbes, les prédicateurs des réveils, des missionnaires comme Hudson Taylor et Amy Carmichael, et des voix du réveil d’Afrique de l’Est.'
			},
			{
				q: 'Tous les livres existent-ils en français ?',
				a: 'Pas encore. La bibliothèque française grandit au fil des mois ; chaque livre publié en français est une édition complète, et certains ouvrages n’existent pour l’instant qu’en anglais.'
			},
			{
				q: 'Comment notre Église peut-elle soutenir l’œuvre ?',
				a: 'En plus de la bibliothèque gratuite, Ochorus imprime des livres et les offre lors de conférences pastorales, dans des Églises, des écoles et des prisons d’Afrique de l’Est. Si votre Église souhaite y prendre part, écrivez-nous.'
			}
		],
		closeHeading: 'Offrez les classiques à votre assemblée',
		closeBody:
			'Commencez par un plan de lecture que chacun peut suivre, ou parcourez la bibliothèque et choisissez un livre à lire ensemble.'
	},
	{
		slug: 'small-groups',
		title: 'Des livres gratuits pour votre petit groupe ou votre étude biblique',
		lead: 'Choisissez un classique pour le trimestre : chacun dans le groupe peut le lire gratuitement sur son propre téléphone. La prière, la sainteté, la grâce et la vie de foi, avec Murray, Bounds, Hannah Whitall Smith, Moody et bien d’autres.',
		seoTitle: 'Livres gratuits pour petits groupes et études bibliques',
		seoDescription:
			'Classiques chrétiens, sermons et plans de lecture gratuits pour petits groupes et études bibliques. Chacun lit le même livre sur son téléphone, sans compte.',
		primary: { href: '#plans', label: 'Choisir un plan pour le groupe' },
		secondary: { href: '#series', label: 'Sermons avec questions d’étude' },
		pointsHeading: 'Pourquoi les petits groupes utilisent Ochorus',
		points: [
			{
				icon: 'users',
				title: 'Le livre pour tout le monde',
				body: 'Chaque livre est gratuit : personne n’est laissé de côté pour le prix d’un exemplaire. Envoyez un lien au groupe, et chacun peut commencer à lire le soir même.',
				link: { href: '/books', label: 'Parcourir les livres' }
			},
			{
				icon: 'calendar',
				title: 'Un rythme que tout le groupe peut tenir',
				body: 'Les plans de lecture proposent une courte lecture par jour : le groupe arrive à la rencontre en ayant lu les mêmes chapitres.',
				link: { href: '/plans', label: 'Voir les plans de lecture' }
			},
			{
				icon: 'mic',
				title: 'Des sermons pour une soirée',
				body: 'Un sermon de Spurgeon, Moody ou Wesley se lit dans la semaine et se discute en une heure, et beaucoup sont accompagnés de questions d’étude.',
				link: { href: '/sermons', label: 'Lire les sermons' }
			},
			{
				icon: 'tag',
				title: 'Trouver un livre par thème',
				body: 'Les thèmes rassemblent livres et sermons sur la prière, la souffrance, la sainteté, le Saint-Esprit et bien d’autres sujets : choisissez une étude qui rejoint le groupe là où il en est.',
				link: { href: '/topics', label: 'Parcourir les thèmes' }
			}
		],
		ideasHeading: 'Des idées pour votre groupe',
		ideas: [
			{
				title: 'Un livre par trimestre',
				body: 'Choisissez un classique, lisez un ou deux chapitres par semaine, et consacrez la rencontre à ce qui a touché chacun.'
			},
			{
				title: 'Un sermon par semaine',
				body: 'Lisez un sermon avant de vous retrouver, et laissez ses questions d’étude ouvrir la conversation.'
			},
			{
				title: 'Lire ensemble avec un plan',
				body: 'Commencez un plan de lecture le même jour, et reprenez ensemble les lectures de la semaine quand vous vous retrouvez.'
			},
			{
				title: 'Rencontrer les auteurs',
				body: 'Beaucoup d’auteurs ont une biographie complète : le groupe peut découvrir l’histoire qui se cache derrière un livre avant de le lire.'
			}
		],
		shelves: [
			{
				title: 'Des livres courts pour un trimestre',
				note: 'Un ou deux chapitres par semaine, et chaque fois une bonne conversation.',
				picks: [
					'humility-2',
					'absolute-surrender',
					'the-christians-secret-of-a-happy-life-4',
					'true-vine',
					'the-god-of-all-comfort',
					'waiting-on-god',
					'holy-in-christ',
					'jesus-himself-2'
				]
			},
			{
				title: 'Pour un groupe qui veut prier',
				note: 'Lire ensemble sur la prière, puis prier.',
				picks: [
					'school-of-prayer',
					'power-through-prayer',
					'prevailing-prayer',
					'lord-teach-us-to-pray-2',
					'ministry-of-intercession',
					'spurgeon-on-prayer',
					'the-inner-chamber',
					'necessity-of-prayer'
				]
			},
			{
				title: 'Des vies à lire ensemble',
				note: 'Des histoires vraies qui donnent au groupe matière à parler.',
				picks: [
					'men-who-moved-heaven',
					'women-who-moved-heaven-2',
					'watchman-nee-a-life',
					'men-and-women-who-gave-everything-2',
					'tukutendereza',
					'things-as-they-are',
					'a-brand-plucked-from-the-fire'
				]
			}
		],
		plans: [
			'praying-men',
			'the-puritan-heart',
			'deeper-life-in-christ',
			'the-inner-chamber-month',
			'humility-12-days'
		],
		authors: [
			'andrew-murray',
			'e-m-bounds',
			'hannah-whitall-smith',
			'dwight-l-moody',
			'george-muller',
			'john-wesley',
			'a-w-tozer'
		],
		series: [PRAYER_SPIRIT_SERIES, CHRIST_GRACE_SERIES],
		invite: {
			text: 'Le prochain livre de notre groupe est gratuit sur Ochorus. Lisez-le sur votre téléphone, sans inscription, et nous en parlerons à la rencontre.',
			href: '/books'
		},
		questions: [
			{ q: 'Ochorus est-il vraiment gratuit ?', a: FREE_ANSWER },
			{ q: 'Chacun dans le groupe doit-il avoir un compte ?', a: ACCOUNT_ANSWER },
			{
				q: 'Y a-t-il des questions pour la discussion ?',
				a: 'Beaucoup de sermons sont accompagnés de questions d’étude et de leurs réponses, tirées du sermon lui-même. Pour les livres, un plan de lecture donne au groupe un rythme commun, et les chapitres sont assez courts pour en parler ensemble.'
			},
			{
				q: 'Peut-on lire sans téléphone ?',
				a: 'Oui. Ochorus fonctionne aussi sur n’importe quel ordinateur ou tablette.'
			}
		],
		closeHeading: 'Choisissez le prochain livre de votre groupe',
		closeBody: 'Commencez par un plan de lecture, ou parcourez la bibliothèque et choisissez un classique à lire ensemble.'
	},
	{
		slug: 'youth',
		title: 'Des livres gratuits que vos adolescents liront vraiment',
		lead: 'Les grands classiques racontés pour les adolescents, des histoires vraies de foi et de courage, et des méditations de trente jours écrites pour les jeunes. Gratuits sur leur propre téléphone, sans publicité et sans compte.',
		seoTitle: 'Livres chrétiens gratuits pour la pastorale des jeunes',
		seoDescription:
			'Livres chrétiens gratuits pour les groupes de jeunes : classiques racontés pour ados, histoires vraies et méditations de trente jours. Sans pub ni compte.',
		primary: { href: '/teens', label: 'Livres pour adolescents' },
		secondary: { href: '#plans', label: 'Des plans pour votre groupe' },
		pointsHeading: 'Pourquoi les responsables de jeunes utilisent Ochorus',
		points: [
			{
				icon: 'layers',
				title: 'Des classiques dans leurs mots',
				body: 'Le Voyage du pèlerin, Tout par grâce, Une vie de confiance et d’autres, racontés pour les adolescents sans rien perdre de ce qu’ils disent. Chacun renvoie au texte intégral pour aller plus loin.',
				link: { href: '/teens', label: 'Voir les éditions pour ados' }
			},
			{
				icon: 'heart',
				title: 'Des histoires vraies qui marquent',
				body: 'Hudson Taylor, George Müller, Amanda Smith et d’autres, racontés pour les adolescents : des hommes et des femmes qui ont fait confiance à Dieu quand cela leur coûtait.',
				link: { href: '/teens', label: 'Les rencontrer' }
			},
			{
				icon: 'calendar',
				title: 'Trente jours avec Dieu',
				body: 'Des méditations comme Enracinés et Filles du Roi donnent quelques minutes par jour pendant un mois, et les plans de lecture gardent tout un groupe sur la même page.',
				link: { href: '/plans', label: 'Voir les plans de lecture' }
			},
			{
				icon: 'headphones',
				title: 'Sur leur téléphone, prêts à écouter',
				body: 'Tout fonctionne sur téléphone sans inscription, et chaque chapitre peut être lu à voix haute avec Écouter : pour le bus, la marche ou le retour de camp.'
			}
		],
		ideasHeading: 'Des idées pour votre groupe de jeunes',
		ideas: [
			{
				title: 'Un défi de trente jours',
				body: 'Après une retraite ou un camp, lancez le groupe dans la même méditation, et faites le point chaque semaine.'
			},
			{
				title: 'Un livre pour le trimestre',
				body: 'Lisez ensemble une édition pour ados, un ou deux chapitres par semaine, et consacrez la rencontre aux questions qu’elle soulève.'
			},
			{
				title: 'Une soirée héros',
				body: 'Racontez chaque semaine une histoire vraie de foi, puis invitez le groupe à lire la suite à la maison.'
			},
			{
				title: 'De quoi accompagner un nouveau croyant',
				body: 'Envoyez à un jeune qui vient de croire le lien vers Tout par grâce pour ados et un court plan de lecture.'
			}
		],
		shelves: [
			{
				title: 'Les classiques racontés pour les adolescents',
				note: 'Les grands livres dans des mots d’ados, chacun relié au texte intégral.',
				picks: [
					'pilgrims-progress-teens',
					'all-of-grace-teens',
					'the-life-of-trust-teens',
					'a-retrospect-teens',
					'talks-to-the-farmer-teens',
					'amanda-smith-autobiography-teens',
					'around-the-wicket-gate'
				]
			},
			{
				title: 'Des histoires vraies',
				note: 'Des vies données à Dieu, pour les plus grands.',
				picks: [
					'watchman-nee-a-life',
					'men-and-women-who-gave-everything-2',
					'women-who-moved-heaven-2',
					'men-who-moved-heaven',
					'a-brand-plucked-from-the-fire',
					'tukutendereza',
					'life-experience-gospel-labours'
				]
			},
			{
				title: 'Quelques minutes avec Dieu chaque jour',
				note: 'Des méditations courtes, à lire seul sur son téléphone.',
				picks: [
					'rooted-1',
					'daughters-of-the-king-2',
					'growing-in-wisdom',
					'rooted-2',
					'rooted-3',
					'rooted-4',
					'cheque-book'
				]
			}
		],
		plans: [
			'first-steps-for-teens',
			'rooted-three-months-books-1-3',
			'growing-in-wisdom-18-days',
			'humility-12-days'
		],
		authors: [
			'corrie-ten-boom',
			'elisabeth-elliot',
			'watchman-nee',
			'amy-carmichael',
			'c-t-studd',
			'hudson-taylor',
			'david-livingstone'
		],
		invite: {
			text: 'Des livres chrétiens gratuits pour les ados sur Ochorus : histoires vraies, classiques racontés pour eux et méditations de trente jours. Sans pub ni inscription.',
			href: '/teens'
		},
		questions: [
			{ q: 'Ochorus est-il vraiment gratuit ?', a: FREE_ANSWER },
			{
				q: 'Les adolescents doivent-ils s’inscrire ?',
				a: 'Non. Tout le monde peut lire sans compte. Un compte gratuit reste possible : il garde la progression, les notes et les livres enregistrés à jour sur tous les appareils.'
			},
			{
				q: 'Pour quel âge sont les livres pour ados ?',
				a: 'Les éditions pour ados sont écrites pour les grands enfants et les adolescents. Pour les plus jeunes, les livres pour jeunes lecteurs racontent les mêmes classiques plus simplement.'
			},
			{
				q: 'Peut-on y envoyer des adolescents sans crainte ?',
				a: 'Ochorus n’a ni publicité ni rien à acheter. C’est une bibliothèque de livres chrétiens, et rien d’autre ne vient leur disputer leur attention.'
			}
		],
		closeHeading: 'Donnez à votre groupe quelque chose de bon à lire',
		closeBody: 'Commencez par les livres pour adolescents, ou choisissez un plan de lecture à suivre ensemble.'
	},
	{
		slug: 'missionaries',
		title: 'Des classiques chrétiens à partager, gratuits, dans les langues que vous servez',
		lead: 'Une bibliothèque gratuite que vous pouvez offrir à n’importe qui avec un simple lien : rien à payer, aucune inscription. Les grands classiques, des sermons et des vies de missionnaires, avec des éditions complètes en plusieurs langues.',
		seoTitle: 'Livres chrétiens gratuits pour les missionnaires',
		seoDescription:
			'Classiques chrétiens, sermons et vies de missionnaires à partager avec ceux que vous servez, en éditions complètes dans plusieurs langues. Gratuit, sans compte.',
		primary: { href: '#languages', label: 'Voir ce que chaque langue propose' },
		secondary: { href: '/biographies', label: 'Vies de missionnaires' },
		pointsHeading: 'Pourquoi les missionnaires utilisent Ochorus',
		points: [
			{
				icon: 'share',
				title: 'Gratuit, à partager avec tous',
				body: 'Chaque livre et chaque sermon est gratuit, sans compte : on peut envoyer un lien à un nouveau croyant, qui commence à lire aussitôt.',
				link: { href: '/books', label: 'Parcourir les livres' }
			},
			{
				icon: 'globe',
				title: 'Des éditions complètes en plusieurs langues',
				body: `Les livres paraissent en éditions complètes ${IN_LANGUAGES}. D’autres langues suivront, pour que chacun puisse lire dans sa propre langue.`,
				link: { href: '#languages', label: 'Voir ce que chaque langue propose' }
			},
			{
				icon: 'compass',
				title: 'La vie de ceux qui nous ont précédés',
				body: 'Hudson Taylor, David Brainerd, Amy Carmichael, George Müller, Samuel Ajayi Crowther et d’autres, à travers leurs propres écrits et leurs biographies.',
				link: { href: '/biographies', label: 'Lire les biographies' }
			},
			{
				icon: 'calendar',
				title: 'Un chemin pour les nouveaux croyants',
				body: 'Les plans de lecture font parcourir un livre à un nouveau chrétien, une courte lecture par jour, et des livres clairs comme Le chemin vers Dieu sont un bon premier pas.',
				link: { href: '/plans', label: 'Voir les plans de lecture' }
			}
		],
		ideasHeading: 'Des idées pour votre mission',
		ideas: [
			{
				title: 'Le discipulat par un lien',
				body: 'Envoyez à chaque nouveau croyant le même court plan de lecture, et reprenez ce qu’il a lu quand vous vous voyez.'
			},
			{
				title: 'Former des responsables locaux',
				body: 'Lisez Le pasteur réformé de Baxter ou Comment amener les hommes à Christ de Torrey avec ceux que vous formez.'
			},
			{
				title: 'De la force pour durer',
				body: 'Quand l’œuvre est rude, lisez les récits et les lettres de ceux qui ont servi avant vous.'
			},
			{
				title: 'Vos soutiens restés au pays',
				body: 'Orientez vos amis qui prient vers les vies de missionnaires qui ont façonné votre propre appel.'
			}
		],
		shelves: [
			{
				title: 'Des vies qui ont envoyé des ouvriers',
				note: 'Les récits et les vies de ceux qui sont partis avant vous.',
				picks: [
					'things-as-they-are',
					'men-and-women-who-gave-everything-2',
					'tukutendereza',
					'watchman-nee-a-life',
					'a-retrospect-teens',
					'stepping-stones-2',
					'life-experience-gospel-labours'
				]
			},
			{
				title: 'Pour former des responsables locaux',
				note: 'Des livres à lire avec ceux que vous faites grandir.',
				picks: [
					'how-to-bring-men-to-christ',
					'the-reformed-pastor',
					'the-fundamental-doctrines-of-the-christian-faith',
					'men-who-tended-the-flock-2',
					'men-of-prayer-2',
					'the-person-and-work-of-the-holy-spirit',
					'key-teachings-of-richard-baxter',
					'clothed-with-strength-and-dignity'
				]
			},
			{
				title: 'Pour les nouveaux croyants',
				note: 'De premiers livres clairs et chaleureux, à offrir à qui vient de croire.',
				picks: [
					'the-way-to-god',
					'all-of-grace',
					'around-the-wicket-gate',
					'pilgrims-progress',
					'absolute-surrender',
					'the-secret-of-guidance',
					'thoughts-for-the-quiet-hour'
				]
			}
		],
		plans: [
			'deeper-life-in-christ',
			'school-of-prayer-31-days',
			'power-from-on-high',
			'humility-12-days'
		],
		authors: [
			'hudson-taylor',
			'david-brainerd',
			'amy-carmichael',
			'george-muller',
			'samuel-ajayi-crowther',
			'john-r-mott',
			'david-livingstone'
		],
		languages: true,
		invite: {
			text: 'Des classiques chrétiens gratuits à lire sur n’importe quel téléphone, en plusieurs langues, sans rien payer ni s’inscrire : Ochorus.',
			href: '/books'
		},
		questions: [
			{ q: 'Ochorus est-il vraiment gratuit ?', a: FREE_ANSWER },
			{
				q: 'Les personnes que je sers ont-elles besoin d’un compte ?',
				a: 'Non. Toute personne qui a le lien peut lire, sans rien payer et sans s’inscrire. Un compte gratuit reste possible et sert seulement à garder la progression et les notes à jour sur plusieurs appareils.'
			},
			{
				q: 'Quelles langues sont disponibles ?',
				a: `Les livres paraissent ${IN_LANGUAGES}. Chaque langue a ses propres éditions : la bibliothèque de chaque langue ne montre que ce qui y a été publié.`
			},
			{
				q: 'Peut-on demander un livre dans une langue que nous servons ?',
				a: 'Écrivez-nous. Nous serions heureux de savoir quels livres et quelles langues aideraient le plus votre œuvre.'
			}
		],
		closeHeading: 'Partagez les classiques avec ceux que vous servez',
		closeBody: 'Parcourez la bibliothèque, ou commencez par la vie des missionnaires qui vous ont précédés.'
	},
	{
		slug: 'chaplains',
		title: 'Des classiques chrétiens gratuits pour les aumôniers de prison, d’hôpital et des armées',
		lead: 'Des livres et des sermons pour ceux qui traversent l’enfermement, la maladie, le deuil ou le danger, gratuits et sans compte. Bunyan a écrit en prison ; Ignace a écrit ses lettres en marchant vers le martyre ; Hannah Whitall Smith a parlé du Dieu de toute consolation.',
		seoTitle: 'Livres chrétiens gratuits pour les aumôniers',
		seoDescription:
			'Classiques chrétiens et sermons gratuits pour aumôniers de prison, d’hôpital et des armées : souffrance, deuil, espérance, et éditions simplifiées. Sans compte.',
		primary: { href: '#shelves', label: 'Des livres pour les jours difficiles' },
		secondary: { href: '/sermons', label: 'Des sermons courts' },
		pointsHeading: 'Pourquoi les aumôniers utilisent Ochorus',
		points: [
			{
				icon: 'book',
				title: 'Gratuit, sans rien à remplir',
				body: 'Chaque livre et chaque sermon se lit gratuitement sans compte : on peut l’offrir à n’importe qui, sans budget, sans formulaire et sans identifiant.',
				link: { href: '/books', label: 'Parcourir les livres' }
			},
			{
				icon: 'heart',
				title: 'Écrits dans les lieux difficiles',
				body: 'Des classiques écrits en prison, dans la maladie ou sous la persécution : Le Voyage du pèlerin, les lettres d’Ignace, les Pensées de Pascal et la vie de Watchman Nee.',
				link: { href: '/topics', label: 'Parcourir par thème' }
			},
			{
				icon: 'mic',
				title: 'Un sermon pour une visite',
				body: 'Des sermons courts de Spurgeon, Moody, Corrie ten Boom et d’autres se lisent en une seule visite, dans une chambre ou une cellule, et beaucoup sont accompagnés de questions d’étude.',
				link: { href: '/sermons', label: 'Lire les sermons' }
			},
			{
				icon: 'layers',
				title: 'Des mots plus simples quand il le faut',
				body: 'Plusieurs classiques sont racontés en langage simple dans des éditions pour jeunes lecteurs et pour ados, qui conviennent aussi aux adultes pour qui les originaux sont difficiles.',
				link: { href: '/young-readers', label: 'Voir les éditions simplifiées' }
			}
		],
		ideasHeading: 'Des idées pour votre aumônerie',
		ideas: [
			{
				title: 'Un livre pour les longues journées',
				body: 'À quelqu’un qui fait face à un long séjour, donnez le lien vers un seul livre et un plan de lecture à suivre, une courte lecture par jour.'
			},
			{
				title: 'Un groupe d’étude',
				body: 'Lisez ensemble un sermon chaque semaine et parcourez ses questions.'
			},
			{
				title: 'Des mots pour le deuil et la peur',
				body: 'Tournez-vous vers Le Dieu de toute consolation, Toutes choses concourent au bien ou Le Roseau froissé pour ceux qui souffrent.'
			},
			{
				title: 'Une promesse pour chaque jour',
				body: 'Le carnet de chèques de la banque de la foi de Spurgeon offre une promesse de l’Écriture pour chaque jour de l’année.'
			}
		],
		shelves: [
			{
				title: 'Pour la souffrance et le deuil',
				note: 'Du réconfort pour les longues nuits.',
				picks: [
					'the-god-of-all-comfort',
					'all-things-for-good',
					'the-bruised-reed',
					'he-holds-my-tomorrows',
					'cheque-book',
					'the-unselfishness-of-god',
					'days-of-heaven-upon-earth'
				]
			},
			{
				title: 'Depuis les lieux difficiles',
				note: 'Des livres écrits en prison, dans la maladie ou sous la persécution, et des vies éprouvées.',
				picks: [
					'pilgrims-progress',
					'epistles-of-ignatius',
					'pensees',
					'watchman-nee-a-life',
					'men-and-women-who-gave-everything-2',
					'a-brand-plucked-from-the-fire',
					'life-experience-gospel-labours'
				]
			},
			{
				title: 'Avec des mots plus simples',
				note: 'Des récits qui conviennent à tout adulte pour qui les originaux sont difficiles.',
				picks: [
					'pilgrims-progress-teens',
					'all-of-grace-teens',
					'the-life-of-trust-teens',
					'a-retrospect-teens',
					'talks-to-the-farmer-teens',
					'amanda-smith-autobiography-teens',
					'corrie-ten-boom-a-life-children',
					'the-practice-of-the-presence-of-god-children'
				]
			}
		],
		plans: [
			'faith-in-the-fire',
			'the-puritan-heart',
			'humility-12-days',
			'the-inner-chamber-month'
		],
		authors: [
			'john-bunyan',
			'corrie-ten-boom',
			'hannah-whitall-smith',
			'richard-sibbes',
			'thomas-watson',
			'ignatius-of-antioch',
			'dietrich-bonhoeffer'
		],
		invite: {
			text: 'Des livres chrétiens et des sermons courts pour les jours difficiles, gratuits sur Ochorus. Aucun compte : il suffit d’ouvrir le lien et de lire.',
			href: '/books'
		},
		questions: [
			{ q: 'Ochorus est-il vraiment gratuit ?', a: FREE_ANSWER },
			{
				q: 'Le lecteur a-t-il besoin d’un compte ?',
				a: 'Non. Tout le monde peut lire sans s’inscrire, sans rien à remplir. Un compte gratuit reste possible et sert seulement à garder la progression et les notes à jour sur plusieurs appareils.'
			},
			{
				q: 'Y a-t-il quelque chose pour ceux qui ont du mal à lire ?',
				a: 'Oui. Les éditions pour jeunes lecteurs et pour ados racontent plusieurs classiques avec des mots plus simples, et chaque chapitre peut être lu à voix haute avec Écouter.'
			}
		],
		closeHeading: 'Apportez les classiques à ceux que vous servez',
		closeBody: 'Parcourez la bibliothèque, ou commencez par un sermon court à lire en une seule visite.'
	},
	{
		slug: 'bible-colleges',
		title: 'Une bibliothèque gratuite de sources pour les instituts bibliques et facultés de théologie',
		lead: 'Les Pères de l’Église, Pascal, les puritains et les prédicateurs des réveils, gratuits pour chaque étudiant et chaque enseignant. Une bibliothèque théologique toute prête pour n’importe quel institut, quel que soit son budget.',
		seoTitle: 'Sources chrétiennes gratuites pour les instituts bibliques',
		seoDescription:
			'Sources gratuites pour instituts bibliques et facultés de théologie : Pères de l’Église, Pascal, puritains et prédicateurs des réveils, avec biographies.',
		primary: { href: '#shelves', label: 'Voir les listes de lecture' },
		secondary: { href: '/originals', label: 'Compagnons d’étude' },
		pointsHeading: 'Pourquoi les instituts bibliques utilisent Ochorus',
		points: [
			{
				icon: 'book',
				title: 'Les sources, sans frais',
				body: 'Clément de Rome, Ignace d’Antioche, Athanase, saint Augustin, Thomas a Kempis, Owen, Baxter et Sibbes : les textes eux-mêmes, gratuits pour chaque étudiant.',
				link: { href: '/biographies', label: 'Rencontrer les auteurs' }
			},
			{
				icon: 'page',
				title: 'Pascal dans le texte',
				body: 'Les Pensées et Les Provinciales se lisent dans le français de Pascal, avec la Vie de Blaise Pascal par sa sœur pour les replacer dans leur temps.',
				link: { href: '/books', label: 'Parcourir les livres' }
			},
			{
				icon: 'list',
				title: 'Des compagnons d’étude',
				body: 'La collection Les enseignements clés présente la vie et la pensée d’un auteur, de Richard Baxter à Andrew Murray.',
				link: { href: '/originals', label: 'Voir les compagnons' }
			},
			{
				icon: 'mic',
				title: 'Des sermons à étudier',
				body: 'Des sermons de Luther, Chrysostome, Edwards, Whitefield, Wesley et Spurgeon, chacun accompagné de questions d’étude : une ressource pour les cours d’homilétique.',
				link: { href: '/sermons', label: 'Lire les sermons' }
			}
		],
		ideasHeading: 'Des idées pour votre institut',
		ideas: [
			{
				title: 'Lectures d’histoire de l’Église',
				body: 'Faites lire Sur l’incarnation du Verbe, Les Confessions et Les épîtres d’Ignace en parallèle du cours, chaque étudiant lisant le même texte.'
			},
			{
				title: 'Théologie pastorale',
				body: 'Lisez Le pasteur réformé de Baxter et Des hommes qui ont pris soin du troupeau avec ceux qui se préparent au ministère.'
			},
			{
				title: 'Cours de prédication',
				body: 'Étudiez les sermons d’Edwards, Whitefield, Wesley et Spurgeon, et voyez comment chacun a traité son texte.'
			},
			{
				title: 'Formation spirituelle',
				body: 'Accompagnez les lectures académiques de classiques de dévotion comme L’Imitation de Jésus-Christ et À l’école de la prière avec Christ.'
			}
		],
		shelves: [
			{
				title: 'Des Pères de l’Église à Pascal',
				note: 'L’Église ancienne, le Moyen Âge et le Grand Siècle, dans leurs propres mots.',
				picks: [
					'first-epistle-of-clement',
					'epistles-of-ignatius',
					'on-the-incarnation',
					'life-of-antony',
					'confessions',
					'the-imitation-of-christ',
					'pensees',
					'provincial-letters'
				]
			},
			{
				title: 'Des puritains aux réveils',
				note: 'La théologie puritaine et l’enseignement des prédicateurs des réveils.',
				picks: [
					'mortification-of-sin',
					'the-reformed-pastor',
					'the-bruised-reed',
					'all-things-for-good',
					'the-fundamental-doctrines-of-the-christian-faith',
					'the-person-and-work-of-the-holy-spirit',
					'the-fourfold-gospel',
					'key-teachings-of-richard-baxter'
				]
			},
			{
				title: 'Théologie pastorale et spirituelle',
				note: 'Pour la formation au ministère et la vie intérieure du serviteur.',
				picks: [
					'school-of-prayer',
					'power-through-prayer',
					'men-who-tended-the-flock-2',
					'humility-2',
					'godliness',
					'the-inner-chamber',
					'holy-in-christ'
				]
			}
		],
		plans: [
			'voices-of-the-early-church',
			'the-puritan-heart',
			'praying-men',
			'school-of-prayer-31-days'
		],
		authors: [
			'augustine-of-hippo',
			'athanasius-of-alexandria',
			'clement-of-rome',
			'ignatius-of-antioch',
			'john-owen',
			'richard-baxter',
			'richard-sibbes',
			'thomas-a-kempis'
		],
		invite: {
			text: 'Les sources de ce cours sont gratuites sur Ochorus : les Pères de l’Église, Pascal et les puritains, sur n’importe quel appareil, sans compte.',
			href: '/books'
		},
		questions: [
			{ q: 'Ochorus est-il vraiment gratuit ?', a: FREE_ANSWER },
			{
				q: 'Les étudiants ont-ils besoin d’un compte ?',
				a: 'Non. Les étudiants peuvent lire sans s’inscrire. Un compte gratuit reste possible : il garde la progression, les notes et les livres enregistrés à jour sur tous les appareils.'
			},
			{
				q: 'Quelles traditions sont représentées ?',
				a: 'La bibliothèque française va de l’Église ancienne au Moyen Âge, de Pascal aux puritains, et jusqu’aux mouvements de réveil et de mission, avec des auteurs de nombreuses traditions. Elle grandit au fil des mois.'
			}
		],
		closeHeading: 'Donnez à vos étudiants toute la tradition',
		closeBody: 'Parcourez la bibliothèque, ou commencez par les biographies des auteurs que vous enseignez.'
	},
	{
		slug: 'schools',
		title: 'Des classiques chrétiens gratuits pour votre classe',
		lead: 'Des sources de vingt siècles d’Église, gratuites pour chaque élève sur n’importe quel appareil. Athanase, saint Augustin, Bunyan et Pascal, des vies de foi, et plusieurs classiques racontés pour les enfants et les adolescents.',
		seoTitle: 'Classiques chrétiens gratuits pour les écoles',
		seoDescription:
			'Classiques chrétiens gratuits pour les écoles : sources pour l’histoire, la littérature et la Bible, biographies, et éditions pour enfants et adolescents.',
		primary: { href: '#shelves', label: 'Listes de lecture par matière' },
		secondary: { href: '/teens', label: 'Livres pour adolescents' },
		pointsHeading: 'Pourquoi les écoles utilisent Ochorus',
		points: [
			{
				icon: 'book',
				title: 'Des lectures imposées sans frais',
				body: 'Chaque livre se lit gratuitement : toute une classe peut lire le même texte sans budget de manuels et sans licences à gérer.',
				link: { href: '/books', label: 'Parcourir les livres' }
			},
			{
				icon: 'layers',
				title: 'Un texte, plusieurs niveaux',
				body: 'Le Voyage du pèlerin et les Entretiens avec le fermier existent en édition pour enfants, en édition pour ados et en texte intégral : une classe hétérogène peut lire la même histoire à différents niveaux.',
				link: { href: '/young-readers', label: 'Voir les éditions pour jeunes lecteurs' }
			},
			{
				icon: 'users',
				title: 'Des biographies pour chaque époque',
				body: 'De longues vies des auteurs, de l’Église ancienne au vingtième siècle, donnent aux élèves l’histoire qui se cache derrière chaque livre.',
				link: { href: '/biographies', label: 'Lire les biographies' }
			},
			{
				icon: 'page',
				title: 'Pascal en version originale',
				body: 'Les Pensées et Les Provinciales se lisent dans le français de Pascal, de quoi relier le cours de lettres et l’histoire des idées.',
				link: { href: '/books', label: 'Parcourir les livres' }
			}
		],
		ideasHeading: 'Des idées pour votre école',
		ideas: [
			{
				title: 'L’histoire de l’Église par les sources',
				body: 'Lisez Sur l’incarnation du Verbe d’Athanase, Les Confessions de saint Augustin et la Première épître de Clément en parallèle de l’histoire qu’ils ont vécue.'
			},
			{
				title: 'Une littérature d’héritage chrétien',
				body: 'Étudiez Le Voyage du pèlerin et les Pensées de Pascal, avec des éditions pour les plus jeunes quand elles existent.'
			},
			{
				title: 'Des exposés biographiques',
				body: 'Laissez chaque élève choisir un auteur, lire sa biographie, et présenter ce qu’il croyait et pourquoi cela comptait.'
			},
			{
				title: 'Chapelle et temps de recueillement',
				body: 'Utilisez un plan de lecture ou un sermon court pour une chapelle ou un moment de recueillement en classe.'
			}
		],
		shelves: [
			{
				title: 'Des sources pour l’histoire',
				note: 'Vingt siècles d’Église, lus dans les mots de ceux qui les ont vécus.',
				picks: [
					'on-the-incarnation',
					'confessions',
					'first-epistle-of-clement',
					'life-of-antony',
					'epistles-of-ignatius',
					'life-experience-gospel-labours',
					'tukutendereza',
					'life-of-pascal'
				]
			},
			{
				title: 'Une littérature d’héritage chrétien',
				note: 'Allégorie, pensées, polémique et récits pour le cours de lettres.',
				picks: [
					'pilgrims-progress',
					'pensees',
					'provincial-letters',
					'the-imitation-of-christ',
					'talks-to-the-farmer',
					'things-as-they-are',
					'around-the-wicket-gate'
				]
			},
			{
				title: 'Pour les plus jeunes',
				note: 'Des éditions pour ados et pour enfants pour les petites classes.',
				picks: [
					'pilgrims-progress-teens',
					'talks-to-the-farmer-teens',
					'a-retrospect-teens',
					'amanda-smith-autobiography-teens',
					'pilgrims-progress-children',
					'mary-slessor-a-life-children',
					'c-s-lewis-a-life-children',
					'brave-for-god'
				]
			}
		],
		plans: [
			'voices-of-the-early-church',
			'growing-in-wisdom-18-days',
			'first-steps-for-teens',
			'humility-12-days'
		],
		authors: [
			'augustine-of-hippo',
			'athanasius-of-alexandria',
			'john-bunyan',
			'clement-of-rome',
			'thomas-a-kempis',
			'richard-allen',
			'samuel-ajayi-crowther'
		],
		levels: ['pilgrims-progress', 'talks-to-the-farmer'],
		invite: {
			text: 'Nos textes de classe sont gratuits sur Ochorus, sur n’importe quel appareil et à plusieurs niveaux de lecture, sans compte.',
			href: '/books'
		},
		questions: [
			{ q: 'Ochorus est-il vraiment gratuit ?', a: FREE_ANSWER },
			{
				q: 'Les élèves ont-ils besoin d’un compte ?',
				a: 'Non. Les élèves peuvent lire sans s’inscrire. Un compte gratuit reste possible : il garde la progression, les notes et les livres enregistrés d’un lecteur à jour sur tous ses appareils.'
			},
			{
				q: 'Pour quels âges est-ce adapté ?',
				a: 'Les éditions pour enfants conviennent aux plus jeunes et à la lecture à voix haute, les éditions pour ados aux grands enfants et aux adolescents, et les textes intégraux aux grands élèves.'
			}
		],
		closeHeading: 'Faites entrer les classiques dans votre classe',
		closeBody: 'Parcourez la bibliothèque, ou commencez par les livres écrits pour les adolescents.'
	},
	{
		slug: 'homeschool',
		title: 'Une bibliothèque gratuite de classiques chrétiens pour l’instruction en famille',
		lead: 'Des livres vivants tirés de vingt siècles d’Église, gratuits sur n’importe quel appareil. Bunyan, saint Augustin, Müller, Hudson Taylor et Spurgeon, avec plusieurs classiques racontés pour les enfants et pour les adolescents.',
		seoTitle: 'Classiques chrétiens gratuits pour l’instruction en famille',
		seoDescription:
			'Livres chrétiens vivants et gratuits pour l’instruction en famille : classiques, vies de missionnaires, éditions pour enfants et ados, plans de lecture.',
		primary: { href: '/young-readers', label: 'Livres pour jeunes lecteurs' },
		secondary: { href: '#plans', label: 'Dévotions en famille' },
		pointsHeading: 'Pourquoi les familles qui instruisent à la maison utilisent Ochorus',
		points: [
			{
				icon: 'book',
				title: 'Une étagère de livres vivants, gratuite',
				body: 'Des classiques chrétiens pour l’histoire, la littérature, la biographie et la Bible. Ni frais de programme ni abonnement, pour une famille comme pour toute une coopérative.',
				link: { href: '/books', label: 'Parcourir les livres' }
			},
			{
				icon: 'layers',
				title: 'La même histoire à chaque niveau',
				body: 'Le Voyage du pèlerin et les Entretiens avec le fermier existent en édition pour enfants, en édition pour ados et en texte intégral : frères et sœurs lisent la même histoire, chacun à son niveau.',
				link: { href: '/young-readers', label: 'Voir les éditions pour jeunes lecteurs' }
			},
			{
				icon: 'calendar',
				title: 'Un programme tout prêt',
				body: 'Les plans de lecture proposent une courte lecture par jour, dont des dévotions familiales de cinq minutes.',
				link: { href: '/plans', label: 'Voir les plans de lecture' }
			},
			{
				icon: 'headphones',
				title: 'La lecture à voix haute intégrée',
				body: 'Chaque chapitre peut être lu à voix haute avec Écouter : pour le temps de lecture partagée, pour un jeune lecteur qui suit les mots, ou en voiture.'
			}
		],
		ideasHeading: 'Des idées pour l’instruction en famille',
		ideas: [
			{
				title: 'L’histoire de l’Église par les sources',
				body: 'Lisez Les Confessions de saint Augustin, Sur l’incarnation du Verbe d’Athanase et la Vie d’Antoine en parallèle des leçons d’histoire, avec les biographies des auteurs pour le contexte.'
			},
			{
				title: 'Des vies de missionnaires',
				body: 'Les histoires vraies de George Müller, Hudson Taylor, Mary Slessor et Amanda Smith, racontées pour les enfants et les adolescents.'
			},
			{
				title: 'Des clubs de lecture en coopérative',
				body: 'Chaque famille peut lire le même livre sans frais. Partagez un lien et retrouvez-vous pour en parler.'
			},
			{
				title: 'Le temps du matin',
				body: 'Ouvrez la journée avec un plan de dévotions familiales ou une page des Pensées pour l’heure du recueillement de Moody.'
			}
		],
		shelves: [
			{
				title: 'À lire à voix haute aux petits',
				note: 'Des histoires à partager autour de la table ou au coucher.',
				picks: [
					'pilgrims-progress-children',
					'the-life-of-trust-children',
					'brave-for-god',
					'brave-for-god-2',
					'mary-slessor-a-life-children',
					'the-practice-of-the-presence-of-god-children',
					'talks-to-the-farmer-children',
					'amanda-smith-autobiography-children'
				]
			},
			{
				title: 'Collège et lycée',
				note: 'Les éditions pour ados, et des livres que les plus grands sont prêts à lire.',
				picks: [
					'pilgrims-progress-teens',
					'a-retrospect-teens',
					'the-life-of-trust-teens',
					'talks-to-the-farmer-teens',
					'amanda-smith-autobiography-teens',
					'growing-in-wisdom',
					'all-of-grace-teens'
				]
			},
			{
				title: 'Des livres vivants pour l’histoire',
				note: 'L’histoire de l’Église racontée par ceux qui l’ont faite.',
				picks: [
					'on-the-incarnation',
					'confessions',
					'life-of-antony',
					'epistles-of-ignatius',
					'first-epistle-of-clement',
					'life-of-pascal',
					'tukutendereza'
				]
			}
		],
		plans: [
			'family-devotions-pilgrims-journey',
			'family-devotions-heroes-who-trusted-god',
			'family-devotions-brave-and-faithful',
			'family-devotions-talking-with-god',
			'rooted-three-months-books-1-3'
		],
		authors: [
			'george-muller',
			'hudson-taylor',
			'samuel-ajayi-crowther',
			'john-bunyan',
			'amanda-berry-smith',
			'augustine-of-hippo',
			'charles-h-spurgeon'
		],
		levels: ['pilgrims-progress', 'talks-to-the-farmer'],
		invite: {
			text: 'Une bibliothèque gratuite de livres chrétiens vivants pour tous les âges, avec des éditions pour enfants et pour ados et des dévotions familiales : Ochorus.',
			href: '/young-readers'
		},
		questions: [
			{ q: 'Ochorus est-il vraiment gratuit ?', a: FREE_ANSWER },
			{
				q: 'Pour quels âges est Ochorus ?',
				a: 'Pour tous. Les éditions pour enfants sont écrites pour les plus jeunes et pour la lecture à voix haute en famille, les éditions pour ados pour les plus grands, et les textes intégraux pour les grands élèves et les parents.'
			},
			{
				q: 'Les éditions pour enfants sont-elles fidèles aux originaux ?',
				a: 'Chaque édition pour jeunes lecteurs raconte le classique avec des mots plus simples, en gardant son histoire et son message. La page de chaque édition renvoie aux autres : un lecteur peut passer à l’édition pour ados puis au texte intégral quand il est prêt.'
			},
			{
				q: 'Notre coopérative ou association peut-elle partager Ochorus avec des familles ?',
				a: 'Avec plaisir. Faites un lien vers cette page ou vers n’importe quel livre, plan ou auteur. Si vous souhaitez parler de l’utilisation d’Ochorus avec un groupe plus large, écrivez-nous.'
			}
		],
		closeHeading: 'Commencez les lectures de ce trimestre',
		closeBody:
			'Parcourez les éditions pour jeunes lecteurs, ou choisissez un plan de lecture à suivre ensemble.'
	},
	{
		slug: 'parents',
		title: 'De grands livres chrétiens pour vos enfants, gratuits',
		lead: 'Des histoires vraies de foi et de courage, des récits classiques et de courtes dévotions familiales, écrits pour les enfants et les adolescents. Gratuits sur n’importe quel appareil, sans publicité et sans compte.',
		seoTitle: 'Livres chrétiens gratuits pour vos enfants',
		seoDescription:
			'Livres chrétiens gratuits pour enfants et ados : histoires vraies de foi, classiques racontés et dévotions familiales de cinq minutes. Sans pub ni compte.',
		primary: { href: '/young-readers', label: 'Livres pour enfants' },
		secondary: { href: '#plans', label: 'Dévotions familiales de cinq minutes' },
		pointsHeading: 'Pourquoi les parents utilisent Ochorus',
		points: [
			{
				icon: 'heart',
				title: 'Des héros dignes d’admiration',
				body: 'De vrais hommes et de vraies femmes qui ont fait confiance à Dieu, parmi eux George Müller, Hudson Taylor, Mary Slessor, Amanda Smith et Corrie ten Boom, avec leur histoire racontée pour les enfants.',
				link: { href: '/young-readers', label: 'Les rencontrer' }
			},
			{
				icon: 'calendar',
				title: 'Des dévotions familiales de cinq minutes',
				body: 'De courts plans de lecture faits pour les familles : un chapitre par soir, lu à voix haute ensemble au coucher ou au petit-déjeuner.',
				link: { href: '/plans', label: 'Voir les plans de lecture' }
			},
			{
				icon: 'layers',
				title: 'Des livres qui grandissent avec eux',
				body: 'Le Voyage du pèlerin existe en édition pour enfants, en édition pour ados et en texte intégral. L’enfant qui l’aime à sept ans pourra lire le livre entier à dix-sept.',
				link: { href: '/teens', label: 'Livres pour adolescents' }
			},
			{
				icon: 'headphones',
				title: 'Écouter ensemble',
				body: 'Chaque chapitre peut être lu à voix haute avec Écouter : les enfants suivent les mots, ou écoutent en voiture.'
			}
		],
		ideasHeading: 'Des idées pour les familles',
		ideas: [
			{
				title: 'Des histoires pour le coucher',
				body: 'Lisez ensemble un chapitre d’une édition pour enfants, ou laissez Écouter le lire pendant qu’ils suivent.'
			},
			{
				title: 'Une habitude quotidienne pour les plus grands',
				body: 'Des méditations de trente jours comme Enracinés et Filles du Roi sont écrites pour qu’un jeune les lise seul sur son téléphone, quelques minutes par jour.'
			},
			{
				title: 'En parler ensemble',
				body: 'Les chapitres sont courts : il reste du temps pour parler de ce que vous avez lu et prier ensemble ensuite.'
			},
			{
				title: 'Quelque chose de sûr à leur confier',
				body: 'Pas de publicité, pas de fil d’actualité, rien à acheter. Seulement de bons livres, prêts dès qu’ils ont envie de lire.'
			}
		],
		shelves: [
			{
				title: 'Histoires du soir',
				note: 'Des favoris à lire ensemble.',
				picks: [
					'pilgrims-progress-children',
					'brave-for-god',
					'the-life-of-trust-children',
					'amanda-smith-autobiography-children',
					'corrie-ten-boom-a-life-children',
					'the-practice-of-the-presence-of-god-children',
					'talks-to-the-farmer-children'
				]
			},
			{
				title: 'Pour les plus grands, à lire seuls',
				note: 'Des méditations de trente jours et des classiques racontés, pour leur propre téléphone.',
				picks: [
					'rooted-1',
					'daughters-of-the-king-2',
					'pilgrims-progress-teens',
					'all-of-grace-teens',
					'the-life-of-trust-teens',
					'growing-in-wisdom',
					'rooted-2'
				]
			},
			{
				title: 'D’autres héros pour les jeunes lecteurs',
				note: 'Des histoires vraies de courage, racontées pour les enfants.',
				picks: [
					'brave-for-god-2',
					'a-retrospect-children',
					'elisabeth-elliot-a-life-children',
					'mary-slessor-a-life-children',
					'pandita-ramabai-a-life-children',
					'john-hyde-a-life-children',
					'c-s-lewis-a-life-children'
				]
			}
		],
		plans: [
			'family-devotions-talking-with-god',
			'family-devotions-heroes-who-trusted-god',
			'family-devotions-brave-and-faithful',
			'family-devotions-pilgrims-journey',
			'rooted-three-months-books-1-3'
		],
		authors: [
			'amanda-berry-smith',
			'george-muller',
			'susanna-wesley',
			'isaac-watts',
			'corrie-ten-boom',
			'hudson-taylor',
			'elisabeth-elliot'
		],
		levels: ['pilgrims-progress', 'talks-to-the-farmer'],
		invite: {
			text: 'Des livres chrétiens gratuits pour enfants et ados sur Ochorus : histoires vraies, récits classiques et dévotions familiales de cinq minutes. Sans pub, rien à acheter.',
			href: '/young-readers'
		},
		questions: [
			{ q: 'Ochorus est-il vraiment gratuit ?', a: FREE_ANSWER },
			{
				q: 'Mon enfant a-t-il besoin d’un compte ?',
				a: 'Non. Tout le monde peut lire sans s’inscrire. Un compte gratuit reste possible : il garde la progression, les notes et les livres enregistrés à jour sur tous les appareils.'
			},
			{
				q: 'Pour quels âges sont les livres ?',
				a: 'Les livres pour jeunes lecteurs se lisent avec un adulte ou seul, les livres pour ados s’adressent aux grands enfants et aux adolescents, et les classiques intégraux les attendent quand ils voudront aller plus loin.'
			},
			{
				q: 'Est-ce sûr pour les enfants ?',
				a: 'Ochorus n’a ni publicité ni rien à acheter. C’est une bibliothèque de livres chrétiens, et rien d’autre ne vient disputer l’attention de votre enfant.'
			}
		],
		closeHeading: 'Trouvez un livre à lire ensemble ce soir',
		closeBody: 'Commencez par les livres pour enfants, ou par les livres pour adolescents.'
	}
];
