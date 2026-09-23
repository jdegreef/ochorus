"""Build *Brave for God* — a For Young Readers collection of six short hero lives.

House-written (Ochorus Originals), not an import: the prose is original and
lives here as module constants (committed, not fetched). Six true stories of
faith retold for young readers in Ochorus's own voice — the Global-South and
women believers as heroes in their own right, the missionaries drawn with
humility. All six subjects already have Ochorus author pages.

Fixture-driven like every other book: ``seed_books`` creates it on the next
deploy from ``fixtures/content/books/brave-for-god.en.json``. This command
GENERATES that fixture reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_brave_for_god
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import covers, english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter, Series

SLUG = "brave-for-god"
TITLE = "Brave for God"
SUBTITLE = "Six who followed Jesus into the wide world"
AUTHOR_SLUG = "ochorus-originals"
COVER_COLOR = covers.ink_safe("#8a3f4a")  # a warm brave red, floored to WCAG AA

DESCRIPTION = (
    "Six true stories of faith, told simply for young readers: a boy carried off "
    "on a slave ship who gave his people the Bible in their own language; a mill "
    "girl who feared nothing; a man who prayed for breakfast and fed ten thousand "
    "orphans; a maid who led a hundred children over the mountains; and more. "
    "Ordinary people who trusted God and were made brave — from Africa and "
    "Asia and the ends of the earth."
)

ATTRIBUTION = (
    "An Ochorus Original, written for young readers. The stories are true; the "
    "telling is our own."
)

# (chapter title, [paragraphs]) — original prose, one hero per chapter.
CHAPTERS: list[tuple[str, list[str]]] = [
    (
        "Samuel Crowther: The Boy from the Slave Ship",
        [
            "When Samuel Crowther was a boy in Africa, he was not called Samuel at "
            "all. His name was Ajayi, and he lived in a town called Osogun, in the "
            "land of the Yoruba people, in what is now Nigeria. He had a mother and "
            "brothers and sisters and a home he loved.",
            "One terrible morning when he was about twelve years old, raiders swept "
            "into the town. They set the houses on fire and dragged the people away "
            "in ropes to be sold as slaves. Ajayi was torn from his mother. He was "
            "sold once, and then again, and again, until at last he was pushed onto "
            "a crowded ship bound across the sea. Below the deck it was dark and "
            "hot and full of frightened people. He did not think he would ever see "
            "his home, or the sky, again.",
            "But God had not forgotten the boy in the dark. Out on the water, a "
            "British ship came sailing after them. Its sailors hunted for slave "
            "ships and set the captives free. They caught Ajayi's ship, struck off "
            "the chains, and carried the freed people to a town called Freetown, in "
            "Sierra Leone, where they could begin a new life.",
            "In Freetown, Ajayi did something he had never been allowed to do "
            "before: he went to school. He turned out to be a wonderful learner. "
            "He soaked up reading and writing the way dry ground soaks up rain. "
            "When he was baptised as a Christian, he took a new name — Samuel "
            "Crowther — but he never forgot Ajayi, or his people, or the "
            "language they spoke.",
            "That last thing became his life's great work. Samuel had heard the "
            "good news of Jesus in English. But his own people, the Yoruba, could "
            "not read English. So Samuel sat down and began the long, patient job "
            "of putting the Bible into the Yoruba language, word by word, so that "
            "mothers and children and old men in his homeland could read it for "
            "themselves. He helped write down the Yoruba language for the very "
            "first time.",
            "Samuel grew up to be a minister, and then, in 1864, something happened "
            "that had never happened before: he was made a bishop — the first "
            "African bishop in his church. The boy who had been sold in chains now "
            "led others in following Jesus, and he did it as an African, proud of "
            "the people he came from.",
            "Samuel Crowther could have grown up bitter about all that had been "
            "done to him. Instead he spent his life giving his people the greatest "
            "gift he had been given: the words of God, in the language of home.",
        ],
    ),
    (
        "Mary Slessor: The Girl Who Feared Nothing",
        [
            "Mary Slessor grew up poor in the grey city of Dundee, in Scotland. Her "
            "family had so little money that Mary went to work in a jute mill when "
            "she was only eleven, tending the great clattering machines from early "
            "morning, and going to school for just half the day. She had red hair "
            "and bright blue eyes and a temper she had to learn to tame.",
            "In the mill, someone gave Mary stories about a missionary named David "
            "Livingstone, who had travelled across Africa. Mary read them until she "
            "could almost see the rivers and the forests. She made up her mind: one "
            "day she would go too.",
            "And she did. When she was grown, Mary sailed to Calabar, in what is "
            "now Nigeria, to tell people about Jesus. But Mary did not want to live "
            "apart from the people in a comfortable house. She wanted to live with "
            "them. She learned their language, Efik, until she could laugh and "
            "argue and pray in it. She ate their food and slept in their villages "
            "and walked barefoot through the forest. The people stopped seeing her "
            "as a stranger. They called her “Ma.”",
            "In that place there was a cruel and frightening custom. When twins "
            "were born, people believed the babies were cursed and that one of them "
            "must be a child of an evil spirit. So the twins were taken out to the "
            "forest and left to die, and their mother was driven away.",
            "Mary thought this was a lie, and a wicked one. So whenever she heard of "
            "twins, she ran — into the forest, into the dark, into the middle "
            "of angry crowds — and she scooped up the babies and carried them "
            "home. She raised many of them as her own. Little by little, because "
            "one small red-haired woman would not be afraid, the killing of twins "
            "began to stop.",
            "Chiefs came to trust her so much that they asked her to settle their "
            "quarrels. A woman who had once been too poor to finish school now sat "
            "as a judge of peace between whole villages.",
            "People said Mary Slessor feared nothing. That was not quite true. Mary "
            "was often afraid. But she had decided long before that she would rather "
            "be afraid and go, than be safe and stay — because she believed "
            "God was going with her.",
        ],
    ),
    (
        "Hudson Taylor: The Man Who Would Not Be a Stranger",
        [
            "Hudson Taylor was a young man from England who longed to tell the "
            "people of China about Jesus. In his day, China was the largest country "
            "in the world, and most of it had never heard the good news even once.",
            "When Hudson arrived, he noticed something that troubled him. The "
            "missionaries there dressed in English clothes, lived in English houses, "
            "and ate English food. To the people of China they looked like foreign "
            "strangers, and it was hard for a stranger to be trusted or believed.",
            "So Hudson did something that shocked the other missionaries. He put "
            "away his English suit. He dressed in the clothes the Chinese people "
            "wore. He grew his hair long at the back in a braid, the way Chinese men "
            "did then. Some of his own friends laughed at him and said he had gone "
            "too far. But now, when Hudson walked through a town, the people did not "
            "see a foreigner. They saw a man who had come close, who had made "
            "himself one of them so that they might listen.",
            "Hudson wanted to reach not just the coast of China but the vast inland, "
            "where no missionary had ever gone. To do it he would need many workers "
            "and a great deal of money — and he had almost none. So Hudson "
            "made a quiet, daring decision. He would never ask any person for "
            "money. He would ask only God, in prayer, and trust God to send what "
            "was needed.",
            "It was a frightening way to live. There were times when there was "
            "little in the cupboard and nothing in his pocket. But again and again "
            "the money came — sometimes in the very hour it was needed, from "
            "people who had no idea how great the need was.",
            "Hudson Taylor started a mission that sent hundreds of workers deep into "
            "China, to places that had waited hundreds of years to hear the name of "
            "Jesus. He spent more than fifty years at it, and never grew tired of "
            "the country or its people.",
            "Hudson had learned a lesson he never forgot: to reach people, you must "
            "first come near to them. He would not stand far off and shout. He "
            "would come close, and become a friend, and would not be a stranger.",
        ],
    ),
    (
        "George Müller: The Man Who Prayed for Breakfast",
        [
            "When George Müller was a boy in Germany, he was not good at all. He "
            "lied, and he stole, even from his own father, and he ended up in "
            "prison before he was sixteen. He seemed the last person on earth to "
            "become a hero of faith.",
            "But George met Jesus, and everything turned around. He moved to the "
            "city of Bristol, in England, and there he saw something that broke his "
            "heart: children with no mothers or fathers, sleeping in the streets, "
            "hungry and alone. George decided to build a home for them.",
            "Then he decided something even more surprising. He would run the home "
            "in a way that would show everyone how real God is. He would never ask "
            "a single person for money. He would not send out letters begging, or "
            "hint that he was short. He would tell God alone what he needed, and "
            "wait.",
            "One famous morning, the children sat down at the long tables with their "
            "plates and cups in front of them — and there was no food in the "
            "house at all, and no money to buy any. George stood up and thanked God "
            "for the breakfast they were about to eat, though there was nothing "
            "there to eat.",
            "As he finished praying, there was a knock at the door. A baker stood "
            "outside. He could not sleep in the night, he said, and felt he must "
            "get up and bake bread for the children, and here it was, still warm. "
            "The knock came again. It was the milkman: his cart had broken down "
            "right outside, and he did not want the milk to spoil — would the "
            "children like it? The children ate breakfast that morning after all.",
            "Things like that did not happen only once. Over his long life George "
            "Müller cared for more than ten thousand orphans, and built great houses "
            "to keep them warm and fed and taught. And through all of it, he asked "
            "no one but God.",
            "George Müller wanted the whole world to see one simple thing: that God "
            "hears, and God provides. He proved it not with clever words, but with "
            "ten thousand children who went to bed each night with full stomachs "
            "because a bad boy from Germany had learned to pray.",
        ],
    ),
    (
        "Gladys Aylward: The Maid Who Led a Hundred Children",
        [
            "Gladys Aylward was a small woman from London who worked as a maid, "
            "cleaning other people's houses. She was sure that God wanted her to go "
            "to China. But when she asked a mission society to send her, they tested "
            "her and told her no — she was not clever enough, they said, and "
            "too old to learn the language.",
            "Gladys did not give up. She saved her wages, penny by penny, until she "
            "had just enough for the cheapest, longest, most dangerous way to travel "
            "— by train across the whole of Europe and Asia. She arrived at a "
            "town called Yangcheng, high in the mountains, with almost nothing but "
            "her Bible and her stubbornness.",
            "And there the people came to love her. She learned the language after "
            "all. She opened an inn where travellers could rest and hear stories "
            "about Jesus. She even became an officer whose job was to travel the "
            "villages, and everywhere she went she gathered up children who had no "
            "one to care for them, until she had a whole houseful.",
            "Then war came. Soldiers invaded the land, and it was no longer safe to "
            "stay. Gladys had nearly a hundred children in her care, and no army to "
            "protect them — only herself. So she did the only thing she could. "
            "She gathered the children and set out on foot, over the mountains, to "
            "carry them to safety on the far side.",
            "It took nearly two weeks. They climbed steep paths and crossed a wide, "
            "rushing river. There was little food, and the little ones grew tired, "
            "and Gladys carried the smallest and sang to keep them going. When they "
            "were afraid, she reminded them of the God who had brought His people "
            "safely through the sea long ago.",
            "Every single child came through the mountains alive.",
            "The clever people had told Gladys Aylward that she was not enough. God "
            "took the maid they turned away and made her strong enough to carry a "
            "hundred children through a war.",
        ],
    ),
    (
        "Amy Carmichael: The Mother of the Rescued",
        [
            "Amy Carmichael was born in Ireland, with brown eyes she did not like. "
            "As a small girl she prayed that God would turn them blue, and in the "
            "morning she ran to the mirror — and they were still brown. She was "
            "disappointed then. Years later she understood: God had a reason for "
            "those brown eyes, and He would use them.",
            "Amy grew up and went far away, to the south of India, to tell people "
            "about Jesus. There she discovered a secret that filled her with horror. "
            "Little children, some of them only babies, were being taken from their "
            "families and given to live in temples, where terrible things were done "
            "to them, and from which they were never allowed to leave.",
            "Amy could not walk past that. She began, very quietly and very bravely, "
            "to rescue the children. Sometimes a frightened child would be smuggled "
            "to her in the night. Sometimes Amy went herself into places she was not "
            "meant to go. To pass through the crowds without being caught, she "
            "dressed in a plain Indian sari and stained her fair skin dark with "
            "coffee — and now her brown eyes, the ones she had wished away as a "
            "girl, helped her blend in and go unseen. God had known.",
            "One by one, then dozens by dozens, the rescued children came to live "
            "with Amy at a place called Dohnavur. She made it a real home, full of "
            "gardens and songs and safety, where a child who had known only fear "
            "could learn to laugh. The children did not call her “miss” or "
            "“madam.” They called her <em>Amma</em> — which means "
            "“mother.”",
            "Amy never married and never went home to Ireland. She gave her whole "
            "life to the rescued children of Dohnavur. Near the end, after a fall, "
            "she spent twenty years unable to leave her room — and even then "
            "she kept writing, sending out words to comfort and strengthen people "
            "all over the world.",
            "Amy Carmichael had once wanted different eyes and an easier life. "
            "Instead she became a mother to children no one else would save — "
            "and would not have traded them for anything.",
        ],
    ),
]


class Command(BaseCommand):
    help = "Build the young-readers hero collection 'Brave for God' (dev DB); then serialize the fixture."

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
            "series": Series.objects.get(slug="brave-for-god"),
            "series_position": 1,
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
            self.stdout.write(f"  ch {order}: {title[:44]:44} {wc:>4} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"))
