/**
 * "The Story of the Bible" (/bible/story/): the whole Bible walked in story
 * order, creation to new creation, one short section per era, each linking the
 * Bible books that tell it and a key chapter or two.
 *
 * The prose is in each hub locale (`BibleText`, like `BIBLE_STARTS` in
 * $lib/bible): the page exists only where the Bible does (BIBLE_LOCALES), and
 * it is imported by that route alone, so it loads with the page instead of
 * riding in every locale's catalogue. Its headings and link labels are chrome
 * and go through the catalogue.
 *
 * It quotes no Scripture on purpose: a quotation here would have to be the
 * Open Word Bible's own wording (CLAUDE.md, "Sourcing"), and the links carry
 * the reader to the text itself.
 *
 * The key chapters are given in the Bible's own numbers; `storyKeys` turns
 * them into reader chapters (`bibleChapterOrder`: each book opens on an
 * introduction). Most are the 60-day plan's own (`the-story-of-the-bible` in
 * `library/plan_seed.py`), so the page and the plan read the same story.
 */

import { bibleChapterOrder, bibleText, type BibleText } from '$lib/bible';
import { canonName, chapterLabel } from '$lib/bibleNames';
import { bookChapterPath } from '$lib/reading-schema';

export { BIBLE_STORY_PATH } from '$lib/bible';

/** The 60-day reading plan that reads the same story, a chapter a day. */
export const STORY_PLAN_SLUG = 'the-story-of-the-bible';
/** The house book that tells the whole story for teens (an Ochorus Original;
 *  the page shows the title the API serves in the reader's language). */
export const STORY_BOOK = { slug: 'the-big-story', title: 'The Big Story' } as const;

/** The page's one-sentence description: its tagline and its meta description. */
export const STORY_TAGLINE: BibleText = {
	en: 'The whole Bible as one story, from creation to new creation, and the books that tell each part of it.',
	es: 'Toda la Biblia como una sola historia, de la creación a la nueva creación, y los libros que cuentan cada parte.',
	fr: 'Toute la Bible comme une seule histoire, de la création à la création nouvelle, et les livres qui en racontent chaque partie.',
	pt: 'A Bíblia inteira como uma só história, da criação à nova criação, e os livros que contam cada parte dela.'
};

/**
 * The `the-bible` series' book slugs in canonical order: index + 1 is the
 * book's `series_position` (1 Genesis … 66 Revelation), the numbering `CANON`
 * and `chapterLabel` use. Checked against the committed fixtures by the test.
 */
export const BIBLE_SLUGS: readonly string[] = [
	'genesis', 'exodus', 'leviticus', 'numbers', 'deuteronomy',
	'joshua', 'judges', 'ruth', '1-samuel', '2-samuel', '1-kings', '2-kings',
	'1-chronicles', '2-chronicles', 'ezra', 'nehemiah', 'esther',
	'job', 'psalms', 'proverbs', 'ecclesiastes', 'song-of-songs',
	'isaiah', 'jeremiah', 'lamentations', 'ezekiel', 'daniel',
	'hosea', 'joel', 'amos', 'obadiah', 'jonah', 'micah', 'nahum', 'habakkuk',
	'zephaniah', 'haggai', 'zechariah', 'malachi',
	'gospel-of-matthew', 'gospel-of-mark', 'gospel-of-luke', 'gospel-of-john',
	'acts-of-the-apostles',
	'romans', '1-corinthians', '2-corinthians', 'galatians', 'ephesians', 'philippians',
	'colossians', '1-thessalonians', '2-thessalonians', '1-timothy', '2-timothy', 'titus',
	'philemon',
	'hebrews', 'james', '1-peter', '2-peter', '1-john', '2-john', '3-john', 'jude',
	'revelation'
];

/** A book's place in the canon (1–66), or null if it is not a Bible book. */
export const canonPosition = (slug: string): number | null => {
	const i = BIBLE_SLUGS.indexOf(slug);
	return i === -1 ? null : i + 1;
};

/** A key chapter: a book and the Bible's own chapter number in it. */
export interface StoryKey {
	slug: string;
	chapter: number;
}

export interface StorySection {
	id: string;
	/** The era's heading. */
	title: BibleText;
	/** Where the Bible tells it ("Genesis 12–50"), or how long it lasts. */
	period: BibleText;
	/** Two or three sentences: plain, accurate, no quotation. */
	prose: BibleText;
	/** The books that tell it, slugs in canonical order. */
	books: readonly string[];
	/** One or two key chapters. */
	keys: readonly StoryKey[];
	testament: 'old' | 'new';
	/**
	 * A bridge between the testaments, told in a line, with no book of its
	 * own (the silent years). Drawn as a pause on the timeline, not an era.
	 */
	interlude?: boolean;
}

export const BIBLE_STORY: readonly StorySection[] = [
	{
		id: 'creation',
		title: { en: 'Creation', es: 'La creación', fr: 'La création', pt: 'A criação' },
		period: { en: 'Genesis 1–2', es: 'Génesis 1–2', fr: 'Genèse 1–2', pt: 'Gênesis 1–2' },
		prose: {
			en: 'The Bible opens with God and nothing else. He makes the world by his word, calls it good, and makes man and woman in his own image to care for it. They live in a garden with God, in a world as it was meant to be.',
			es: 'La Biblia comienza con Dios y nada más. Él hace el mundo por su palabra, lo llama bueno, y hace al hombre y a la mujer a su propia imagen para que lo cuiden. Viven en un jardín con Dios, en un mundo tal como debía ser.',
			fr: 'La Bible s’ouvre sur Dieu, et rien d’autre. Il fait le monde par sa parole, le déclare bon, et fait l’homme et la femme à sa propre image pour qu’ils en prennent soin. Ils vivent dans un jardin avec Dieu, dans un monde tel qu’il devait être.',
			pt: 'A Bíblia começa com Deus e nada mais. Ele faz o mundo pela sua palavra, o declara bom e faz o homem e a mulher à sua própria imagem para cuidarem dele. Eles vivem num jardim com Deus, num mundo como ele devia ser.'
		},
		books: ['genesis'],
		keys: [
			{ slug: 'genesis', chapter: 1 },
			{ slug: 'genesis', chapter: 2 }
		],
		testament: 'old'
	},
	{
		id: 'fall',
		title: { en: 'The fall', es: 'La caída', fr: 'La chute', pt: 'A queda' },
		period: { en: 'Genesis 3–11', es: 'Génesis 3–11', fr: 'Genèse 3–11', pt: 'Gênesis 3–11' },
		prose: {
			en: 'Adam and Eve choose their own way over God’s, and everything changes: shame, pain and death come into the world, and they are sent out of the garden. Even then God speaks a promise of rescue. The chapters that follow show how far the damage spreads, through Cain, the flood and the tower of Babel.',
			es: 'Adán y Eva eligen su propio camino en lugar del de Dios, y todo cambia: la vergüenza, el dolor y la muerte entran en el mundo, y son expulsados del jardín. Aun entonces Dios pronuncia una promesa de rescate. Los capítulos siguientes muestran hasta dónde se extiende el daño, con Caín, el diluvio y la torre de Babel.',
			fr: 'Adam et Ève choisissent leur propre chemin plutôt que celui de Dieu, et tout change : la honte, la souffrance et la mort entrent dans le monde, et ils sont chassés du jardin. Même alors, Dieu prononce une promesse de délivrance. Les chapitres suivants montrent jusqu’où le mal se répand, avec Caïn, le déluge et la tour de Babel.',
			pt: 'Adão e Eva escolhem o próprio caminho em vez do caminho de Deus, e tudo muda: a vergonha, a dor e a morte entram no mundo, e eles são expulsos do jardim. Mesmo então Deus pronuncia uma promessa de resgate. Os capítulos seguintes mostram até onde o dano se espalha, com Caim, o dilúvio e a torre de Babel.'
		},
		books: ['genesis'],
		keys: [
			{ slug: 'genesis', chapter: 3 },
			{ slug: 'genesis', chapter: 11 }
		],
		testament: 'old'
	},
	{
		id: 'patriarchs',
		title: { en: 'Abraham and his family', es: 'Abraham y su familia', fr: 'Abraham et sa famille', pt: 'Abraão e sua família' },
		period: { en: 'Genesis 12–50', es: 'Génesis 12–50', fr: 'Genèse 12–50', pt: 'Gênesis 12–50' },
		prose: {
			en: 'God calls Abraham to leave his home and promises to make of him a great nation, through which all the families of the earth will be blessed. The promise passes, through many failures, to Isaac, Jacob and Jacob’s twelve sons. Genesis ends with the family in Egypt, where Joseph, sold as a slave by his brothers, has risen to save them from famine.',
			es: 'Dios llama a Abraham a dejar su tierra y le promete hacer de él una gran nación, por medio de la cual serán bendecidas todas las familias de la tierra. La promesa pasa, a través de muchos fracasos, a Isaac, a Jacob y a los doce hijos de Jacob. Génesis termina con la familia en Egipto, donde José, a quien sus hermanos vendieron como esclavo, ha llegado a lo más alto para salvarlos del hambre.',
			fr: 'Dieu appelle Abraham à quitter son pays et promet de faire de lui une grande nation, par laquelle toutes les familles de la terre seront bénies. La promesse passe, à travers bien des échecs, à Isaac, à Jacob et aux douze fils de Jacob. La Genèse se termine avec la famille en Égypte, où Joseph, vendu comme esclave par ses frères, s’est élevé assez haut pour les sauver de la famine.',
			pt: 'Deus chama Abraão a deixar a sua terra e promete fazer dele uma grande nação, por meio da qual todas as famílias da terra serão abençoadas. A promessa passa, através de muitos fracassos, a Isaque, a Jacó e aos doze filhos de Jacó. Gênesis termina com a família no Egito, onde José, vendido como escravo pelos irmãos, chegou ao topo para salvá-los da fome.'
		},
		books: ['genesis'],
		keys: [
			{ slug: 'genesis', chapter: 12 },
			{ slug: 'genesis', chapter: 50 }
		],
		testament: 'old'
	},
	{
		id: 'exodus',
		title: { en: 'Out of Egypt', es: 'La salida de Egipto', fr: 'La sortie d’Égypte', pt: 'A saída do Egito' },
		period: { en: 'Exodus 1–18', es: 'Éxodo 1–18', fr: 'Exode 1–18', pt: 'Êxodo 1–18' },
		prose: {
			en: 'Generations later Jacob’s descendants, the Israelites, are slaves in Egypt. God hears their cry and sends Moses to bring them out. At the Passover and the crossing of the sea he rescues his people, and the exodus becomes the great picture of salvation for the rest of the Bible.',
			es: 'Generaciones después, los descendientes de Jacob, los israelitas, son esclavos en Egipto. Dios oye su clamor y envía a Moisés a sacarlos. En la Pascua y en el cruce del mar rescata a su pueblo, y el éxodo se convierte en la gran imagen de la salvación para el resto de la Biblia.',
			fr: 'Des générations plus tard, les descendants de Jacob, les Israélites, sont esclaves en Égypte. Dieu entend leur cri et envoie Moïse les faire sortir. À la Pâque et au passage de la mer, il délivre son peuple, et l’exode devient la grande image du salut pour le reste de la Bible.',
			pt: 'Gerações depois, os descendentes de Jacó, os israelitas, são escravos no Egito. Deus ouve o seu clamor e envia Moisés para tirá-los de lá. Na Páscoa e na travessia do mar, ele resgata o seu povo, e o êxodo se torna a grande imagem da salvação para o resto da Bíblia.'
		},
		books: ['exodus'],
		keys: [
			{ slug: 'exodus', chapter: 3 },
			{ slug: 'exodus', chapter: 14 }
		],
		testament: 'old'
	},
	{
		id: 'law',
		title: { en: 'The law and the wilderness', es: 'La ley y el desierto', fr: 'La loi et le désert', pt: 'A lei e o deserto' },
		period: { en: 'Exodus 19 – Deuteronomy', es: 'Éxodo 19 – Deuteronomio', fr: 'Exode 19 – Deutéronome', pt: 'Êxodo 19 – Deuteronômio' },
		prose: {
			en: 'At Mount Sinai God makes a covenant with Israel, gives them his law, and comes to live among them in the tabernacle, with sacrifices to deal with their sin. When they refuse to enter the promised land, they wander forty years in the wilderness. On its border Moses sets the law before a new generation and urges them to love God with all their heart.',
			es: 'En el monte Sinaí Dios hace un pacto con Israel, le da su ley y viene a vivir en medio de ellos en el tabernáculo, con sacrificios para tratar su pecado. Cuando se niegan a entrar en la tierra prometida, andan errantes cuarenta años por el desierto. En su frontera, Moisés pone la ley delante de una nueva generación y la exhorta a amar a Dios con todo el corazón.',
			fr: 'Au mont Sinaï, Dieu conclut une alliance avec Israël, lui donne sa loi et vient habiter au milieu de son peuple dans le tabernacle, avec des sacrifices pour traiter son péché. Quand ils refusent d’entrer dans le pays promis, ils errent quarante ans dans le désert. À sa frontière, Moïse place la loi devant une nouvelle génération et l’exhorte à aimer Dieu de tout son cœur.',
			pt: 'No monte Sinai, Deus faz uma aliança com Israel, lhe dá a sua lei e vem habitar no meio do povo no tabernáculo, com sacrifícios para tratar o seu pecado. Quando eles se recusam a entrar na terra prometida, vagam quarenta anos pelo deserto. Na fronteira, Moisés põe a lei diante de uma nova geração e a exorta a amar a Deus de todo o coração.'
		},
		books: ['exodus', 'leviticus', 'numbers', 'deuteronomy'],
		keys: [
			{ slug: 'exodus', chapter: 20 },
			{ slug: 'deuteronomy', chapter: 6 }
		],
		testament: 'old'
	},
	{
		id: 'conquest',
		title: { en: 'The land and the judges', es: 'La tierra y los jueces', fr: 'Le pays et les juges', pt: 'A terra e os juízes' },
		period: { en: 'Joshua – Ruth', es: 'Josué – Rut', fr: 'Josué – Ruth', pt: 'Josué – Rute' },
		prose: {
			en: 'Under Joshua, Israel crosses the Jordan and settles in the land God promised. Then comes a long, repeating cycle: the people turn away, trouble comes, they cry out, and God raises up a judge to deliver them. In the middle of those dark days the book of Ruth tells a quiet story of faithfulness, and of a family line that leads to King David.',
			es: 'Con Josué al frente, Israel cruza el Jordán y se establece en la tierra que Dios prometió. Luego viene un largo ciclo que se repite: el pueblo se aparta, llega la angustia, claman, y Dios levanta a un juez para librarlos. En medio de esos días oscuros, el libro de Rut cuenta una historia sencilla de fidelidad, y de un linaje que conduce al rey David.',
			fr: 'Sous la conduite de Josué, Israël traverse le Jourdain et s’installe dans le pays que Dieu a promis. Vient alors un long cycle qui se répète : le peuple se détourne, le malheur arrive, il crie à Dieu, et Dieu suscite un juge pour le délivrer. Au milieu de ces jours sombres, le livre de Ruth raconte une histoire simple de fidélité, et d’une lignée qui mène au roi David.',
			pt: 'Sob a liderança de Josué, Israel atravessa o Jordão e se estabelece na terra que Deus prometeu. Então vem um longo ciclo que se repete: o povo se afasta, a angústia chega, eles clamam, e Deus levanta um juiz para livrá-los. No meio desses dias sombrios, o livro de Rute conta uma história simples de fidelidade, e de uma linhagem que leva ao rei Davi.'
		},
		books: ['joshua', 'judges', 'ruth'],
		keys: [
			{ slug: 'joshua', chapter: 1 },
			{ slug: 'judges', chapter: 2 }
		],
		testament: 'old'
	},
	{
		id: 'kings',
		title: { en: 'The kings', es: 'Los reyes', fr: 'Les rois', pt: 'Os reis' },
		period: { en: '1 Samuel – 2 Chronicles', es: '1 Samuel – 2 Crónicas', fr: '1 Samuel – 2 Chroniques', pt: '1 Samuel – 2 Crônicas' },
		prose: {
			en: 'Israel asks for a king. After Saul comes David, the shepherd boy, to whom God promises a son whose kingdom will never end; Solomon, his son, builds the temple in Jerusalem, but after him the kingdom splits in two, Israel in the north and Judah in the south, and most of their kings lead the people away from God. Beside the story stand Israel’s books of song and wisdom: the Psalms, many of them David’s; Proverbs, Ecclesiastes and the Song of Songs, linked with Solomon; and Job.',
			es: 'Israel pide un rey. Después de Saúl viene David, el joven pastor, a quien Dios promete un hijo cuyo reino no tendrá fin; Salomón, su hijo, construye el templo en Jerusalén, pero después de él el reino se divide en dos, Israel en el norte y Judá en el sur, y la mayoría de sus reyes apartan al pueblo de Dios. Junto a la historia están los libros de cantos y de sabiduría de Israel: los Salmos, muchos de ellos de David; Proverbios, Eclesiastés y el Cantar de los Cantares, vinculados con Salomón; y Job.',
			fr: 'Israël demande un roi. Après Saül vient David, le jeune berger, à qui Dieu promet un fils dont le règne n’aura pas de fin ; Salomon, son fils, bâtit le temple à Jérusalem, mais après lui le royaume se divise en deux, Israël au nord et Juda au sud, et la plupart de leurs rois détournent le peuple de Dieu. À côté de l’histoire se tiennent les livres de chants et de sagesse d’Israël : les Psaumes, dont beaucoup sont de David ; les Proverbes, l’Ecclésiaste et le Cantique des cantiques, liés à Salomon ; et Job.',
			pt: 'Israel pede um rei. Depois de Saul vem Davi, o jovem pastor, a quem Deus promete um filho cujo reino não terá fim; Salomão, seu filho, constrói o templo em Jerusalém, mas depois dele o reino se divide em dois, Israel ao norte e Judá ao sul, e a maioria dos seus reis afasta o povo de Deus. Ao lado da história estão os livros de cânticos e de sabedoria de Israel: os Salmos, muitos deles de Davi; Provérbios, Eclesiastes e o Cântico dos Cânticos, ligados a Salomão; e Jó.'
		},
		books: [
			'1-samuel',
			'2-samuel',
			'1-kings',
			'2-kings',
			'1-chronicles',
			'2-chronicles',
			'job',
			'psalms',
			'proverbs',
			'ecclesiastes',
			'song-of-songs'
		],
		keys: [
			{ slug: '2-samuel', chapter: 7 },
			{ slug: '1-kings', chapter: 12 }
		],
		testament: 'old'
	},
	{
		id: 'prophets',
		title: { en: 'The prophets', es: 'Los profetas', fr: 'Les prophètes', pt: 'Os profetas' },
		period: { en: 'Isaiah – Zephaniah', es: 'Isaías – Sofonías', fr: 'Ésaïe – Sophonie', pt: 'Isaías – Sofonias' },
		prose: {
			en: 'Through the years of the kings, God sends prophets to call his people back to him, away from idols and injustice, before judgement falls. Most of their warnings go unheeded. Yet their books are full of hope as well: of a King to come from David’s line, and of a servant who will suffer for the sins of many.',
			es: 'Durante los años de los reyes, Dios envía profetas para llamar a su pueblo a volver a él, lejos de los ídolos y la injusticia, antes de que caiga el juicio. La mayoría de sus advertencias no son escuchadas. Sin embargo, sus libros también están llenos de esperanza: la de un Rey que vendrá del linaje de David, y la de un siervo que sufrirá por los pecados de muchos.',
			fr: 'Pendant les années des rois, Dieu envoie des prophètes pour ramener son peuple à lui, loin des idoles et de l’injustice, avant que le jugement ne tombe. La plupart de leurs avertissements restent sans écho. Pourtant, leurs livres sont aussi remplis d’espérance : celle d’un Roi à venir de la lignée de David, et celle d’un serviteur qui souffrira pour les péchés de beaucoup.',
			pt: 'Durante os anos dos reis, Deus envia profetas para chamar o seu povo de volta para ele, longe dos ídolos e da injustiça, antes que o juízo caia. A maioria das suas advertências não é ouvida. Mesmo assim, os seus livros também estão cheios de esperança: a de um Rei que virá da linhagem de Davi, e a de um servo que sofrerá pelos pecados de muitos.'
		},
		books: [
			'isaiah',
			'hosea',
			'joel',
			'amos',
			'jonah',
			'micah',
			'nahum',
			'habakkuk',
			'zephaniah'
		],
		keys: [
			{ slug: 'isaiah', chapter: 53 },
			{ slug: 'hosea', chapter: 11 }
		],
		testament: 'old'
	},
	{
		id: 'exile',
		title: { en: 'Exile', es: 'El exilio', fr: 'L’exil', pt: 'O exílio' },
		period: { en: '2 Kings 17–25 · Jeremiah – Daniel', es: '2 Reyes 17–25 · Jeremías – Daniel', fr: '2 Rois 17–25 · Jérémie – Daniel', pt: '2 Reis 17–25 · Jeremias – Daniel' },
		prose: {
			en: 'Assyria takes the northern kingdom, and later Babylon destroys Jerusalem and its temple and carries Judah away. Lamentations mourns the city; in Babylon, Ezekiel and Daniel speak of a God who has not abandoned his people. Jeremiah, who saw the end coming, also speaks of a new covenant, written on the heart.',
			es: 'Asiria conquista el reino del norte, y más tarde Babilonia destruye Jerusalén y su templo y se lleva cautivo a Judá. Lamentaciones llora por la ciudad; en Babilonia, Ezequiel y Daniel hablan de un Dios que no ha abandonado a su pueblo. Jeremías, que vio venir el fin, habla también de un nuevo pacto, escrito en el corazón.',
			fr: 'L’Assyrie s’empare du royaume du nord, puis Babylone détruit Jérusalem et son temple et emmène Juda en captivité. Les Lamentations pleurent la ville ; à Babylone, Ézéchiel et Daniel parlent d’un Dieu qui n’a pas abandonné son peuple. Jérémie, qui avait vu venir la fin, parle aussi d’une alliance nouvelle, écrite sur le cœur.',
			pt: 'A Assíria conquista o reino do norte, e mais tarde a Babilônia destrói Jerusalém e o seu templo e leva Judá para o cativeiro. Lamentações chora pela cidade; na Babilônia, Ezequiel e Daniel falam de um Deus que não abandonou o seu povo. Jeremias, que viu o fim chegar, fala também de uma nova aliança, escrita no coração.'
		},
		books: ['2-kings', 'jeremiah', 'lamentations', 'ezekiel', 'daniel', 'obadiah'],
		keys: [
			{ slug: '2-kings', chapter: 25 },
			{ slug: 'ezekiel', chapter: 37 }
		],
		testament: 'old'
	},
	{
		id: 'return',
		title: { en: 'The return', es: 'El regreso', fr: 'Le retour', pt: 'O retorno' },
		period: { en: 'Ezra – Esther · Haggai – Malachi', es: 'Esdras – Ester · Hageo – Malaquías', fr: 'Esdras – Esther · Aggée – Malachie', pt: 'Esdras – Ester · Ageu – Malaquias' },
		prose: {
			en: 'When Persia conquers Babylon, the exiles are allowed to go home. They rebuild the temple and, under Nehemiah, the walls of Jerusalem, and Ezra reads them the law again; the book of Esther shows God keeping his people who stayed in Persia. The last prophets urge them on, and the Old Testament closes still waiting for the promised King.',
			es: 'Cuando Persia conquista Babilonia, a los exiliados se les permite volver a casa. Reconstruyen el templo y, con Nehemías, los muros de Jerusalén, y Esdras vuelve a leerles la ley; el libro de Ester muestra a Dios guardando a los de su pueblo que se quedaron en Persia. Los últimos profetas los animan, y el Antiguo Testamento se cierra esperando todavía al Rey prometido.',
			fr: 'Quand la Perse conquiert Babylone, les exilés sont autorisés à rentrer chez eux. Ils rebâtissent le temple et, avec Néhémie, les murailles de Jérusalem, et Esdras leur lit de nouveau la loi ; le livre d’Esther montre Dieu gardant ceux de son peuple restés en Perse. Les derniers prophètes les encouragent, et l’Ancien Testament se referme encore dans l’attente du Roi promis.',
			pt: 'Quando a Pérsia conquista a Babilônia, os exilados recebem permissão para voltar para casa. Eles reconstroem o templo e, com Neemias, os muros de Jerusalém, e Esdras volta a ler a lei para eles; o livro de Ester mostra Deus guardando os do seu povo que ficaram na Pérsia. Os últimos profetas os encorajam, e o Antigo Testamento se encerra ainda à espera do Rei prometido.'
		},
		books: ['ezra', 'nehemiah', 'esther', 'haggai', 'zechariah', 'malachi'],
		keys: [
			{ slug: 'ezra', chapter: 1 },
			{ slug: 'nehemiah', chapter: 8 }
		],
		testament: 'old'
	},
	{
		id: 'silent-years',
		title: { en: 'The silent years', es: 'Los años de silencio', fr: 'Les années de silence', pt: 'Os anos de silêncio' },
		period: { en: 'About four hundred years', es: 'Unos cuatrocientos años', fr: 'Environ quatre cents ans', pt: 'Cerca de quatrocentos anos' },
		prose: {
			en: 'Between Malachi and the coming of Jesus lie some four hundred years the Old Testament does not tell: empires rise and fall, and Israel waits.',
			es: 'Entre Malaquías y la venida de Jesús pasan unos cuatrocientos años que el Antiguo Testamento no cuenta: los imperios se levantan y caen, e Israel espera.',
			fr: 'Entre Malachie et la venue de Jésus s’étendent quelque quatre cents ans que l’Ancien Testament ne raconte pas : des empires s’élèvent et tombent, et Israël attend.',
			pt: 'Entre Malaquias e a vinda de Jesus passam cerca de quatrocentos anos que o Antigo Testamento não conta: impérios se levantam e caem, e Israel espera.'
		},
		books: [],
		keys: [],
		testament: 'old',
		interlude: true
	},
	{
		id: 'jesus',
		title: { en: 'Jesus', es: 'Jesús', fr: 'Jésus', pt: 'Jesus' },
		period: { en: 'The Gospels', es: 'Los Evangelios', fr: 'Les Évangiles', pt: 'Os Evangelhos' },
		prose: {
			en: 'In Bethlehem, Jesus is born to Mary, the long-promised son of David and the Son of God. He announces that the kingdom of God has come near, teaches, heals the sick, forgives sinners and calls twelve disciples to follow him. Four Gospels tell his life, each in its own way.',
			es: 'En Belén nace Jesús, hijo de María, el hijo de David tanto tiempo prometido y el Hijo de Dios. Anuncia que el reino de Dios se ha acercado, enseña, sana a los enfermos, perdona a los pecadores y llama a doce discípulos a seguirlo. Cuatro Evangelios cuentan su vida, cada uno a su manera.',
			fr: 'À Bethléem, Jésus naît de Marie, le fils de David promis depuis si longtemps et le Fils de Dieu. Il annonce que le royaume de Dieu s’est approché, il enseigne, guérit les malades, pardonne aux pécheurs et appelle douze disciples à le suivre. Quatre Évangiles racontent sa vie, chacun à sa manière.',
			pt: 'Em Belém nasce Jesus, filho de Maria, o filho de Davi prometido havia tanto tempo e o Filho de Deus. Ele anuncia que o reino de Deus se aproximou, ensina, cura os doentes, perdoa os pecadores e chama doze discípulos para segui-lo. Quatro Evangelhos contam a sua vida, cada um à sua maneira.'
		},
		books: ['gospel-of-matthew', 'gospel-of-mark', 'gospel-of-luke', 'gospel-of-john'],
		keys: [
			{ slug: 'gospel-of-luke', chapter: 2 },
			{ slug: 'gospel-of-matthew', chapter: 5 }
		],
		testament: 'new'
	},
	{
		id: 'cross',
		title: { en: 'The cross and the empty tomb', es: 'La cruz y la tumba vacía', fr: 'La croix et le tombeau vide', pt: 'A cruz e o túmulo vazio' },
		period: { en: 'The Gospels', es: 'Los Evangelios', fr: 'Les Évangiles', pt: 'Os Evangelhos' },
		prose: {
			en: 'Jesus goes up to Jerusalem knowing what waits for him there. He shares a last supper with his disciples, is arrested, and is crucified, giving his life for the sins of the world. On the third day the tomb is empty: he is risen, and he appears to his friends.',
			es: 'Jesús sube a Jerusalén sabiendo lo que lo espera allí. Comparte una última cena con sus discípulos, es arrestado y crucificado, y da su vida por los pecados del mundo. Al tercer día la tumba está vacía: ha resucitado, y se aparece a sus amigos.',
			fr: 'Jésus monte à Jérusalem en sachant ce qui l’y attend. Il partage un dernier repas avec ses disciples, est arrêté et crucifié, et donne sa vie pour les péchés du monde. Le troisième jour, le tombeau est vide : il est ressuscité, et il apparaît à ses amis.',
			pt: 'Jesus sobe a Jerusalém sabendo o que o espera ali. Ele compartilha uma última ceia com os discípulos, é preso e crucificado, e dá a sua vida pelos pecados do mundo. No terceiro dia o túmulo está vazio: ele ressuscitou, e aparece aos seus amigos.'
		},
		books: ['gospel-of-matthew', 'gospel-of-mark', 'gospel-of-luke', 'gospel-of-john'],
		keys: [
			{ slug: 'gospel-of-mark', chapter: 15 },
			{ slug: 'gospel-of-john', chapter: 20 }
		],
		testament: 'new'
	},
	{
		id: 'church',
		title: { en: 'The church', es: 'La iglesia', fr: 'L’Église', pt: 'A igreja' },
		period: { en: 'Acts', es: 'Hechos', fr: 'Actes', pt: 'Atos' },
		prose: {
			en: 'Jesus returns to his Father and sends the Holy Spirit on his followers at Pentecost. From Jerusalem the good news spreads outward, carried by Peter, by Paul, once its fierce opponent, and by many others, until there are churches across the Roman world. Acts ends with Paul in Rome, still preaching.',
			es: 'Jesús vuelve a su Padre y envía el Espíritu Santo sobre sus seguidores en Pentecostés. Desde Jerusalén la buena noticia se extiende, llevada por Pedro, por Pablo, que antes fue su feroz enemigo, y por muchos otros, hasta que hay iglesias por todo el mundo romano. Hechos termina con Pablo en Roma, predicando todavía.',
			fr: 'Jésus retourne auprès de son Père et envoie le Saint-Esprit sur ses disciples à la Pentecôte. Depuis Jérusalem, la bonne nouvelle se répand, portée par Pierre, par Paul, autrefois son farouche adversaire, et par beaucoup d’autres, jusqu’à ce qu’il y ait des Églises dans tout le monde romain. Les Actes se terminent avec Paul à Rome, qui prêche encore.',
			pt: 'Jesus volta para o seu Pai e envia o Espírito Santo sobre os seus seguidores no Pentecostes. De Jerusalém a boa notícia se espalha, levada por Pedro, por Paulo, que antes foi o seu feroz opositor, e por muitos outros, até haver igrejas por todo o mundo romano. Atos termina com Paulo em Roma, ainda pregando.'
		},
		books: ['acts-of-the-apostles'],
		keys: [
			{ slug: 'acts-of-the-apostles', chapter: 2 },
			{ slug: 'acts-of-the-apostles', chapter: 9 }
		],
		testament: 'new'
	},
	{
		id: 'letters',
		title: { en: 'The letters', es: 'Las cartas', fr: 'Les lettres', pt: 'As cartas' },
		period: { en: 'Romans – Jude', es: 'Romanos – Judas', fr: 'Romains – Jude', pt: 'Romanos – Judas' },
		prose: {
			en: 'Paul and other leaders of the first Christians write to the young churches and to friends, explaining what Jesus has done and how to live in the light of it. The letters speak of grace and faith, of Jew and Gentile made one people, of love, suffering and hope. They are written to real congregations with real troubles, and they still speak to ours.',
			es: 'Pablo y otros líderes de los primeros cristianos escriben a las iglesias jóvenes y a sus amigos, explicando lo que Jesús ha hecho y cómo vivir a la luz de ello. Las cartas hablan de gracia y de fe, de judíos y gentiles hechos un solo pueblo, de amor, sufrimiento y esperanza. Fueron escritas a congregaciones reales con problemas reales, y todavía les hablan a las nuestras.',
			fr: 'Paul et d’autres responsables des premiers chrétiens écrivent aux jeunes Églises et à des amis, pour expliquer ce que Jésus a fait et comment vivre à sa lumière. Les lettres parlent de grâce et de foi, de Juifs et de non-Juifs devenus un seul peuple, d’amour, de souffrance et d’espérance. Elles ont été écrites à de vraies communautés aux prises avec de vraies difficultés, et elles parlent encore aux nôtres.',
			pt: 'Paulo e outros líderes dos primeiros cristãos escrevem às igrejas jovens e a amigos, explicando o que Jesus fez e como viver à luz disso. As cartas falam de graça e de fé, de judeus e gentios feitos um só povo, de amor, sofrimento e esperança. Foram escritas a congregações reais com problemas reais, e ainda falam às nossas.'
		},
		books: [
			'romans',
			'1-corinthians',
			'2-corinthians',
			'galatians',
			'ephesians',
			'philippians',
			'colossians',
			'1-thessalonians',
			'2-thessalonians',
			'1-timothy',
			'2-timothy',
			'titus',
			'philemon',
			'hebrews',
			'james',
			'1-peter',
			'2-peter',
			'1-john',
			'2-john',
			'3-john',
			'jude'
		],
		keys: [
			{ slug: 'romans', chapter: 8 },
			{ slug: 'ephesians', chapter: 2 }
		],
		testament: 'new'
	},
	{
		id: 'new-creation',
		title: { en: 'The new creation', es: 'La nueva creación', fr: 'La création nouvelle', pt: 'A nova criação' },
		period: { en: 'Revelation', es: 'Apocalipsis', fr: 'Apocalypse', pt: 'Apocalipse' },
		prose: {
			en: 'The Bible ends where it began, with God and his world. In visions given to John, Jesus reigns, evil is finally overthrown, and heaven and earth are made new. God lives with his people, and there is no more death, mourning or pain.',
			es: 'La Biblia termina donde comenzó, con Dios y su mundo. En visiones dadas a Juan, Jesús reina, el mal es vencido por fin, y el cielo y la tierra son hechos nuevos. Dios vive con su pueblo, y la muerte, el llanto y el dolor quedan atrás.',
			fr: 'La Bible se termine là où elle a commencé, avec Dieu et son monde. Dans des visions données à Jean, Jésus règne, le mal est enfin vaincu, et le ciel et la terre sont faits nouveaux. Dieu habite avec son peuple, et la mort, le deuil et la douleur ne sont plus.',
			pt: 'A Bíblia termina onde começou, com Deus e o seu mundo. Em visões dadas a João, Jesus reina, o mal é enfim vencido, e o céu e a terra são feitos novos. Deus vive com o seu povo, e a morte, o luto e a dor ficaram para trás.'
		},
		books: ['revelation'],
		keys: [
			{ slug: 'revelation', chapter: 21 },
			{ slug: 'revelation', chapter: 22 }
		],
		testament: 'new'
	}
];

/** A link the page draws: its label and its unlocalized href. */
export interface StoryLink {
	label: string;
	href: string;
}

/** A section's books as links to their book pages, named as the canon strip names them. */
export const storyBooks = (section: StorySection, lang: string): StoryLink[] =>
	section.books.map((slug) => ({
		label: canonName(canonPosition(slug), lang)!,
		href: `/books/${slug}`
	}));

/** A section's key chapters as links into the reader ("Psalm 23", «Romanos 8»). */
export const storyKeys = (section: StorySection, lang: string): StoryLink[] =>
	section.keys.map(({ slug, chapter }) => ({
		label: chapterLabel(canonPosition(slug), chapter, lang) ?? `${slug} ${chapter}`,
		href: bookChapterPath(slug, bibleChapterOrder(chapter), false)
	}));

/** The eras the timeline numbers (the interlude is a pause, not an era). */
export const storyEras = (sections: readonly StorySection[] = BIBLE_STORY) =>
	sections.filter((s) => !s.interlude);

/** A section's words in `lang`. */
export const storyText = (section: StorySection, lang: string) => ({
	title: bibleText(section.title, lang),
	period: bibleText(section.period, lang),
	prose: bibleText(section.prose, lang)
});
