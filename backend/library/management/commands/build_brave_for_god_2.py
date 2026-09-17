"""Build *Brave for God: Book Two* — six more For Young Readers hero lives.

The second volume of the house-written children's hero collection (see
``build_brave_for_god``). Original prose, committed here as module constants,
nothing fetched. Leans further into the Global South and the East African
Revival: an Indian scholar who rescued the forgotten, a Ugandan bishop who
loved his enemy, an explorer who fought the slave trade, and more. Five of the
six already have Ochorus author pages.

Fixture-driven: ``seed_books`` creates it on the next deploy from
``fixtures/content/books/brave-for-god-2.en.json``. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_brave_for_god_2
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import covers, english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter

SLUG = "brave-for-god-2"
TITLE = "Brave for God: Book Two"
SUBTITLE = "Six more who followed Jesus into the wide world"
AUTHOR_SLUG = "ochorus-originals"
COVER_COLOR = covers.ink_safe("#2f6b5c")  # a brave green, floored to WCAG AA

DESCRIPTION = (
    "Six more true stories of faith, told simply for young readers: a poor "
    "cobbler who gave India the Bible; a mill boy who walked across Africa and "
    "fought the slave trade; a Ugandan bishop who loved even a cruel ruler; a "
    "brilliant Indian scholar who rescued the widows and orphans no one else "
    "would help; a watchmaker who hid the hunted; and a runner who gave up the "
    "race. Ordinary people made brave by God — the second book of Brave "
    "for God."
)

ATTRIBUTION = (
    "An Ochorus Original, written for young readers. The stories are true; the "
    "telling is our own."
)

CHAPTERS: list[tuple[str, list[str]]] = [
    (
        "William Carey: The Cobbler Who Would Not Give Up",
        [
            "William Carey was a poor man who mended shoes in a little English "
            "village. He was not clever in the way rich men were clever — he "
            "had left school early to work — but he had a hungry mind. While "
            "his hands stitched leather, he taught himself languages, one word at a "
            "time, from books propped up on his workbench.",
            "On the wall of his workshop William hung a map of the whole world, "
            "drawn by his own hand, with notes scribbled all over it. As he worked, "
            "he looked at the great lands far away — India, China, Africa, the "
            "islands of the sea — where millions of people had never once "
            "heard the name of Jesus. And it broke his heart.",
            "In those days many Christians thought there was nothing to be done "
            "about it. If God wanted those far-off people to hear, they said, God "
            "would see to it without any help from us. But William did not believe "
            "God worked that way. He stood up among older, grander men and said "
            "something that changed the world: <em>Expect great things from God; "
            "attempt great things for God.</em>",
            "Then he did the hard part — he went. William sailed to India, and "
            "there he stayed for the rest of his life, forty years, and never came "
            "home. He set himself the enormous task of putting the Bible into the "
            "languages of India, so that the people could read God's words for "
            "themselves. With his friends he translated the Bible, in whole or in "
            "part, into dozens of Indian languages — more than most people "
            "could even learn to speak.",
            "He did more than translate. He started schools. He planted gardens and "
            "studied the plants of India. And he fought hard, and at last "
            "successfully, against a cruel custom of burning widows alive.",
            "People remember William Carey as the father of modern missions — "
            "the one who woke the church up to the whole wide world. But he never "
            "thought himself anything special. If anyone remembered him at all, he "
            "once said, let it be only as a man who could plod — who kept on "
            "and on and would not give up. And plod on he did, until the far "
            "countries on his hand-drawn map could read the good news in their own "
            "tongues.",
        ],
    ),
    (
        "David Livingstone: The Man Who Walked Across Africa",
        [
            "Like Mary Slessor after him, David Livingstone grew up poor in "
            "Scotland and went to work in a cotton mill when he was only ten years "
            "old. He fixed a book open on the spinning machine and read as he "
            "worked, snatching learning between the roar of the wheels. Bit by bit, "
            "he taught himself enough to become a doctor.",
            "David went to Africa to tell people about Jesus, but he soon found he "
            "could not sit still in one place. There was a whole vast continent "
            "that maps of his day left blank, full of peoples no outsider had ever "
            "met. So David walked. He walked thousands upon thousands of miles, "
            "across deserts and through forests, over mountains and along great "
            "rivers, further than almost any traveller had gone before.",
            "But the more he walked, the more he saw a terrible thing. Everywhere he "
            "went, slave traders were stealing people from their homes — "
            "mothers, fathers, children — and marching them away in chains to "
            "be sold. David called the slave trade “the open sore of the "
            "world,” and he made it his life's work to help end it. He wrote "
            "and spoke and travelled to shame the powerful into stopping it.",
            "David made deep friendships among the African people he lived and "
            "travelled with, and they loved him. He was often ill, and often alone, "
            "and far from home for years at a time. He died in Africa, on his "
            "knees beside his bed, as if he had fallen asleep praying.",
            "Then his African friends did something wonderful. They did not want his "
            "body lost in the wilderness. So they carried him — by hand, taking "
            "turns — more than a thousand miles to the coast, a journey of many "
            "months, so that he could be sent home to be buried with honour. But "
            "first, because they knew how much he had loved their land, they buried "
            "his heart in the soil of Africa. And there it stayed.",
        ],
    ),
    (
        "Festo Kivengere: The Man Who Loved His Enemy",
        [
            "Festo Kivengere grew up herding cattle on the green hills of Uganda, "
            "in the heart of Africa. As a young man he met Jesus during a great "
            "wave of new faith that swept East Africa, and joy so filled him that "
            "he could not keep it to himself. He became one of the most loved "
            "preachers his country ever knew — some called him “the Billy "
            "Graham of Africa.”",
            "But a dark time came to Uganda. A cruel ruler named Idi Amin seized "
            "power, and he was terribly afraid of anyone who would not bow to him. "
            "His soldiers arrested and killed many people, including Christians who "
            "spoke the truth. One of them was Festo's own dear friend, Archbishop "
            "Janani Luwum, who was murdered for standing up to the dictator.",
            "Festo knew he might be next. Soldiers were looking for him. So one "
            "night he and his wife fled, climbing on foot over the steep mountains "
            "at the border, through the darkness, until they crossed safely into "
            "the next country. He had lost his home and his friend and very nearly "
            "his life.",
            "Now, anyone would understand if Festo had hated Idi Amin. But Festo had "
            "learned something at the foot of the cross of Jesus, where a dying Man "
            "had prayed, <em>Father, forgive them.</em> Instead of hate, Festo chose "
            "love. He even wrote a whole book with a title that astonished people: "
            "<em>I Love Idi Amin.</em> He did not mean that the cruel things were "
            "good — they were wicked, and he said so. He meant that he would "
            "not let hate grow in his own heart, because Jesus had forgiven him, "
            "and so he could forgive too.",
            "Festo Kivengere spent the rest of his life carrying that message across "
            "the world: that the love of God is stronger than the worst that evil "
            "can do, and that even an enemy can be loved.",
        ],
    ),
    (
        "Pandita Ramabai: The Scholar Who Rescued the Forgotten",
        [
            "In India long ago, most girls were not taught to read at all. But "
            "Ramabai's father believed a girl could learn, and he taught his "
            "daughter the oldest and hardest books in the land. She learned so much "
            "that when she grew up, the wise men of India gave her a special name: "
            "<em>Pandita</em>, which means “the learned one.” A woman had "
            "almost never been given such an honour.",
            "But Ramabai had seen how hard life could be for women and girls in her "
            "country. When a girl's husband died, she was often treated as if the "
            "sadness were her fault — these “widows,” some of them "
            "only children, were made to suffer, and many had no one at all to care "
            "for them. And when famine came and the crops failed, it was the "
            "orphans and the poor who starved.",
            "Ramabai became a follower of Jesus, and she believed He had given her "
            "all her learning for one purpose: to rescue the people India had "
            "forgotten. So that is what she did. She travelled into the worst of "
            "the famine and gathered up starving girls and orphans by the hundreds "
            "and brought them home.",
            "She built a place for them near the city of Pune and called it "
            "<em>Mukti</em>, which means “Salvation.” It grew into a great "
            "home where thousands of rescued women and children were fed and taught "
            "and loved, and learned trades so they could stand on their own. And "
            "like William Carey, Ramabai gave her people the Scriptures in their "
            "own words, translating the whole Bible into her Marathi language "
            "— a labour of many years that she finished only just before she "
            "died.",
            "Ramabai grew famous, and was honoured even by those who did not share "
            "her faith, for her learning and her tireless love for the poor. But "
            "fame never turned her head. She wore plain clothes, ate simple food, "
            "and worked beside the very women she had rescued, until they were not "
            "her servants but her family.",
            "Pandita Ramabai took the learning that was meant to make her famous and "
            "spent it, every bit, on the widows and orphans nobody else would "
            "help.",
        ],
    ),
    (
        "Corrie ten Boom: The Watchmaker Who Hid the Hunted",
        [
            "Corrie ten Boom lived above her family's watch shop in Holland, where "
            "her father mended clocks and taught her the trade. The ten Booms were "
            "quiet, kind people who loved God and loved their neighbours — and "
            "one day that love was put to a terrible test.",
            "Armies had marched into Holland, ruled by men who hunted down the "
            "Jewish people to imprison and kill them, only because they were Jews. "
            "When frightened Jewish families came knocking at the watch shop, the "
            "ten Booms did not turn them away. They took them in and hid them.",
            "Corrie's brave helpers built a secret room behind the wall of her own "
            "bedroom — so cleverly that no one could tell it was there. When "
            "soldiers came searching, the hidden families would slip through a "
            "little door and stand silent in that narrow space until the danger "
            "passed. In this way the ten Booms saved many lives.",
            "But one day they were betrayed. Soldiers arrested the whole family and "
            "sent Corrie and her sister Betsie to a dreadful prison camp, a place of "
            "cold and hunger and cruelty. Even there the two sisters told the other "
            "prisoners about God's love, and Betsie kept saying that no pit is so "
            "deep that God's love is not deeper still. Betsie died in that camp. "
            "Corrie lived, and was set free.",
            "After the war, Corrie travelled the world telling her story. The "
            "hardest part came when she met, face to face, one of the cruel guards "
            "from the camp — now sorry for what he had done, holding out his "
            "hand. Everything in her wanted to turn away. But she remembered that "
            "God had forgiven her, and she prayed for the strength to forgive him "
            "— and she took his hand. Corrie ten Boom spent the rest of her "
            "long life teaching the world that there is no one God cannot forgive, "
            "and no hurt His love cannot heal.",
        ],
    ),
    (
        "Eric Liddell: The Runner Who Would Not Run on Sunday",
        [
            "Eric Liddell was born in China, where his parents had gone to tell "
            "people about Jesus, and he grew up to be the fastest runner in all of "
            "Scotland. When he raced, people said, he ran with his head thrown back "
            "and his face lifted to the sky, as if he were running for the sheer "
            "joy of it. “God made me fast,” Eric said, “and when I "
            "run, I feel His pleasure.”",
            "In 1924 Eric was chosen to run for his country in the Olympic Games, "
            "and everyone was sure he would win the hundred-metre race. Then the "
            "timetable was announced, and Eric's heart sank: his race was to be run "
            "on a Sunday. Eric believed Sunday was God's day, a day to rest and "
            "worship, and he made up his mind that he would not run on it — not "
            "even for an Olympic gold medal.",
            "People were angry. Newspapers called him foolish. The whole country "
            "urged him to change his mind. But Eric would not. So he trained "
            "instead for a different, longer race, the four hundred metres, which "
            "was not his best and which nobody expected him to win.",
            "On the day of that race, someone slipped a note into Eric's hand. It "
            "said that God honours those who honour Him. Eric ran as though his feet "
            "had wings — and he not only won the gold medal, he broke the world "
            "record. The boy who gave up his best race had been given a better one.",
            "But the most surprising thing came next. At the very height of his "
            "fame, when he could have had anything, Eric gave it all up and went "
            "back to China to serve as a missionary and teacher. Years later, during "
            "a great war, he was locked in a crowded prison camp. There he became "
            "everyone's friend and helper, teaching the children games and lessons, "
            "carrying the sick, and giving away his own small share of food. He died "
            "in that camp, worn out from caring for others, and the whole camp "
            "mourned him. Eric Liddell had run his last and best race — not for "
            "a medal, but for the love of God and of everyone around him.",
        ],
    ),
]


class Command(BaseCommand):
    help = "Build the young-readers hero collection 'Brave for God: Book Two' (dev DB); then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist as exc:
            raise CommandError(f"author {AUTHOR_SLUG!r} not found — seed authors.json first.") from exc

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "source_url": "",
        }
        next_order = (Book.objects.aggregate(m=Max("sort_order"))["m"] or 0) + 1
        book, created = Book.objects.update_or_create(
            slug=SLUG,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": next_order,
            },
        )
        book.chapters.all().delete()

        total = 0
        for order, (title, paras) in enumerate(CHAPTERS, start=1):
            body = "".join(f"<p>{p}</p>" for p in paras)
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 300:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order}: {title[:46]:46} {wc:>4} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"))
