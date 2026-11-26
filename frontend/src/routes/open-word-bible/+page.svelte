<script lang="ts">
	import { toBookTile, type BookSummary, type SeriesDetail } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumbLd, absUrl, hreflangExact } from '$lib/seo';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { BIBLE_PATH, BIBLE_SERIES, bibleIn, bibleText, type BibleText } from '$lib/bible';
	import {
		OWB_FAN,
		OWB_LANGUAGES,
		OWB_LEVELS,
		OWB_PATH,
		OWB_READ_URL,
		OWB_URL
	} from '$lib/openWordBible';
	import Seo from '$lib/components/Seo.svelte';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import Arrow from '$lib/components/Arrow.svelte';

	/**
	 * The Open Word Bible: what the translation is, how it is made, and where
	 * to find all of it (OpenWordBible.org). The page the Bible's byline links
	 * to, in place of an author page — the translation has no biography.
	 *
	 * Its prose is the page's own, in each hub locale (`COPY`, a `BibleText`
	 * each): the page, like the Bible it describes, exists only in
	 * BIBLE_LOCALES (the loader 404s elsewhere), so a language joins the list
	 * with its words here. The sample verses and the decision are the
	 * translation's own (John 3:16, record JHN.3.16.s1), not paraphrase: in
	 * English all three levels; in Spanish, French and Portuguese the Balanced
	 * text Ochorus prints (`owb-es-b`, `owb-fr-b`, `owb-pt-b`), the one level
	 * bundled in each, so the other two cards there describe their level
	 * without a sample.
	 */
	let { data } = $props();
	const series = $derived<SeriesDetail | null>(data.series);
	const t = i18n.t;
	const lang = getLang();
	const say = (text: BibleText) => bibleText(text, lang);

	const books = $derived(series?.books ?? []);
	const fan = $derived.by(() => {
		const bySlug = new Map(books.map((b) => [b.slug, b]));
		return OWB_FAN.map((s) => bySlug.get(s)).filter((b): b is BookSummary => !!b);
	});

	// John 3:16 at each level, the reader settings at their defaults; per
	// language, only the levels that language's text has.
	const SAMPLE: Record<string, Partial<Record<(typeof OWB_LEVELS)[number]['code'], string>>> = {
		en: {
			'OWB-L':
				'For in this way God loved the world, that he gave the Son, the one and only, in order that everyone who believes in him may not perish but may have eternal life.',
			'OWB-B':
				"For God's love for the world was such that he gave his one and only Son, so that everyone who believes in him may not perish but have eternal life.",
			'OWB-R':
				'God loved the people of the world, and this is how he loved them: he gave his one and only Son, so that everyone who believes in him will not be lost but will have eternal life.'
		},
		es: {
			'OWB-B':
				'Porque Dios amó al mundo de tal manera que dio a Su Hijo único, para que todo el que cree en Él no perezca, sino que tenga vida eterna.'
		},
		fr: {
			'OWB-B':
				'Car tel a été l’amour de Dieu pour le monde qu’Il a donné Son Fils unique, pour que quiconque croit en Lui ne périsse pas, mais possède la vie éternelle.'
		},
		pt: {
			'OWB-B':
				'Pois o amor de Deus pelo mundo foi tal que Ele deu o Seu Filho único, para que todo aquele que crê Nele não pereça, mas tenha a vida eterna.'
		}
	};
	const samples = SAMPLE[lang] ?? {};

	/** The page's words, one per hub locale. */
	const COPY = {
		title: { en: 'The Open Word Bible — Ochorus', es: 'La Open Word Bible — Ochorus', fr: 'L’Open Word Bible — Ochorus', pt: 'A Open Word Bible — Ochorus' },
		description: {
			en: 'The Open Word Bible is a new, free translation of the Bible from Hebrew and Greek, at three levels, with every decision explained. Ochorus prints its Balanced text.',
			es: 'La Open Word Bible es una nueva traducción gratuita de la Biblia desde el hebreo y el griego, en tres niveles, con cada decisión explicada. Ochorus imprime en español su nivel Equilibrado.',
			fr: 'L’Open Word Bible est une nouvelle traduction gratuite de la Bible à partir de l’hébreu et du grec, en trois niveaux, où chaque décision est expliquée. Ochorus en publie en français le niveau Équilibré.',
			pt: 'A Open Word Bible é uma nova tradução gratuita da Bíblia a partir do hebraico e do grego, em três níveis, com cada decisão explicada. O Ochorus publica em português o seu nível Equilibrado.'
		},
		eyebrow: { en: 'The translation', es: 'La traducción', fr: 'La traduction', pt: 'A tradução' },
		heading: { en: 'The Open Word Bible', es: 'La Open Word Bible', fr: 'L’Open Word Bible', pt: 'A Open Word Bible' },
		lede: {
			en: "A new translation of the Bible from the Hebrew and Greek, in today's English. Every sentence is translated three ways, from word-for-word to plain, and every choice the translators made is written down with its reason, so you can see why it reads as it does. It is free for anyone to read, copy and share.",
			es: 'Una nueva traducción de la Biblia hecha directamente del hebreo y el griego. Traduce cada oración en tres niveles, de la palabra por palabra a la más sencilla, y deja por escrito cada decisión de los traductores con su razón, para que se pueda ver por qué dice lo que dice. En Ochorus se lee en español, en su nivel Equilibrado, y cualquiera puede leerla, copiarla y compartirla, gratis.',
			fr: 'Une nouvelle traduction de la Bible faite directement à partir de l’hébreu et du grec. Chaque phrase y est traduite à trois niveaux, du mot à mot au plus simple, et chaque choix des traducteurs est consigné avec sa raison, pour qu’on puisse voir pourquoi le texte dit ce qu’il dit. Sur Ochorus, on la lit en français, au niveau Équilibré, et chacun peut la lire, la copier et la partager, gratuitement.',
			pt: 'Uma nova tradução da Bíblia feita diretamente do hebraico e do grego. Cada frase é traduzida em três níveis, da palavra por palavra à mais simples, e cada decisão dos tradutores fica registrada com a sua razão, para que se possa ver por que o texto diz o que diz. No Ochorus ela é lida em português, no nível Equilibrado, e qualquer pessoa pode lê-la, copiá-la e compartilhá-la, de graça.'
		},
		onOchorus: { en: 'on Ochorus', es: 'en Ochorus', fr: 'sur Ochorus', pt: 'no Ochorus' },
		languages: { en: 'Hebrew & Greek', es: 'Hebreo y griego', fr: 'Hébreu et grec', pt: 'Hebraico e grego' },
		publicDomain: { en: 'Public domain (CC0)', es: 'Dominio público (CC0)', fr: 'Domaine public (CC0)', pt: 'Domínio público (CC0)' },
		readBible: { en: 'Read the Bible', es: 'Leer la Biblia', fr: 'Lire la Bible', pt: 'Ler a Bíblia' },
		visit: { en: 'Visit OpenWordBible.org', es: 'Visitar OpenWordBible.org', fr: 'Visiter OpenWordBible.org', pt: 'Visitar OpenWordBible.org' },
		levelsEyebrow: { en: 'Three levels', es: 'Tres niveles', fr: 'Trois niveaux', pt: 'Três níveis' },
		levelsHeading: { en: 'One verse, translated three ways', es: 'Tres maneras de traducir', fr: 'Trois manières de traduire', pt: 'Três maneiras de traduzir' },
		levelsLede: {
			en: 'Translations usually pick one point between word-for-word and thought-for-thought. The Open Word Bible gives you three, side by side. Here is John 3:16.',
			es: 'Las traducciones suelen escoger un punto entre la palabra por palabra y el sentido por sentido. La Open Word Bible ofrece tres, lado a lado. Ochorus imprime el Equilibrado; aquí está Juan 3:16 en él.',
			fr: 'Les traductions choisissent d’ordinaire un point entre le mot à mot et le sens pour sens. L’Open Word Bible en propose trois, côte à côte. Ochorus publie le niveau Équilibré ; voici Jean 3:16 dans ce niveau.',
			pt: 'As traduções costumam escolher um ponto entre a palavra por palavra e o sentido por sentido. A Open Word Bible oferece três, lado a lado. O Ochorus publica o Equilibrado; aqui está João 3:16 nesse nível.'
		},
		ours: { en: 'On Ochorus', es: 'En Ochorus', fr: 'Sur Ochorus', pt: 'No Ochorus' },
		workingEyebrow: { en: 'Open reasoning', es: 'Razonamiento abierto', fr: 'Un raisonnement ouvert', pt: 'Raciocínio aberto' },
		workingHeading: { en: 'Every sentence shows its working', es: 'Cada oración muestra su razonamiento', fr: 'Chaque phrase montre son raisonnement', pt: 'Cada frase mostra o seu raciocínio' },
		working1: {
			en: 'Behind each sentence is a record: the original words, a literal gloss, the three translations, and every decision the translators made, with the options they set aside and the reason for their choice. Where a reading is uncertain, the record says so.',
			es: 'Detrás de cada oración hay un registro: las palabras originales, una glosa literal, las tres traducciones y cada decisión que tomaron los traductores, con las opciones que descartaron y la razón de su elección. Donde una lectura es incierta, el registro lo dice.',
			fr: 'Derrière chaque phrase, il y a une fiche : les mots originaux, une glose littérale, les trois traductions et chaque décision des traducteurs, avec les options écartées et la raison de leur choix. Là où une lecture est incertaine, la fiche le dit.',
			pt: 'Por trás de cada frase há um registro: as palavras originais, uma glosa literal, as três traduções e cada decisão que os tradutores tomaram, com as opções que deixaram de lado e a razão da escolha. Onde uma leitura é incerta, o registro diz isso.'
		},
		working2: {
			en: 'On OpenWordBible.org you can open any verse and read its record, compare the three levels, and follow the cross-references in the margin.',
			es: 'En OpenWordBible.org se puede abrir cualquier versículo y leer su registro, comparar los tres niveles y seguir las referencias cruzadas del margen.',
			fr: 'Sur OpenWordBible.org, on peut ouvrir n’importe quel verset et lire sa fiche, comparer les trois niveaux et suivre les renvois de la marge.',
			pt: 'No OpenWordBible.org é possível abrir qualquer versículo e ler o seu registro, comparar os três níveis e seguir as referências cruzadas da margem.'
		},
		readReasoning: {
			en: 'Read with the reasoning on OpenWordBible.org',
			es: 'Leer con el razonamiento en OpenWordBible.org',
			fr: 'Lire avec le raisonnement sur OpenWordBible.org',
			pt: 'Ler com o raciocínio no OpenWordBible.org'
		},
		recordCaption: { en: 'John 3:16 · a decision', es: 'Juan 3:16 · una decisión', fr: 'Jean 3:16 · une décision', pt: 'João 3:16 · uma decisão' },
		chosen: { en: 'Chosen', es: 'Elegido', fr: 'Retenu', pt: 'Escolhido' },
		chosenText: {
			en: '“in this way”: God’s love took the form of giving the Son',
			es: '«de esta manera»: el amor de Dios tomó la forma de dar al Hijo',
			fr: '« de cette manière » : l’amour de Dieu a pris la forme du don du Fils',
			pt: '“desta maneira”: o amor de Deus tomou a forma de dar o Filho'
		},
		setAside: { en: 'Set aside', es: 'Descartado', fr: 'Écarté', pt: 'Deixado de lado' },
		setAsideText: {
			en: '“so much”: God loved the world to such a degree',
			es: '«tanto»: Dios amó al mundo en tal grado',
			fr: '« tant » : Dieu a aimé le monde à un tel degré',
			pt: '“tanto”: Deus amou o mundo a tal ponto'
		},
		why: { en: 'Why', es: 'Por qué', fr: 'Pourquoi', pt: 'Por quê' },
		// The quotation of 3:14 is the Open Word Bible's, in each language.
		whyText: {
			en: 'In John the word normally means “thus, in this way”, and it has just been used in 3:14: “so must the Son of Man be lifted up”. This is how God loved the world: by giving the Son.',
			es: 'En Juan la palabra suele significar «así, de esta manera», y se acaba de usar en 3:14: «del mismo modo el Hijo del Hombre tiene que ser levantado en alto». Así es como Dios amó al mundo: dando al Hijo.',
			fr: 'Chez Jean, le mot signifie d’ordinaire « ainsi, de cette manière », et il vient d’être employé en 3:14 : « de la même manière, il faut que le Fils de l’homme soit élevé ». Voilà comment Dieu a aimé le monde : en donnant le Fils.',
			pt: 'Em João a palavra normalmente significa “assim, desta maneira”, e acabou de ser usada em 3:14: “do mesmo modo o Filho do Homem precisa ser elevado”. É assim que Deus amou o mundo: dando o Filho.'
		},
		sourcesEyebrow: { en: 'From the original languages', es: 'Desde las lenguas originales', fr: 'À partir des langues originales', pt: 'Das línguas originais' },
		sourcesHeading: { en: 'Translated from the source texts', es: 'Traducida de los textos fuente', fr: 'Traduite des textes sources', pt: 'Traduzida dos textos-fonte' },
		oldSource: {
			en: 'the Westminster Leningrad Codex, with the MACULA Hebrew word data, numbered as in the Hebrew.',
			es: 'el Códice de Leningrado de Westminster, con los datos de palabras hebreas de MACULA, numerado como en el hebreo.',
			fr: 'le Codex de Leningrad de Westminster, avec les données lexicales hébraïques de MACULA, numéroté comme dans l’hébreu.',
			pt: 'o Códice de Leningrado de Westminster, com os dados de palavras hebraicas do MACULA, numerado como no hebraico.'
		},
		newSource: {
			en: 'the SBL Greek New Testament, whose sentences and paragraphs the translation follows.',
			es: 'el Nuevo Testamento Griego de la SBL, cuyas oraciones y párrafos sigue la traducción.',
			fr: 'le Nouveau Testament grec de la SBL, dont la traduction suit les phrases et les paragraphes.',
			pt: 'o Novo Testamento Grego da SBL, cujas frases e parágrafos a tradução segue.'
		},
		noTyping: {
			en: 'No Hebrew or Greek is typed by hand: every original word is loaded from the source data, and checked against it.',
			es: 'Ninguna palabra hebrea o griega se escribe a mano: cada palabra original se carga desde los datos fuente y se coteja con ellos.',
			fr: 'Aucun mot hébreu ou grec n’est saisi à la main : chaque mot original est chargé depuis les données sources, et vérifié par rapport à elles.',
			pt: 'Nenhuma palavra hebraica ou grega é digitada à mão: cada palavra original é carregada dos dados-fonte e conferida com eles.'
		},
		freeEyebrow: { en: 'Free for everyone', es: 'Libre para todos', fr: 'Libre pour tous', pt: 'Livre para todos' },
		freeHeading: { en: 'Given to the public domain', es: 'Cedida al dominio público', fr: 'Versée au domaine public', pt: 'Cedida ao domínio público' },
		freeText: {
			en: 'The translation is released under CC0: no permission to ask, no fee, no limit on copies. Print it, quote it at length, put it in an app or a church bulletin. That is why it can sit in a free library like this one.',
			es: 'La traducción se publica bajo CC0: sin permisos que pedir, sin costo, sin límite de copias. Se puede imprimir, citar extensamente, poner en una aplicación o en el boletín de una iglesia. Por eso puede estar en una biblioteca gratuita como esta.',
			fr: 'La traduction est publiée sous CC0 : aucune permission à demander, aucun frais, aucune limite au nombre de copies. On peut l’imprimer, la citer longuement, la mettre dans une application ou dans le bulletin d’une Église. C’est pourquoi elle peut figurer dans une bibliothèque gratuite comme celle-ci.',
			pt: 'A tradução é publicada sob CC0: sem permissão a pedir, sem custo, sem limite de cópias. Pode ser impressa, citada extensamente, colocada num aplicativo ou no boletim de uma igreja. Por isso ela pode estar numa biblioteca gratuita como esta.'
		},
		follow: {
			en: 'English comes first, and these languages follow:',
			es: 'El inglés va primero, y le siguen estos idiomas:',
			fr: 'L’anglais vient en premier, et ces langues suivent :',
			pt: 'O inglês vem primeiro, e estas línguas vêm em seguida:'
		},
		languagesLabel: { en: 'Languages', es: 'Idiomas', fr: 'Langues', pt: 'Idiomas' },
		hereEyebrow: { en: 'On Ochorus', es: 'En Ochorus', fr: 'Sur Ochorus', pt: 'No Ochorus' },
		hereHeading: {
			en: 'Read it here like any book in the library',
			es: 'Se lee aquí como cualquier libro de la biblioteca',
			fr: 'Elle se lit ici comme n’importe quel livre de la bibliothèque',
			pt: 'Ela é lida aqui como qualquer livro da biblioteca'
		},
		everyBook: { en: 'Every book, in order', es: 'Todos los libros, en orden', fr: 'Tous les livres, dans l’ordre', pt: 'Todos os livros, em ordem' },
		everyBookText: {
			en: 'Genesis to Revelation, grouped by testament and division, each with its own cover in its Hebrew or Greek name.',
			es: 'De Génesis a Apocalipsis, agrupados por testamento y división, cada uno con su portada en su nombre hebreo o griego.',
			fr: 'De la Genèse à l’Apocalypse, regroupés par testament et par section, chacun avec sa couverture à son nom hébreu ou grec.',
			pt: 'De Gênesis a Apocalipse, agrupados por testamento e divisão, cada um com a sua capa no seu nome hebraico ou grego.'
		},
		through: { en: 'Straight through', es: 'De principio a fin', fr: 'Du début à la fin', pt: 'Do começo ao fim' },
		throughText: {
			en: 'Genesis to Revelation as one reading, with your place kept from book to book.',
			es: 'De Génesis a Apocalipsis como una sola lectura, con el lugar de lectura guardado de un libro a otro.',
			fr: 'De la Genèse à l’Apocalypse en une seule lecture, la page où l’on en est gardée d’un livre à l’autre.',
			pt: 'De Gênesis a Apocalipse como uma só leitura, com o ponto de leitura guardado de um livro para outro.'
		},
		daily: { en: 'A chapter a day', es: 'Un capítulo al día', fr: 'Un chapitre par jour', pt: 'Um capítulo por dia' },
		dailyText: {
			en: 'Reading plans such as John in 21 days, Proverbs in a month and Psalms in 150 days.',
			es: 'Planes de lectura que recorren la Biblia, o uno de sus libros, un capítulo a la vez.',
			fr: 'Des plans de lecture qui parcourent la Bible, ou l’un de ses livres, un chapitre à la fois.',
			pt: 'Planos de leitura que percorrem a Bíblia, ou um dos seus livros, um capítulo de cada vez.'
		},
		plansLink: { en: 'Reading plans', es: 'Planes de lectura', fr: 'Plans de lecture', pt: 'Planos de leitura' },
		intro: { en: 'An introduction to each book', es: 'Una introducción a cada libro', fr: 'Une introduction à chaque livre', pt: 'Uma introdução a cada livro' },
		introText: {
			en: 'Who wrote it, when and why, before you begin; and a closing note on what to carry away. Poetry is set line by line, as the Hebrew divides it.',
			es: 'Quién lo escribió, cuándo y por qué, antes de empezar; y una nota final sobre lo que conviene llevarse. La poesía se presenta línea por línea, como la divide el hebreo.',
			fr: 'Qui l’a écrit, quand et pourquoi, avant de commencer ; et une note finale sur ce qu’il faut en retenir. La poésie est présentée vers par vers, comme l’hébreu la divise.',
			pt: 'Quem o escreveu, quando e por quê, antes de começar; e uma nota final sobre o que levar consigo. A poesia é apresentada linha por linha, como o hebraico a divide.'
		},
		whole: { en: 'See the whole translation', es: 'Ver la traducción completa', fr: 'Voir toute la traduction', pt: 'Ver a tradução completa' },
		wholeText: {
			en: 'All three levels, every reasoning record, the interlinear view and the other languages as they are drafted live at OpenWordBible.org.',
			es: 'Los tres niveles, cada registro de razonamiento, la vista interlineal y los demás idiomas, a medida que se redactan, están en OpenWordBible.org.',
			fr: 'Les trois niveaux, chaque fiche de raisonnement, la vue interlinéaire et les autres langues, au fil de leur rédaction, se trouvent sur OpenWordBible.org.',
			pt: 'Os três níveis, cada registro de raciocínio, a visão interlinear e os outros idiomas, à medida que são redigidos, estão no OpenWordBible.org.'
		}
	} satisfies Record<string, BibleText>;

	const path = `${OWB_PATH}/`;
	const canonical = `${SITE_URL}${localizeHref(path)}`;
	const title = say(COPY.title);
	const description = say(COPY.description);
	// Wherever the hub is, as the hub's own hreflang: the series' languages
	// that the chrome links (the sitemap lists the page in the same set).
	const hreflang = $derived(
		series ? hreflangExact(path, series.available_languages.filter(bibleIn)) : null
	);
	const crumbsLd = breadcrumbLd([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.bible'), href: `${BIBLE_PATH}/` },
		{ name: 'Open Word Bible', href: path }
	]);
	// The translation as a CreativeWork in its own right, with its home and its
	// licence; the books here are its parts.
	const workLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'CreativeWork',
			name: 'Open Word Bible',
			alternateName: 'OWB',
			url: OWB_URL,
			sameAs: OWB_URL,
			license: 'https://creativecommons.org/publicdomain/zero/1.0/',
			inLanguage: lang,
			description,
			mainEntityOfPage: canonical,
			hasPart: books.map((b) => ({
				'@type': 'Book',
				name: b.title,
				url: absUrl(localizeHref(`/books/${b.slug}`))
			}))
		})
	);
</script>

<Seo
	{title}
	{description}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og/bible.png`}
	structuredData={[crumbsLd, workLd]}
/>

<div class="page-col px-5 py-10">
	<!-- Hero: the name, what it is in a sentence, the two ways in. -->
	<section class="hero">
		<div>
			<p class="eyebrow text-gold-ink">{say(COPY.eyebrow)}</p>
			<h1 class="mt-2 text-balance font-display text-h1 font-semibold leading-tight">
				{say(COPY.heading)}
			</h1>
			<p class="lede mt-4 text-muted">{say(COPY.lede)}</p>
			<p class="facts mt-5 text-small text-muted">
				{#if books.length}
					<span
						>{i18n.count(books.length, 'common.bookOne', 'common.bookMany')}
						{say(COPY.onOchorus)}</span
					>
					<span class="sep" aria-hidden="true">·</span>
				{/if}
				<span>{say(COPY.languages)}</span>
				<span class="sep" aria-hidden="true">·</span>
				<span>{say(COPY.publicDomain)}</span>
			</p>
			<div class="mt-6 flex flex-wrap gap-3">
				<a class="btn btn-primary" href={localizeHref(`${BIBLE_PATH}/`)}>{say(COPY.readBible)} <Arrow /></a>
				<a class="btn btn-ghost" href={OWB_URL} rel="external noopener">
					{say(COPY.visit)} <span aria-hidden="true">↗</span>
				</a>
			</div>
		</div>
		{#if fan.length >= 3}
			<div class="fan">
				<CoverStrip covers={fan.map(toBookTile)} size="fan" priority />
			</div>
		{/if}
	</section>

	<!-- Three levels: one verse, side by side, the Ochorus one marked. -->
	<section class="mt-12" aria-labelledby="levels-heading">
		<p class="eyebrow text-gold-ink">{say(COPY.levelsEyebrow)}</p>
		<h2 id="levels-heading" class="mt-1 text-h2 font-display font-semibold">
			{say(COPY.levelsHeading)}
		</h2>
		<p class="mt-2 max-w-prose text-small text-muted">{say(COPY.levelsLede)}</p>
		<ol class="levels mt-6">
			{#each OWB_LEVELS as level (level.code)}
				{@const ours = level.code === 'OWB-B'}
				{@const sample = samples[level.code]}
				<li class="level" class:ours>
					<div class="flex items-baseline justify-between gap-3">
						<h3 class="font-display text-h3 font-semibold">{say(level.name)}</h3>
						<span class="code">{level.code}</span>
					</div>
					{#if sample}
						<blockquote class="verse mt-3 font-display">{sample}</blockquote>
					{/if}
					<p class="mt-3 text-small text-muted">{say(level.aim)}</p>
					{#if ours}
						<p class="badge mt-3">{say(COPY.ours)}</p>
					{/if}
				</li>
			{/each}
		</ol>
	</section>

	<!-- The reasoning record: one real decision, as the translation keeps it. -->
	<section class="working mt-14" aria-labelledby="working-heading">
		<div>
			<p class="eyebrow text-gold-ink">{say(COPY.workingEyebrow)}</p>
			<h2 id="working-heading" class="mt-1 text-h2 font-display font-semibold">
				{say(COPY.workingHeading)}
			</h2>
			<p class="mt-3 text-small text-muted">{say(COPY.working1)}</p>
			<p class="mt-3 text-small text-muted">{say(COPY.working2)}</p>
			<a class="mt-4 inline-block text-small font-semibold text-accent" href={OWB_READ_URL} rel="external noopener">
				{say(COPY.readReasoning)} <span aria-hidden="true">↗</span>
			</a>
		</div>
		<figure class="record">
			<figcaption class="eyebrow text-muted">{say(COPY.recordCaption)}</figcaption>
			<p class="mt-3">
				<span class="greek" lang="grc">Οὕτως</span>
				<span class="text-small text-muted">houtōs</span>
			</p>
			<dl class="mt-3 text-small">
				<div>
					<dt>{say(COPY.chosen)}</dt>
					<dd>{say(COPY.chosenText)}</dd>
				</div>
				<div>
					<dt>{say(COPY.setAside)}</dt>
					<dd>{say(COPY.setAsideText)}</dd>
				</div>
				<div>
					<dt>{say(COPY.why)}</dt>
					<dd>{say(COPY.whyText)}</dd>
				</div>
			</dl>
		</figure>
	</section>

	<!-- Sources and freedom, as two quiet panels. -->
	<section class="facts-grid mt-14">
		<div class="panel">
			<p class="eyebrow text-gold-ink">{say(COPY.sourcesEyebrow)}</p>
			<h2 class="mt-1 text-h3 font-display font-semibold">{say(COPY.sourcesHeading)}</h2>
			<ul class="mt-3 space-y-2 text-small text-muted">
				<li>
					<strong class="text-text">{t('bible.oldTestament')}:</strong>
					{say(COPY.oldSource)}
				</li>
				<li>
					<strong class="text-text">{t('bible.newTestament')}:</strong>
					{say(COPY.newSource)}
				</li>
				<li>{say(COPY.noTyping)}</li>
			</ul>
		</div>
		<div class="panel">
			<p class="eyebrow text-gold-ink">{say(COPY.freeEyebrow)}</p>
			<h2 class="mt-1 text-h3 font-display font-semibold">{say(COPY.freeHeading)}</h2>
			<p class="mt-3 text-small text-muted">{say(COPY.freeText)}</p>
			<p class="mt-4 text-small text-muted">{say(COPY.follow)}</p>
			<ul class="mt-2 flex flex-wrap gap-2" aria-label={say(COPY.languagesLabel)}>
				{#each OWB_LANGUAGES.slice(1) as l (l.en)}
					<li class="tag">{say(l)}</li>
				{/each}
			</ul>
		</div>
	</section>

	<!-- What Ochorus adds around the text, each a door into the library. -->
	<section class="mt-14" aria-labelledby="here-heading">
		<p class="eyebrow text-gold-ink">{say(COPY.hereEyebrow)}</p>
		<h2 id="here-heading" class="mt-1 text-h2 font-display font-semibold">
			{say(COPY.hereHeading)}
		</h2>
		<ul class="here mt-6">
			<li>
				<a class="here-card card-lift" href={localizeHref(`${BIBLE_PATH}/`)}>
					<span class="font-display text-body font-semibold text-text">{say(COPY.everyBook)}</span>
					<span class="mt-1 block text-small text-muted">{say(COPY.everyBookText)}</span>
					<span class="mt-2 block text-small font-semibold text-accent">{t('nav.bible')} <Arrow /></span>
				</a>
			</li>
			<li>
				<a class="here-card card-lift" href={localizeHref(`/series/${BIBLE_SERIES}/`)}>
					<span class="font-display text-body font-semibold text-text">{say(COPY.through)}</span>
					<span class="mt-1 block text-small text-muted">{say(COPY.throughText)}</span>
					<span class="mt-2 block text-small font-semibold text-accent">{t('bible.inOrder')} <Arrow /></span>
				</a>
			</li>
			<li>
				<a class="here-card card-lift" href={localizeHref('/plans/')}>
					<span class="font-display text-body font-semibold text-text">{say(COPY.daily)}</span>
					<span class="mt-1 block text-small text-muted">{say(COPY.dailyText)}</span>
					<span class="mt-2 block text-small font-semibold text-accent">{say(COPY.plansLink)} <Arrow /></span>
				</a>
			</li>
			<li>
				<div class="here-card">
					<span class="font-display text-body font-semibold text-text">{say(COPY.intro)}</span>
					<span class="mt-1 block text-small text-muted">{say(COPY.introText)}</span>
				</div>
			</li>
		</ul>
	</section>

	<!-- The way out: everything else lives at the translation's home. -->
	<section class="cta mt-16">
		<div>
			<h2 class="text-h2 font-display font-semibold">{say(COPY.whole)}</h2>
			<p class="mt-2 text-small text-muted">{say(COPY.wholeText)}</p>
		</div>
		<a class="btn btn-primary" href={OWB_URL} rel="external noopener">
			OpenWordBible.org <span aria-hidden="true">↗</span>
		</a>
	</section>
</div>

<style>
	.hero {
		display: grid;
		grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
		gap: 2.5rem;
		align-items: center;
		padding-block: 1rem 2.5rem;
	}
	.lede {
		max-width: 56ch;
		font-size: var(--fs-body);
		line-height: 1.65;
	}
	.facts {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 0.6rem;
	}
	.levels {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 1rem;
	}
	.level {
		display: flex;
		flex-direction: column;
		padding: 1.25rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.level.ours {
		border-color: var(--accent);
		box-shadow: 0 0 0 1px var(--accent);
	}
	.code {
		font-size: var(--fs-eyebrow);
		letter-spacing: 0.06em;
		color: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	.verse {
		flex: 1;
		font-size: var(--fs-body);
		line-height: 1.6;
		color: var(--text);
	}
	.badge {
		align-self: flex-start;
		padding: 0.15rem 0.6rem;
		border-radius: var(--radius-pill);
		font-size: var(--fs-eyebrow);
		font-weight: 600;
		color: var(--accent);
		background: var(--surface-2);
	}
	.working {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: 2.5rem;
		align-items: start;
	}
	.working p {
		max-width: 56ch;
	}
	.record {
		padding: 1.5rem;
		border: 1px solid var(--border);
		border-inline-start: 3px solid var(--gold);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.greek {
		font-family: var(--font-display);
		font-size: var(--fs-h2);
		font-weight: 600;
		margin-inline-end: 0.5rem;
	}
	.record dl > div {
		display: grid;
		grid-template-columns: 5.5rem minmax(0, 1fr);
		gap: 0.75rem;
		padding-block: 0.6rem;
		border-top: 1px solid var(--border);
	}
	.record dt {
		font-weight: 600;
		color: var(--muted);
	}
	.record dd {
		color: var(--text);
	}
	.facts-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 1rem;
	}
	.panel {
		padding: 1.5rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.here {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 0.875rem;
	}
	.here-card {
		display: block;
		height: 100%;
		padding: 1.1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.cta {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 1.25rem;
		padding: 1.75rem;
		border-radius: var(--radius-card);
		background: var(--surface-2);
	}
	.cta p {
		max-width: 56ch;
	}
	@media (max-width: 900px) {
		.levels,
		.working,
		.facts-grid {
			grid-template-columns: minmax(0, 1fr);
		}
		.here {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (max-width: 639.98px) {
		.hero {
			grid-template-columns: minmax(0, 1fr);
			gap: 0.5rem;
			padding-block: 0 1.5rem;
		}
		.fan {
			order: -1;
			margin-bottom: 0.75rem;
		}
		.here {
			grid-template-columns: minmax(0, 1fr);
		}
		.cta {
			padding: 1.25rem;
		}
	}
</style>
