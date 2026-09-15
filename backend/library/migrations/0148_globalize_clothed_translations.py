"""Globalize the Clothed with Strength and Dignity TRANSLATIONS for the worldwide church.

Companion to the fixture edits in the same PR, and the translation counterpart of
migration 0146 (which globalized the English edition). `seed_books` upserts every
book ROW every deploy — including each per-language row — so the reworded
translated *descriptions* reach prod on their own; but it never touches an
existing book's CHAPTERS, so the translated chapter-body rewrites need this data
migration to reach an already-seeded production DB. On a fresh DB it no-ops
(chapters load from the fixture after migrate); the fixture carries the same
settled text, so the halves agree and seed_books reports no chapter drift.

Only the framing that assumed an East African reader is widened; every historical
reference (Uganda Martyrs, the East African Revival, Nsibambi, Gayaza, Perpetua,
the language/food lists) is kept, exactly as the English edition kept them. Each
replacement is guarded by an `old in body` check, so this is idempotent.

Derived columns are set explicitly (a historical model bypasses Chapter.save()):
body_text/word_count are re-derived with the real helpers and search_vector is
NULLed so backfill_search_vectors rebuilds it.
"""

from django.db import migrations

SLUG = "clothed-with-strength-and-dignity"

# (language, chapter order) -> [(old body_html, new body_html), ...]
CHAPTER_EDITS = {
    ('es', 1): [
        ('El mismo Dios que hizo los montes Rwenzori, que extendió las aguas del lago Victoria, que colgó cada estrella en el cielo',
         'El mismo Dios que levantó las grandes montañas, que extendió las aguas de todo lago y mar, que colgó cada estrella en el cielo'),
    ],
    ('es', 2): [
        ('Más cerca de nuestro propio tiempo y lugar, el Avivamiento de África Oriental',
         'Más cerca de nuestro propio tiempo, el Avivamiento de África Oriental'),
    ],
    ('es', 3): [
        ('Y ahora, aquí en África Oriental, tenemos la Biblia en muchas de nuestras propias lenguas: luganda, suajili, kinyarwanda, runyankole, luo y muchas más. ¡Qué regalo es este!',
         'Y ahora la Biblia ha sido traducida a miles de lenguas: solo en África Oriental, al luganda, suajili, kinyarwanda, runyankole, luo y muchas más; y por todo el mundo, muy probablemente a la tuya. ¡Qué regalo es este!'),
    ],
    ('es', 5): [
        ('las presiones que enfrentan muchas mujeres solteras en África Oriental.',
         'las presiones que enfrentan muchas mujeres solteras: presiones que se sienten con fuerza en África Oriental y en muchas culturas del mundo.'),
        ('Las tías preguntan cuándo traerás a alguien a casa. Las mujeres en el mercado murmuran sobre por qué sigues sola.',
         'Los parientes preguntan cuándo traerás a alguien a casa. Los vecinos murmuran sobre por qué sigues sola.'),
    ],
    ('es', 6): [
        ('los próximos líderes de tu aldea, de tu pueblo, de tu nación. La manera en que sean criados determinará si el evangelio avanza o retrocede en África Oriental en los años venideros.',
         'los próximos líderes de tu comunidad y de tu nación. La manera en que sean criados ayudará a determinar si el evangelio avanza o retrocede en tu tierra en los años venideros.'),
        ('Las madres africanas siempre han sido grandes narradoras.',
         'Las madres siempre han sido grandes narradoras, y pocas culturas más que la africana.'),
        ('¿Cómo se crían hijos piadosos en el África Oriental de hoy',
         '¿Cómo se crían hijos piadosos en el mundo de hoy'),
        ('Dios sabe que África Oriental tiene muchos huérfanos que necesitan tías cristianas.',
         'Dios sabe que este mundo tiene muchos huérfanos que necesitan madres cristianas en la fe.'),
        ('Orar por Baba cuando está lejos en el trabajo. Orar por la tía enferma.',
         'Orar por su padre cuando está lejos en el trabajo. Orar por un pariente enfermo.'),
    ],
    ('es', 7): [
        ('Aprende a cocinar bien los platos de tu pueblo: matoke, frijoles, arroz, ugali, sukuma wiki, guiso de maní, chapati.',
         'Aprende a cocinar bien los platos de tu pueblo, ya sea matoke, ugali y sukuma wiki, o arroz, frijoles y pan, o lo que sea que alimente a las familias de tu tierra.'),
        ('En nuestra cultura, la hospitalidad es un valor profundo y hermoso.',
         'En muchas culturas —y la cultura de África Oriental es rica en esto— la hospitalidad es un valor profundo y hermoso.'),
        ('En nuestra cultura, con frecuencia existe una fuerte expectativa de que la esposa y madre sirva sin descanso y sin límite.',
         'En muchas culturas existe una fuerte expectativa de que la esposa y madre sirva sin descanso y sin límite.'),
        ('Puedes hacer de una casa de adobe con techo de láminas de hierro un santuario apacible para tu familia.',
         'Puedes hacer incluso de la casa más humilde —una sola habitación alquilada, una casa de adobe con techo de láminas de hierro— un santuario apacible para tu familia.'),
    ],
    ('es', 10): [
        ('En muchas culturas africanas, las mujeres realizan gran parte de la labor física más dura. Acarreamos agua, cultivamos los huertos, cargamos pesados fardos, cocinamos sobre el fuego y lavamos la ropa a mano.',
         'En muchas culturas, las mujeres realizan gran parte de la labor física más dura. En gran parte de África, acarrean agua, cultivan los huertos, cargan pesados fardos, cocinan sobre el fuego y lavan la ropa a mano.'),
        ('Muchas mujeres en África Oriental son el sostén económico de sus familias.',
         'En muchos lugares, las mujeres son el sostén económico de sus familias.'),
        ('Cultivas frijoles y matoke para la venta.',
         'Cultivas cosechas para la venta.'),
    ],
    ('es', 11): [
        ('La cultura de África Oriental siempre ha valorado la hospitalidad.',
         'Muchas culturas valoran la hospitalidad, y la cultura de África Oriental especialmente.'),
        ('Este es un hermoso don de nuestra cultura que concuerda estrechamente con la enseñanza bíblica.',
         'Este es un hermoso don que concuerda estrechamente con la enseñanza bíblica.'),
        ('Muchas personas en nuestras comunidades están enfermas',
         'Muchas personas a tu alrededor están enfermas'),
        ('Las viudas en nuestras comunidades a menudo enfrentan grandes dificultades. Pueden perder su tierra.',
         'Las viudas a menudo enfrentan grandes dificultades. Pueden perder su tierra o su hogar.'),
        ('Uganda y África Oriental tienen muchos huérfanos: algunos a causa del VIH y el SIDA, algunos a causa de la guerra, algunos a causa de la pobreza.',
         'Toda tierra tiene sus huérfanos: algunos a causa del VIH y el SIDA, algunos a causa de la guerra, algunos a causa de la pobreza; África Oriental los ha conocido en gran número.'),
    ],
    ('es', 13): [
        ('En nuestra propia tierra vemos el mismo patrón. Cuando el evangelio llegó a Uganda a finales del siglo XIX',
         'En Uganda vemos el mismo patrón. Cuando el evangelio llegó allí a finales del siglo XIX'),
    ],
    ('es', 14): [
        ('En nuestras aldeas y en nuestros campos has visto dos bueyes uncidos juntos para arar.',
         'En las granjas de muchas tierras, dos bueyes son uncidos juntos para arar, algo familiar en nuestras propias aldeas y campos.'),
    ],
    ('pt', 1): [
        ('O mesmo Deus que fez as montanhas do Rwenzori, que estendeu as águas do Lago Vitória, que pendurou cada estrela no céu',
         'O mesmo Deus que ergueu as grandes montanhas, que estendeu as águas de cada lago e mar, que pendurou cada estrela no céu'),
    ],
    ('pt', 2): [
        ('Mais perto do nosso tempo e do nosso lugar, o Avivamento da África Oriental',
         'Mais perto do nosso tempo, o Avivamento da África Oriental'),
    ],
    ('pt', 3): [
        ('E agora, aqui na África Oriental, temos a Bíblia em muitas das nossas próprias línguas — luganda, suaíli, quiniaruanda, runyankole, luo e muitas outras. Que dádiva é esta!',
         'E agora a Bíblia já foi traduzida para milhares de línguas — só na África Oriental, luganda, suaíli, quiniaruanda, runyankole, luo e muitas outras; e por todo o mundo, muito provavelmente a sua própria. Que dádiva é esta!'),
    ],
    ('pt', 5): [
        ('as pressões que muitas mulheres solteiras enfrentam na África Oriental.',
         'as pressões que muitas mulheres solteiras enfrentam — pressões sentidas de modo agudo na África Oriental e em muitas culturas ao redor do mundo.'),
        ('As tias perguntam quando você trará alguém para casa. As mulheres do mercado cochicham sobre por que você ainda está sozinha.',
         'Os parentes perguntam quando você trará alguém para casa. Os vizinhos cochicham sobre por que você ainda está sozinha.'),
    ],
    ('pt', 6): [
        ('os próximos líderes da sua aldeia, da sua cidade, da sua nação. O modo como forem criados determinará se o evangelho avançará ou recuará na África Oriental nos anos que vêm.',
         'os próximos líderes da sua comunidade e da sua nação. O modo como forem criados ajudará a determinar se o evangelho avançará ou recuará na sua terra nos anos que vêm.'),
        ('As mães africanas sempre foram grandes contadoras de histórias.',
         'As mães sempre foram grandes contadoras de histórias, e poucas culturas o são mais do que a africana.'),
        ('Como criar filhos piedosos na África Oriental de hoje',
         'Como criar filhos piedosos no mundo de hoje'),
        ('e Deus sabe que a África Oriental tem muitos órfãos que precisam de tias cristãs.',
         'e Deus sabe que este mundo tem muitos órfãos que precisam de mães cristãs na fé.'),
        ('Orar pelo Baba quando ele está fora, no trabalho. Orar pela tia que está doente.',
         'Orar pelo pai quando ele está fora, no trabalho. Orar pelo parente que está doente.'),
    ],
    ('pt', 7): [
        ('a comida do seu povo — matoke, feijão, arroz, ugali, sukuma wiki, ensopado de amendoim, chapati.',
         'a comida do seu povo — seja matoke, ugali e sukuma wiki, seja arroz, feijão e pão, seja o que for que alimente as famílias da sua terra.'),
        ('Na nossa cultura, a hospitalidade é um valor profundo e belo.',
         'Em muitas culturas — e a cultura da África Oriental é rica nisto — a hospitalidade é um valor profundo e belo.'),
        ('Na nossa cultura, muitas vezes existe uma forte expectativa de que a esposa e mãe sirva sem descanso e sem limite.',
         'Em muitas culturas existe uma forte expectativa de que a esposa e mãe sirva sem descanso e sem limite.'),
        ('Você pode fazer de uma casa de tijolo de barro com telhado de zinco um santuário de paz para a sua família.',
         'Você pode fazer até da mais humilde casa — um único quarto alugado, uma casa de tijolo de barro com telhado de zinco — um santuário de paz para a sua família.'),
    ],
    ('pt', 10): [
        ('Em muitas culturas africanas, as mulheres realizam boa parte do trabalho físico mais pesado. Buscamos água, cultivamos as hortas, carregamos cargas pesadas, cozinhamos no fogo, lavamos roupa à mão.',
         'Em muitas culturas, as mulheres realizam boa parte do trabalho físico mais pesado. Em boa parte da África, elas buscam água, cultivam as hortas, carregam cargas pesadas, cozinham no fogo, lavam roupa à mão.'),
        ('Muitas mulheres da África Oriental são a coluna econômica das suas famílias.',
         'Em muitos lugares as mulheres são a coluna econômica das suas famílias.'),
        ('Planta feijão e matoke para vender.',
         'Planta lavouras para vender.'),
    ],
    ('pt', 11): [
        ('A cultura da África Oriental sempre valorizou a hospitalidade.',
         'Muitas culturas valorizam a hospitalidade, e a cultura da África Oriental especialmente.'),
        ('Esse é um belo presente da nossa cultura, muito próximo do ensino bíblico.',
         'Esse é um belo presente, muito próximo do ensino bíblico.'),
        ('Muitas pessoas nas nossas comunidades estão doentes',
         'Muitas pessoas ao seu redor estão doentes'),
        ('As viúvas nas nossas comunidades enfrentam com frequência grandes lutas. Podem perder as suas terras.',
         'As viúvas enfrentam com frequência grandes lutas. Podem perder as suas terras ou o seu lar.'),
        ('Uganda e a África Oriental têm muitos órfãos — alguns por causa do HIV e da AIDS, outros por causa da guerra, outros por causa da pobreza.',
         'Toda terra tem os seus órfãos — alguns por causa do HIV e da AIDS, outros por causa da guerra, outros por causa da pobreza; a África Oriental os conheceu em grande número.'),
    ],
    ('pt', 13): [
        ('Na nossa própria terra vemos o mesmo padrão. Quando o evangelho chegou a Uganda no fim do século XIX',
         'Em Uganda, vemos o mesmo padrão. Quando o evangelho chegou ali no fim do século XIX'),
    ],
    ('pt', 14): [
        ('Nas nossas vilas e nas nossas roças, você já viu dois bois jungidos juntos para arar.',
         'Nas roças de muitas terras, dois bois são jungidos juntos para arar — uma cena familiar nas nossas próprias vilas e lavouras.'),
    ],
    ('ar', 1): [
        ('فذاك الإله نفسه الذي صنع جبال روينزوري، والذي بسط مياه بحيرة فيكتوريا، والذي علّق كلّ نجم في السماء',
         'فذاك الإله نفسه الذي أقام الجبال الشوامخ، والذي بسط مياه كلّ بحيرة وبحر، والذي علّق كلّ نجم في السماء'),
    ],
    ('ar', 2): [
        ('وفي زمن أقرب إلينا وفي مكان أقرب إلينا، نجد أنّ نهضة شرق أفريقيا',
         'وفي زمن أقرب إلينا، نجد أنّ نهضة شرق أفريقيا'),
    ],
    ('ar', 3): [
        ('والآن، ها نحن هنا في شرق أفريقيا، عندنا الكتاب المقدّس بكثير من لغاتنا نحن — باللوغندا، والسواحيليّة، والكينيارواندا، والرونيانكولي، واللوو، وبغيرها كثير. فيا لها من عطيّة عظيمة!',
         'والآن قد تُرجم الكتاب المقدّس إلى آلاف اللغات — ففي شرق أفريقيا وحدها نجده باللوغندا، والسواحيليّة، والكينيارواندا، والرونيانكولي، واللوو، وبغيرها كثير؛ وفي أنحاء العالم كلّه، بل على الأرجح بلغتكِ أنتِ. فيا لها من عطيّة عظيمة!'),
    ],
    ('ar', 5): [
        ('دعيني أتكلّم بصراحة عن الضغوط التي تواجهها كثيرات من النساء غير المتزوّجات في شرق أفريقيا.',
         'دعيني أتكلّم بصراحة عن الضغوط التي تواجهها كثيرات من النساء غير المتزوّجات — وهي ضغوط تُحَسّ بشدّة في شرق أفريقيا وفي كثير من الثقافات حول العالم.'),
        ('الخالات والعمّات يسألنك متى تُحضرين أحدًا إلى البيت. والنساء في السوق يتهامسن عن سبب بقائك وحدك إلى الآن.',
         'الأقارب يسألونك متى تُحضرين أحدًا إلى البيت. والجيران يتهامسون عن سبب بقائك وحدك إلى الآن.'),
    ],
    ('ar', 6): [
        ('وهم الذين سيقودون قريتك وبلدتك وأمّتك في الغد. والطريقة التي يُربَّون بها هي التي ستحدّد أيتقدّم الإنجيل في شرق أفريقيا في السنين المقبلة أم يتراجع إلى الوراء.',
         'وهم الذين سيقودون مجتمعك وأمّتك في الغد. والطريقة التي يُربَّون بها هي التي ستُسهم في تحديد أيتقدّم الإنجيل في بلدك في السنين المقبلة أم يتراجع إلى الوراء.'),
        ('فلطالما كانت الأمّهات الأفريقيّات راويات قصص بارعات.',
         'فلطالما كانت الأمّهات راويات قصص بارعات، وقلّ أن تبلغ ثقافةٌ في ذلك ما بلغته الثقافة الأفريقيّة.'),
        ('كيف تربّين أولادًا أتقياء في شرق أفريقيا اليوم',
         'كيف تربّين أولادًا أتقياء في عالم اليوم'),
        ('والله يعلم أنّ في شرق أفريقيا أيتامًا كثيرين يحتاجون إلى خالات مسيحيّات.',
         'والله يعلم أنّ في هذا العالم أيتامًا كثيرين يحتاجون إلى أمّهات في الإيمان.'),
        ('وصلّوا لأجل «بابا» حين يكون غائبًا في عمله. وصلّوا لأجل الخالة المريضة.',
         'وصلّوا لأجل أبيهم حين يكون غائبًا في عمله. وصلّوا لأجل قريب مريض.'),
    ],
    ('ar', 7): [
        ('فتعلّمي أن تطبخي طبخًا جيّدًا أطعمة شعبك — الماتوكي، والفاصولياء، والأرزّ، والأوغالي، والسوكوما ويكي، ويخنة الفول السودانيّ، والتشاباتي.',
         'فتعلّمي أن تطبخي طبخًا جيّدًا أطعمة شعبك — سواء أكانت الماتوكي والأوغالي والسوكوما ويكي، أم الأرزّ والفاصولياء والخبز، أم أيّ طعام يقتات به أهل بلدك.'),
        ('وفي ثقافتنا نحن، الضيافة قيمة عميقة جميلة.',
         'وفي كثير من الثقافات — والثقافة الشرق أفريقيّة غنيّة بهذا — الضيافة قيمة عميقة جميلة.'),
        ('في ثقافتنا نحن، كثيرًا ما يُتوقّع من الزوجة والأمّ توقّعًا شديدًا أن تخدم بلا راحة وبلا حدّ.',
         'في كثير من الثقافات، يُتوقّع من الزوجة والأمّ توقّعًا شديدًا أن تخدم بلا راحة وبلا حدّ.'),
        ('وأنتِ تقدرين أن تجعلي بيتًا من الطوب الطينيّ سقفه من ألواح الحديد ملاذًا هادئًا لعائلتك.',
         'وأنتِ تقدرين أن تجعلي أبسط بيت — غرفةً واحدة مستأجَرة، أو بيتًا من الطوب الطينيّ سقفه من ألواح الحديد — ملاذًا هادئًا لعائلتك.'),
    ],
    ('ar', 10): [
        ('في كثير من الثقافات الأفريقيّة، تقوم النساء بمعظم الأعمال الجسديّة الشاقّة. نحن نستقي الماء، ونشتغل في الحقول والحدائق، ونحمل الأحمال الثقيلة، ونطبخ على النار، ونغسل الثياب بأيدينا.',
         'في كثير من الثقافات، تقوم النساء بمعظم الأعمال الجسديّة الشاقّة. وفي معظم أنحاء أفريقيا يستقين الماء، ويشتغلن في الحقول والحدائق، ويحملن الأحمال الثقيلة، ويطبخن على النار، ويغسلن الثياب بأيديهنّ.'),
        ('فكثيرات من النساء في شرق أفريقيا هنّ العمود الفقريّ لاقتصاد عائلاتهنّ.',
         'ففي أماكن كثيرة تكون النساء العمود الفقريّ لاقتصاد عائلاتهنّ.'),
        ('وأنتِ تزرعين الفاصولياء والماتوكي للبيع.',
         'وأنتِ تزرعين المحاصيل للبيع.'),
    ],
    ('ar', 11): [
        ('لطالما كانت ثقافة شرق أفريقيا مُقدِّرةً للضيافة.',
         'تُقدّر ثقافاتٌ كثيرة الضيافةَ، وثقافة شرق أفريقيا تُقدّرها تقديرًا خاصًّا.'),
        ('وهذه عطيّة جميلة من عطايا ثقافتنا، تتوافق توافقًا وثيقًا مع تعليم الكتاب المقدّس.',
         'وهذه عطيّة جميلة تتوافق توافقًا وثيقًا مع تعليم الكتاب المقدّس.'),
        ('فكثيرون في مجتمعاتنا مرضى',
         'فكثيرون ممّن حولكِ مرضى'),
        ('فالأرامل في مجتمعاتنا كثيرًا ما يواجهن ضيقات عظيمة. فقد يفقدن أرضهنّ التي يعشن منها.',
         'فالأرامل كثيرًا ما يواجهن ضيقات عظيمة. فقد يفقدن أرضهنّ أو بيتهنّ.'),
        ('ففي أوغندا وشرق أفريقيا يتامى كثيرون — بعضهم بسبب فيروس نقص المناعة والإيدز، وبعضهم بسبب الحرب، وبعضهم بسبب الفقر.',
         'فلكلّ أرض يتاماها — بعضهم بسبب فيروس نقص المناعة والإيدز، وبعضهم بسبب الحرب، وبعضهم بسبب الفقر؛ وقد عرفتهم شرق أفريقيا بأعداد كبيرة.'),
    ],
    ('ar', 13): [
        ('وفي بلادنا نحن نرى النمط نفسه يتكرّر. فحين وصل الإنجيل إلى أوغندا في أواخر القرن التاسع عشر',
         'وفي أوغندا نرى النمط نفسه يتكرّر. فحين وصل الإنجيل إليها في أواخر القرن التاسع عشر'),
    ],
    ('ar', 14): [
        ('ففي قرانا وفي مزارعنا، رأيتِ ثورين مقرونين معًا بنير واحد للحراثة.',
         'ففي مزارع بلدان كثيرة، يُقرَن ثوران معًا بنير واحد للحراثة — وهو مشهد مألوف في قرانا وحقولنا.'),
    ],
    ('hi', 1): [
        ('वही परमेश्वर जिसने रुवेनज़ोरी के पहाड़ों को बनाया, जिसने विक्टोरिया झील के जल को फैलाया, जिसने आकाश में हर एक तारे को टाँगा',
         'वही परमेश्वर जिसने बड़े-बड़े पहाड़ों को खड़ा किया, जिसने हर झील और हर समुद्र के जल को फैलाया, जिसने आकाश में हर एक तारे को टाँगा'),
    ],
    ('hi', 2): [
        ('अपने ही समय और अपने ही स्थान के और निकट आएँ',
         'अपने ही समय के और निकट आएँ'),
    ],
    ('hi', 3): [
        ('और अब, यहाँ पूर्वी अफ्रीका में, हमारे पास अपनी ही अनेक भाषाओं में बाइबल है — लुगांडा, स्वाहिली, किन्यारवांडा, रुन्यांकोले, लुओ, और और भी बहुत सी। यह कैसा बड़ा वरदान है।',
         'और अब बाइबल का अनुवाद हजारों भाषाओं में हो चुका है — केवल पूर्वी अफ्रीका में ही लुगांडा, स्वाहिली, किन्यारवांडा, रुन्यांकोले, लुओ, और और भी बहुत सी; और सारे संसार में, बहुत सम्भव है कि आपकी अपनी भाषा में भी। यह कैसा बड़ा वरदान है।'),
    ],
    ('hi', 5): [
        ('मुझे स्पष्ट रूप से उन दबावों की चर्चा करने दीजिए जिनका सामना पूर्वी अफ्रीका की अनेक अविवाहित स्त्रियाँ करती हैं।',
         'मुझे स्पष्ट रूप से उन दबावों की चर्चा करने दीजिए जिनका सामना अनेक अविवाहित स्त्रियाँ करती हैं — ऐसे दबाव जो पूर्वी अफ्रीका में और संसार भर की अनेक संस्कृतियों में तीव्रता से अनुभव किए जाते हैं।'),
        ('मौसियाँ पूछती हैं कि तुम कब किसी को घर लाओगी। बाजार की स्त्रियाँ आपस में कानाफूसी करती हैं कि तुम अब तक अकेली क्यों हो।',
         'रिश्तेदार पूछते हैं कि तुम कब किसी को घर लाओगी। पड़ोसी आपस में कानाफूसी करते हैं कि तुम अब तक अकेली क्यों हो।'),
    ],
    ('hi', 6): [
        ('आपके गाँव के, आपके नगर के, आपके देश के अगले अगुवे हैं। उनका पालन-पोषण किस रीति से होता है, इसी से यह ठहरेगा कि आनेवाले वर्षों में पूर्वी अफ्रीका में सुसमाचार आगे बढ़ेगा या पीछे हटेगा।',
         'आपके समुदाय के और आपके देश के अगले अगुवे हैं। उनका पालन-पोषण किस रीति से होता है, इसी से यह तय होने में सहायता मिलेगी कि आनेवाले वर्षों में आपकी अपनी भूमि में सुसमाचार आगे बढ़ेगा या पीछे हटेगा।'),
        ('अफ्रीकी माताएँ सदा से उत्तम कहानीकार रही हैं।',
         'माताएँ सदा से उत्तम कहानीकार रही हैं, और शायद ही किसी संस्कृति में अफ्रीका की संस्कृति से बढ़कर।'),
        ('आज के पूर्वी अफ्रीका में, जहाँ इतनी बातें आपके विरुद्ध खींचती हैं',
         'आज के संसार में, जहाँ इतनी बातें आपके विरुद्ध खींचती हैं'),
        ('और परमेश्वर जानता है कि पूर्वी अफ्रीका में ऐसे अनेक अनाथ हैं जिन्हें मसीही मौसियों की आवश्यकता है।',
         'और परमेश्वर जानता है कि इस संसार में ऐसे अनेक अनाथ हैं जिन्हें विश्वास में मसीही माताओं की आवश्यकता है।'),
        ('बाबा के लिये प्रार्थना करना जब वह काम पर बाहर गया हो। बीमार मौसी के लिये प्रार्थना करना।',
         'अपने पिता के लिये प्रार्थना करना जब वह काम पर बाहर गया हो। किसी बीमार रिश्तेदार के लिये प्रार्थना करना।'),
    ],
    ('hi', 7): [
        ('अपने लोगों के भोजन अच्छी रीति से पकाना सीखिए — मातोके, फलियाँ, चावल, उगाली, सुकुमा विकी, मूँगफली का सालन, चपाती।',
         'अपने लोगों के भोजन अच्छी रीति से पकाना सीखिए — चाहे वह मातोके, उगाली और सुकुमा विकी हो, या चावल, फलियाँ और रोटी, या जो कुछ भी आपकी भूमि के परिवारों का पोषण करता हो।'),
        ('हमारी संस्कृति में अतिथि-सत्कार एक गहरा और सुन्दर मूल्य है।',
         'अनेक संस्कृतियों में — और पूर्वी अफ्रीकी संस्कृति इसमें बहुत धनी है — अतिथि-सत्कार एक गहरा और सुन्दर मूल्य है।'),
        ('हमारी संस्कृति में प्रायः यह प्रबल आशा की जाती है कि पत्नी और माता बिना विश्राम और बिना सीमा के सेवा करती रहे।',
         'अनेक संस्कृतियों में यह प्रबल आशा की जाती है कि पत्नी और माता बिना विश्राम और बिना सीमा के सेवा करती रहे।'),
        ('मिट्टी की ईंटों और लोहे की चादर की छतवाले घर को भी आप अपने परिवार के लिये शान्ति का आश्रय-स्थान बना सकती हैं।',
         'सबसे साधारण घर को भी — चाहे वह किराए का एक ही कमरा हो, या मिट्टी की ईंटों और लोहे की चादर की छतवाला घर — आप अपने परिवार के लिये शान्ति का आश्रय-स्थान बना सकती हैं।'),
    ],
    ('hi', 10): [
        ('अनेक अफ्रीकी संस्कृतियों में सबसे कठिन शारीरिक श्रम का बड़ा भाग स्त्रियाँ ही करती हैं। हम पानी भरकर लाती हैं, हम बारियों में काम करती हैं, हम भारी बोझ ढोती हैं, हम आग पर भोजन पकाती हैं, हम हाथों से कपड़े धोती हैं।',
         'अनेक संस्कृतियों में सबसे कठिन शारीरिक श्रम का बड़ा भाग स्त्रियाँ ही करती हैं। अफ्रीका के बहुत से भागों में वे पानी भरकर लाती हैं, बारियों में काम करती हैं, भारी बोझ ढोती हैं, आग पर भोजन पकाती हैं, और हाथों से कपड़े धोती हैं।'),
        ('पूर्वी अफ्रीका की अनेक स्त्रियाँ अपने परिवारों की आर्थिक रीढ़ हैं।',
         'अनेक स्थानों में स्त्रियाँ अपने परिवारों की आर्थिक रीढ़ हैं।'),
        ('आप बेचने के लिये सेम और मातोके उगाती हैं।',
         'आप बेचने के लिये फसलें उगाती हैं।'),
    ],
    ('hi', 11): [
        ('पूर्वी अफ्रीकी संस्कृति ने अतिथि-सत्कार को सदा ही मूल्यवान जाना है।',
         'अनेक संस्कृतियाँ अतिथि-सत्कार को मूल्यवान जानती हैं, और पूर्वी अफ्रीकी संस्कृति तो विशेष रूप से।'),
        ('यह हमारी संस्कृति का एक सुन्दर वरदान है, जो बाइबल की शिक्षा से गहरा मेल खाता है।',
         'यह एक सुन्दर वरदान है, जो बाइबल की शिक्षा से गहरा मेल खाता है।'),
        ('हमारे समाजों में बहुत से लोग रोगी हैं',
         'आपके आस-पास बहुत से लोग रोगी हैं'),
        ('हमारे समाजों की विधवाओं को प्रायः बड़े संघर्ष झेलने पड़ते हैं। उनकी भूमि छिन सकती है।',
         'विधवाओं को प्रायः बड़े संघर्ष झेलने पड़ते हैं। उनकी भूमि या उनका घर छिन सकता है।'),
        ('युगाण्डा और पूर्वी अफ्रीका में बहुत से अनाथ हैं — कुछ एच.आई.वी. और एड्स के कारण, कुछ युद्ध के कारण, कुछ दरिद्रता के कारण।',
         'हर देश के अपने अनाथ हैं — कुछ एच.आई.वी. और एड्स के कारण, कुछ युद्ध के कारण, कुछ दरिद्रता के कारण; और पूर्वी अफ्रीका ने तो इन्हें बड़ी संख्या में जाना है।'),
    ],
    ('hi', 13): [
        ('हमारे अपने देश में भी हम यही रीति देखते हैं। जब 1800 के दशक के अन्त में सुसमाचार युगाण्डा पहुँचा',
         'युगाण्डा में भी हम यही रीति देखते हैं। जब 1800 के दशक के अन्त में सुसमाचार वहाँ पहुँचा'),
    ],
    ('hi', 14): [
        ('हमारे गाँवों में और हमारे खेतों में आपने हल जोतने के लिये दो बैलों को एक ही जूए में जुते हुए देखा है।',
         'अनेक देशों के खेतों में हल जोतने के लिये दो बैलों को एक ही जूए में जोता जाता है — यह दृश्य हमारे अपने गाँवों और खेतों में जाना-पहचाना है।'),
    ],
    ('uk', 1): [
        ('Той самий Бог, який здійняв гори Рувензорі, який розлив води озера Вікторія, який повісив у небі кожну окрему зорю',
         'Той самий Бог, який здійняв великі гори, який розлив води кожного озера й моря, який повісив у небі кожну окрему зорю'),
    ],
    ('uk', 2): [
        ('Ближче до нашого часу і до нашого краю: Східноафриканське пробудження',
         'Ближче до нашого часу: Східноафриканське пробудження'),
    ],
    ('uk', 3): [
        ('А тепер тут, у Східній Африці, ми маємо Біблію багатьма нашими власними мовами — луганда, суахілі, кіньяруанда, руньянколе, луо і багатьма іншими. Який же це великий дар!',
         'А тепер Біблію перекладено тисячами мов — лише у Східній Африці це луганда, суахілі, кіньяруанда, руньянколе, луо і багато інших; а по всьому світі — дуже ймовірно, і твоєю рідною. Який же це великий дар!'),
    ],
    ('uk', 5): [
        ('той тиск, який відчувають багато незаміжніх жінок у Східній Африці.',
         'той тиск, який відчувають багато незаміжніх жінок, — тиск, гостро відчутний у Східній Африці й у багатьох культурах по всьому світі.'),
        ('Тітки запитують, коли ж ти нарешті приведеш когось додому. Жінки на ринку перешіптуються, чому ти й досі сама.',
         'Родичі запитують, коли ж ти нарешті приведеш когось додому. Сусіди перешіптуються, чому ти й досі сама.'),
    ],
    ('uk', 6): [
        ('це наступні провідники твого села, твого міста, твого народу. Від того, як їх виховають, залежатиме, чи просуватиметься Євангеліє вперед у Східній Африці в найближчі роки, чи відступатиме.',
         'це наступні провідники твоєї громади і твого народу. Від того, як їх виховають, значною мірою залежатиме, чи просуватиметься Євангеліє вперед у твоєму краю в найближчі роки, чи відступатиме.'),
        ('Африканські матері завжди були чудовими оповідачками.',
         'Матері завжди були чудовими оповідачками, і мало в яких культурах більше, ніж в африканській.'),
        ('Як виховувати побожних дітей у сьогоднішній Східній Африці',
         'Як виховувати побожних дітей у сьогоднішньому світі'),
        ('а Бог знає, що у Східній Африці багато сиріт, які потребують християнських тітоньок.',
         'а Бог знає, що в цьому світі багато сиріт, які потребують християнських матерів у вірі.'),
        ('Помолитися за тата, коли він на роботі. Помолитися за хвору тітоньку.',
         'Помолитися за їхнього батька, коли він на роботі. Помолитися за хворого родича.'),
    ],
    ('uk', 7): [
        ('страви свого народу — матоке, квасолю, рис, угалі, сукума вікі, юшку з арахісу, чапаті.',
         'страви свого народу — чи то матоке, угалі й сукума вікі, чи рис, квасоля і хліб, чи будь-що інше, чим годуються родини твого краю.'),
        ('У нашій культурі гостинність — це глибока й прекрасна цінність.',
         'У багатьох культурах — а східноафриканська культура особливо багата на це — гостинність — це глибока й прекрасна цінність.'),
        ('У нашій культурі часто є сильне сподівання, що дружина й мати служитиме без відпочинку і без межі.',
         'У багатьох культурах є сильне сподівання, що дружина й мати служитиме без відпочинку і без межі.'),
        ('Ти можеш зробити хату із саманної цегли під бляшаним дахом мирним прихистком для своєї родини.',
         'Ти можеш зробити навіть найскромніше житло — одну винайняту кімнату, хату із саманної цегли під бляшаним дахом — мирним прихистком для своєї родини.'),
    ],
    ('uk', 10): [
        ('У багатьох африканських культурах саме жінки виконують найтяжчу фізичну роботу. Ми носимо воду, ми порпаємось на городах, ми тягаємо важкі ноші, ми готуємо на вогні, ми перемо руками.',
         'У багатьох культурах саме жінки виконують найтяжчу фізичну роботу. У значній частині Африки вони носять воду, порпаються на городах, тягають важкі ноші, готують на вогні, перуть руками.'),
        ('Багато жінок у Східній Африці є економічною опорою своїх сімей.',
         'У багатьох місцях жінки є економічною опорою своїх сімей.'),
        ('Ти вирощуєш квасолю та банани на продаж.',
         'Ти вирощуєш урожай на продаж.'),
    ],
    ('uk', 11): [
        ('Східноафриканська культура завжди цінувала гостинність.',
         'Багато культур цінують гостинність, а східноафриканська особливо.'),
        ('Це прекрасний дар нашої культури, який тісно збігається з біблійним ученням.',
         'Це прекрасний дар, який тісно збігається з біблійним ученням.'),
        ('Багато людей у наших громадах хворіють',
         'Багато людей навколо тебе хворіють'),
        ('Вдови в наших громадах часто зазнають великих труднощів. Вони можуть утратити свою землю.',
         'Вдови часто зазнають великих труднощів. Вони можуть утратити свою землю чи свій дім.'),
        ('В Уганді та Східній Африці багато сиріт — хтось через ВІЛ і СНІД, хтось через війну, хтось через бідність.',
         'У кожній землі є свої сироти — хтось через ВІЛ і СНІД, хтось через війну, хтось через бідність; Східна Африка знала їх у великому числі.'),
    ],
    ('uk', 13): [
        ('У нашій власній землі ми бачимо той самий взірець. Коли наприкінці 1800-х років Євангеліє прийшло в Уганду,',
         'В Уганді ми бачимо той самий взірець. Коли наприкінці 1800-х років Євангеліє прийшло туди,'),
    ],
    ('uk', 14): [
        ('У наших селах і на наших полях ти бачила двох волів, запряжених в одне ярмо для оранки.',
         'На фермах у багатьох краях двох волів запрягають в одне ярмо для оранки — це видовище, звичне і в наших селах та на наших полях.'),
    ],
    ('sw', 1): [
        ('Mungu yule yule aliyeziumba milima ya Rwenzori, aliyeyatandaza maji ya Ziwa Victoria, aliyeitundika kila nyota angani',
         'Mungu yule yule aliyeinua milima mikuu, aliyeyatandaza maji ya kila ziwa na bahari, aliyeitundika kila nyota angani'),
    ],
    ('sw', 2): [
        ('Karibu na wakati wetu na mahali petu, Uamsho wa Afrika Mashariki',
         'Karibu na wakati wetu, Uamsho wa Afrika Mashariki'),
    ],
    ('sw', 3): [
        ('Na sasa, hapa Afrika Mashariki, tunayo Biblia katika lugha zetu nyingi wenyewe &mdash; Luganda, Kiswahili, Kinyarwanda, Runyankole, Luo, na nyingine nyingi. Ni zawadi iliyoje hii.',
         'Na sasa Biblia imetafsiriwa katika maelfu ya lugha &mdash; katika Afrika Mashariki peke yake, Luganda, Kiswahili, Kinyarwanda, Runyankole, Luo, na nyingine nyingi; na kotekote duniani, yamkini hata lugha yako mwenyewe. Ni zawadi iliyoje hii.'),
    ],
    ('sw', 5): [
        ('Niseme waziwazi kuhusu shinikizo ambalo wanawake wengi wasioolewa Afrika Mashariki wanakabiliana nalo.',
         'Niseme waziwazi kuhusu shinikizo ambalo wanawake wengi wasioolewa wanakabiliana nalo — shinikizo linalohisiwa kwa nguvu hapa Afrika Mashariki na katika tamaduni nyingi ulimwenguni pote.'),
        ('Shangazi wanauliza ni lini utaleta mtu nyumbani. Wanawake sokoni wananong&#x27;ona kuhusu kwa nini bado uko peke yako.',
         'Watu wa jamaa wanauliza ni lini utaleta mtu nyumbani. Majirani wananong&#x27;ona kuhusu kwa nini bado uko peke yako.'),
    ],
    ('sw', 6): [
        ('viongozi wajao wa kijiji chako, mji wako, taifa lako. Jinsi wanavyolelewa itaamua kama injili itasonga mbele au itarudi nyuma katika Afrika Mashariki katika miaka ijayo.',
         'viongozi wajao wa jamii yako na taifa lako. Jinsi wanavyolelewa itasaidia kuamua kama injili itasonga mbele au itarudi nyuma katika nchi yako katika miaka ijayo.'),
        ('Akina mama wa Kiafrika siku zote wamekuwa wasimuliaji hodari wa hadithi.',
         'Akina mama siku zote wamekuwa wasimuliaji hodari wa hadithi, na tamaduni chache huzidi ile ya Kiafrika katika hili.'),
        ('Unawaleaje watoto wacha Mungu katika Afrika Mashariki ya leo',
         'Unawaleaje watoto wacha Mungu katika ulimwengu wa leo'),
        ('na Mungu anajua Afrika Mashariki ina yatima wengi wanaohitaji shangazi Wakristo.',
         'na Mungu anajua ulimwengu huu una yatima wengi wanaohitaji akina mama Wakristo katika imani.'),
        ('Kumwombea Baba akiwa mbali kazini. Kumwombea shangazi mgonjwa.',
         'Kumwombea baba yao akiwa mbali kazini. Kumwombea ndugu mgonjwa.'),
    ],
    ('sw', 7): [
        ('Jifunze kupika vizuri vyakula vya watu wako — matoke, maharagwe, wali, ugali, sukuma wiki, mchuzi wa karanga, chapati.',
         'Jifunze kupika vizuri vyakula vya watu wako — vikiwa matoke, ugali na sukuma wiki, au wali, maharagwe na mkate, au chochote kinacholisha familia za nchi yako.'),
        ('Katika utamaduni wetu, ukarimu ni thamani ya ndani na nzuri.',
         'Katika tamaduni nyingi — na utamaduni wa Afrika Mashariki ni tajiri katika hili — ukarimu ni thamani ya ndani na nzuri.'),
        ('Katika utamaduni wetu, mara nyingi kuna matarajio makubwa kwamba mke na mama atatumika bila kupumzika na bila kikomo.',
         'Katika tamaduni nyingi kuna matarajio makubwa kwamba mke na mama atatumika bila kupumzika na bila kikomo.'),
        ('Waweza kuifanya nyumba ya matofali ya udongo yenye paa la mabati kuwa mahali pa amani na usalama kwa jamaa yako.',
         'Waweza kuifanya hata nyumba duni kabisa — chumba kimoja cha kupanga, nyumba ya matofali ya udongo yenye paa la mabati — kuwa mahali pa amani na usalama kwa jamaa yako.'),
    ],
    ('sw', 10): [
        ('Katika tamaduni nyingi za Kiafrika, wanawake hufanya sehemu kubwa ya kazi ngumu za mwili. Tunateka maji, tunalima mashamba, tunabeba mizigo mizito, tunapika kwa moto wa kuni, tunafua nguo kwa mikono.',
         'Katika tamaduni nyingi, wanawake hufanya sehemu kubwa ya kazi ngumu za mwili. Katika sehemu kubwa ya Afrika huteka maji, hulima mashamba, hubeba mizigo mizito, hupika kwa moto wa kuni, na hufua nguo kwa mikono.'),
        ('Wanawake wengi Afrika Mashariki ndio uti wa mgongo wa kiuchumi wa familia zao.',
         'Katika maeneo mengi wanawake ndio uti wa mgongo wa kiuchumi wa familia zao.'),
        ('Unalima maharagwe na matoke kwa ajili ya kuuza.',
         'Unalima mazao kwa ajili ya kuuza.'),
    ],
    ('sw', 11): [
        ('Utamaduni wa Afrika Mashariki umethamini ukarimu siku zote.',
         'Tamaduni nyingi huthamini ukarimu, na utamaduni wa Afrika Mashariki hasa.'),
        ('Hii ni zawadi nzuri ya utamaduni wetu inayolingana kwa karibu na mafundisho ya Biblia.',
         'Hii ni zawadi nzuri inayolingana kwa karibu na mafundisho ya Biblia.'),
        ('Watu wengi katika jamii zetu ni wagonjwa',
         'Watu wengi walio karibu nawe ni wagonjwa'),
        ('Wajane katika jamii zetu mara nyingi hukabili taabu nyingi. Waweza kupoteza ardhi yao.',
         'Wajane mara nyingi hukabili taabu nyingi. Waweza kupoteza ardhi yao au nyumba yao.'),
        ('Uganda na Afrika Mashariki zina yatima wengi — wengine kwa sababu ya VVU na UKIMWI, wengine kwa sababu ya vita, wengine kwa sababu ya umaskini.',
         'Kila nchi ina yatima wake — wengine kwa sababu ya VVU na UKIMWI, wengine kwa sababu ya vita, wengine kwa sababu ya umaskini; Afrika Mashariki imewajua kwa idadi kubwa.'),
    ],
    ('sw', 13): [
        ('Katika nchi yetu wenyewe, tunaona mtindo huohuo. Injili ilipofika Uganda mwishoni mwa miaka ya 1800',
         'Nchini Uganda, tunaona mtindo huohuo. Injili ilipofika huko mwishoni mwa miaka ya 1800'),
    ],
    ('sw', 14): [
        ('Katika vijiji vyetu na mashambani mwetu, umewahi kuona maksai wawili wamefungwa nira pamoja kwa ajili ya kulima.',
         'Katika mashamba ya nchi nyingi, maksai wawili hufungwa nira pamoja kwa ajili ya kulima — mandhari inayozoeleka katika vijiji na mashamba yetu wenyewe.'),
    ],
    ('lg', 1): [
        ("Katonda oyo omu eyakola ensozi za Rwenzori, eyayanjuluza amazzi g'ennyanja Nnalubaale, eyawanika buli mmunyeenye mu ggulu",
         "Katonda oyo omu eyayimusa ensozi ennene, eyayanjuluza amazzi g'ennyanja zonna, eyawanika buli mmunyeenye mu ggulu"),
    ],
    ('lg', 2): [
        ("Ne mu biseera n'ebifo byaffe ffe, Okuzuukuka",
         'Ne mu biseera byaffe ffe, Okuzuukuka'),
    ],
    ('lg', 3): [
        ("Ne kaakano, wano mu Afrika ey'Ebuvanjuba, tulina Baibuli mu nnimi zaffe ennyingi — Oluganda, Oluswayiri, Ikinyarwanda, Orunyankole, Luo, n'endala nnyingi. Kino kirabo kya ngeri ki!",
         "Ne kaakano, Baibuli evvuunuddwa mu nnimi enkumi n'enkumi — mu Afrika ey'Ebuvanjuba yokka, Oluganda, Oluswayiri, Ikinyarwanda, Orunyankole, Luo, n'endala nnyingi; ne mu nsi yonna, oboolyawo n'olulimi lwo ggwe. Kino kirabo kya ngeri ki!"),
    ],
    ('lg', 5): [
        ('Ka njogere lwatu ku kunyigirizibwa bannaabwe abakazi abawuulu abangi mu Buvanjuba bwa Afirika kwe basanga.',
         'Ka njogere lwatu ku kunyigirizibwa abakazi abawuulu abangi kwe basanga — okunyigirizibwa okuwulirwa ennyo mu Buvanjuba bwa Afirika ne mu buwangwa obungi mu nsi yonna.'),
        ("Ba ssenga bakubuuza lw'olireeta omuntu eka. Abakazi mu katale beebuuza lwaki okyali wekka.",
         "Ab'oluganda bakubuuza lw'olireeta omuntu eka. Baliraanwa beebuuza lwaki okyali wekka."),
    ],
    ('lg', 6): [
        ("be bakulembeze abaddako ab'omu kyalo kyo, ekibuga kyo, eggwanga lyo. Engeri gye banaakulizibwamu ye erisalawo oba enjiri erikulaakulana oba erikendeera mu Buvanjuba bwa Afirika mu myaka egijja.",
         "be bakulembeze abaddako ab'omu kitundu kyo n'eggwanga lyo. Engeri gye banaakulizibwamu eriyamba okusalawo oba enjiri erikulaakulana oba erikendeera mu nsi yo mu myaka egijja."),
        ('Bamaama Abaafirika bulijjo baabanga bakugu mu kubuulira ebifumu.',
         'Bamaama bulijjo baabanga bakugu mu kubuulira ebifumu, era tewali buwangwa businga obwa Afirika mu kino.'),
        ("Okuza otya abaana ab'okutya Katonda mu Buvanjuba bwa Afirika obwa leero",
         "Okuza otya abaana ab'okutya Katonda mu nsi eya leero"),
        ('era Katonda amanyi nti Buvanjuba bwa Afirika buno bulina bamulekwa bangi abeetaaga baasenga ba Kikristaayo.',
         'era Katonda amanyi nti ensi eno erina bamulekwa bangi abeetaaga bamaama Abakristaayo mu kukkiriza.'),
        ("Basabire Baaba ng'ali ku mirimu. Basabire ssenga omulwadde.",
         "Basabire kitaabwe ng'ali ku mirimu. Basabire ow'oluganda omulwadde."),
    ],
    ('lg', 7): [
        ("Yiga okufumba obulungi emmere y'abantu bo — matooke, ebijanjaalo, omuceere, obugali, enva endiirwa, ebinyeebwa, chapati.",
         "Yiga okufumba obulungi emmere y'abantu bo — ka gabe matooke, obugali n'enva endiirwa, oba omuceere, ebijanjaalo n'omugaati, oba kyonna ekiriisa amaka g'omu nsi yo."),
        ('Mu mpisa zaffe, okusembeza abagenyi mpisa ya muwendo era nnungi nnyo.',
         "Mu buwangwa obungi — era obuwangwa bw'omu Buvanjuba bwa Afirika bugagga mu kino — okusembeza abagenyi mpisa ya muwendo era nnungi nnyo."),
        ("Mu mpisa zaffe, emirundi mingi waliwo essuubi ery'amaanyi nti omukazi era nnyina anaaweerezanga awatali kuwummula era awatali kkomo.",
         "Mu buwangwa obungi waliwo essuubi ery'amaanyi nti omukazi era nnyina anaaweerezanga awatali kuwummula era awatali kkomo."),
        ("Osobola okufuula ennyumba ey'amatoffaali g'ebbumba erina akasolya k'amabaati ekifo eky'emirembe eri ab'omu maka go.",
         "Osobola okufuula n'ennyumba esinga obunafu — akasenge kamu akapangisa, ennyumba ey'amatoffaali g'ebbumba erina akasolya k'amabaati — ekifo eky'emirembe eri ab'omu maka go."),
    ],
    ('lg', 10): [
        ("Mu mpisa nnyingi ez'Afirika, abakazi be bakola emirimu emizibu ennyo egy'omubiri. Tukima amazzi, tulima ennimiro, twetikka emigugu emizito, tufumba ku muliro, tuyoza engoye n'emikono.",
         "Mu buwangwa obungi, abakazi be bakola emirimu emizibu ennyo egy'omubiri. Mu bitundu bingi eby'Afirika bakima amazzi, balima ennimiro, beetikka emigugu emizito, bafumba ku muliro, ne bayoza engoye n'emikono."),
        ("Abakazi bangi mu Buvanjuba bwa Afirika be mugongo gw'ebyenfuna eby'amaka gaabwe.",
         "Mu bifo bingi abakazi be mugongo gw'ebyenfuna eby'amaka gaabwe."),
        ('Olima ebijanjaalo ne matooke okutunda.',
         'Olima ebirime okutunda.'),
    ],
    ('lg', 11): [
        ("Obuwangwa bw'omu Buvanjuba bwa Afirika okuva edda bwassaamu ekitiibwa okusembeza abagenyi.",
         "Obuwangwa obungi buwa ekitiibwa okusembeza abagenyi, era obuwangwa bw'omu Buvanjuba bwa Afirika bwe businga."),
        ("Kino kirabo kirungi eky'obuwangwa bwaffe ekituukagana bulungi n'okuyigiriza kw'Ebyawandiikibwa.",
         "Kino kirabo kirungi ekituukagana bulungi n'okuyigiriza kw'Ebyawandiikibwa."),
        ('Abantu bangi mu bitundu byaffe balwadde',
         'Abantu bangi abakwetoolodde balwadde'),
        ("Bannamwandu mu bitundu byaffe emirundi mingi bayolekagana n'okulwanirira okunene. Bayinza okufiirwa ettaka lyabwe.",
         "Bannamwandu emirundi mingi bayolekagana n'okulwanirira okunene. Bayinza okufiirwa ettaka lyabwe oba amaka gaabwe."),
        ("Yuganda ne Afirika ey'Obuvanjuba birimu bamulekwa bangi — abamu olwa akawuka ka mukenenya n'obulwadde bwa siriimu, abamu olw'entalo, abamu olw'obwavu.",
         "Buli nsi erina bamulekwa baayo — abamu olwa akawuka ka mukenenya n'obulwadde bwa siriimu, abamu olw'entalo, abamu olw'obwavu; Afirika ey'Obuvanjuba ebamanyi mu buwendo bungi."),
    ],
    ('lg', 13): [
        ("Mu nsi yaffe ffe, tulaba enkola y'emu. Enjiri bwe yajja mu Uganda mu myaka gya 1800 egy'oluvannyuma,",
         "Mu Uganda, tulaba enkola y'emu. Enjiri bwe yajja eyo mu myaka gya 1800 egy'oluvannyuma,"),
    ],
    ('lg', 14): [
        ('Mu byalo byaffe ne mu nnimiro zaffe, olabye ente bbiri nga zisibiddwa ku kikoligo kimu okulima.',
         "Mu nnimiro z'omu nsi nnyingi, ente bbiri zisibibwa ku kikoligo kimu okulima &mdash; ekintu ekimanyiddwa mu byalo byaffe ne mu nnimiro zaffe."),
    ],
}


def forwards(apps, schema_editor):
    from library.text import html_to_text, word_count

    Chapter = apps.get_model("library", "Chapter")
    for (language, order), pairs in CHAPTER_EDITS.items():
        ch = (
            Chapter.objects.filter(
                book__slug=SLUG, book__language=language, order=order
            )
            .only("id", "body_html")
            .first()
        )
        if ch is None:
            continue
        html = ch.body_html
        changed = False
        for old, new in pairs:
            if old in html:
                html = html.replace(old, new)
                changed = True
        if not changed:
            continue
        Chapter.objects.filter(pk=ch.pk).update(
            body_html=html,
            body_text=html_to_text(html),
            word_count=word_count(html),
            search_vector=None,
            citations_indexed_at=None,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0147_merge_20260915_1825"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
