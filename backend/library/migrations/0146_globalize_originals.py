"""Globalize the audience-framed Ochorus Originals for the worldwide church.

Companion to the fixture edits in the same PR. `seed_books` upserts the Book row
(so the reworded *descriptions* reach prod on their own), but it deliberately
never touches an existing book's CHAPTERS — so the chapter-body rewrites need a
data migration to reach an already-seeded production DB. On a fresh DB this
no-ops (chapters are loaded from the fixture *after* migrate runs); the fixture
carries the same settled text, so the two halves agree and seed_books reports no
chapter drift.

Only the framing that assumed an East African reader is widened; every historical
reference (Uganda Martyrs, the East African Revival, Nsibambi, Luwum, Kivengere,
Crowther, Gayaza) is kept. Each replacement is guarded by an `old in body` check,
so the migration is idempotent and safe to re-run.

Derived columns are set explicitly because a historical model bypasses
`Chapter.save()`: body_text and word_count are re-derived with the real helpers,
and search_vector is NULLed so the release step `backfill_search_vectors` (which
fills NULLs only) rebuilds it — a bulk text change otherwise leaves the tsvector
STALE and search keeps matching the old prose.
"""

from django.db import migrations

# (slug, chapter order) -> [(old body_html, new body_html), ...]
CHAPTER_EDITS = {
    ('rise-up-men-of-god-2', 2): [
        ('in the north of our country.',
         'in the north of the country.'),
        ('a reminder to every African man:',
         'a reminder to every man:'),
    ],
    ('rise-up-men-of-god-2', 3): [
        ('your small shop in Kampala, your farm in the village, your job in Nairobi, your family in Dar es Salaam?',
         'your small shop, your farm, your job, your family — wherever God has placed you?'),
    ],
    ('rise-up-men-of-god-2', 4): [
        ('Let us be honest about our culture, brothers. In many parts of East Africa, we have inherited practices',
         'Let us be honest about our cultures, brothers. In many places around the world, we have inherited practices'),
        ('the silence about bride price that turned the wife into a purchase',
         'the customs that treat a wife as a possession to be bought'),
    ],
    ('rise-up-men-of-god-2', 5): [
        ('Our nations are overrun with young men who have never been fathered.',
         'So many nations are overrun with young men who have never been fathered.'),
        ('On the boda-boda ride to school.',
         'On the ride or the walk to school.'),
        ('Many fathers in our culture have exasperated their children',
         'Many fathers in every culture have exasperated their children'),
        ('chief reasons our young people walk away from the church.',
         'chief reasons young people walk away from the church.'),
        ('In our African culture, the cane has been used freely for generations.',
         'In many cultures, the cane and the strap have been used freely for generations.'),
        ('but I will say this: many of us crossed a line from biblical discipline into cruelty, and our children have carried those scars',
         'but I will say this: many fathers crossed a line from biblical discipline into cruelty, and their children have carried those scars'),
    ],
    ('rise-up-men-of-god-2', 6): [
        ('We have a serious problem in our culture.',
         'We have a serious problem in many cultures.'),
        ('Brother, our land is full of hard men.',
         'Brother, our world is full of hard men.'),
    ],
    ('rise-up-men-of-god-2', 7): [
        ('Brother, in our East African context, we must confront a spirit of idleness',
         'Brother, in our day, we must confront a spirit of idleness'),
        ('They dream of going abroad to Dubai or America, but they will not dig the garden at home.',
         'They dream of going abroad to some richer country, but they will not dig the garden at home.'),
        ('Learn a skill. Drive a boda-boda. Start small.',
         'Learn a skill. Drive a taxi. Start small.'),
        ('Now let us think about provision in the African context. A Christian man in East Africa often has more than just his immediate family',
         'Now let us think about provision in the wider family. A Christian man in many cultures often has more than just his immediate family'),
        ('Many Christian men in our region have been destroyed by the prosperity gospel',
         'Many Christian men in our day have been destroyed by the prosperity gospel'),
    ],
    ('rise-up-men-of-god-2', 9): [
        ('Here in our region, the East African Revival was marked precisely by this kind of honesty.',
         'The East African Revival was marked precisely by this kind of honesty.'),
    ],
    ('rise-up-men-of-god-2', 10): [
        ('this is crucial in our East African context where alcohol destroys so many homes.',
         'this is crucial in every culture where alcohol destroys so many homes.'),
        ('In our rapidly growing churches across East Africa, this warning is often ignored.',
         'In many rapidly growing churches, this warning is often ignored.'),
        ('the market woman who sells you tomatoes, the boda-boda rider who has driven you',
         'the trader who sells you food, the driver who has carried you'),
        ('In our region, we have seen too many one-man churches',
         'In our day, we have seen too many one-man churches'),
        ('the humble pastor in a small village church in Uganda or Kenya or Tanzania.',
         'the humble pastor in a small village church in some forgotten corner of the world.'),
    ],
    ('rise-up-men-of-god-2', 11): [
        ('they will ever hear from the greatest preacher in Africa.',
         'they will ever hear from the greatest preacher alive.'),
        ('on the walk to school, on the boda-boda, wherever you travel together',
         'on the walk to school, on the bus, wherever you travel together'),
        ('Fathers in East Africa, pass the fire.',
         'Fathers, wherever you are, pass the fire.'),
    ],
    ('rise-up-men-of-god-2', 12): [
        ('some specific sins that devastate men, especially in our East African context.',
         'some specific sins that devastate men everywhere.'),
        ('Second, alcohol. This is a particular plague in East Africa. Home-brewed spirits, local beers, waragi, imported whiskeys — they have destroyed more African homes',
         'Second, alcohol. This is a plague in many places. Home-brewed spirits, local beers, cheap gin, imported whiskeys — they have destroyed more homes'),
        ('Many men in our region cannot lead because they cannot rule their cups.',
         'Many men today cannot lead because they cannot rule their cups.'),
        ('In our culture, bribery is so common it has almost become invisible.',
         'In many places, bribery is so common it has almost become invisible.'),
    ],
    ('rise-up-men-of-god-2', 13): [
        ('Consider also our African brothers who have done the same.',
         'Consider also African brothers who have done the same.'),
    ],
    ('rise-up-men-of-god-2', 14): [
        ('In many African contexts, when the husband dies without a will',
         'In many cultures, when the husband dies without a will'),
        ('East Africa — Uganda, Kenya, Tanzania, Rwanda, Burundi, South Sudan, Ethiopia, and beyond — is waiting for men like you',
         'Your family, your church, your community — your nation, wherever God has placed you — is waiting for men like you'),
        ('Our grandfathers in the faith — Charles Lwanga at Namugongo',
         'The great fathers of the East African church — Charles Lwanga at Namugongo'),
        ('Rise up, man of Africa. The nations are watching.',
         'Rise up, man of God. The nations are watching.'),
        ('For our nations — Uganda, Kenya, Tanzania, Rwanda, Burundi, South Sudan, Ethiopia, Sudan, the Congo, and all of Africa — send us a revival like the fire that fell in the 1930s',
         'For our nations — wherever we live, on every continent — send us a revival like the East African Revival, the fire that fell in the 1930s'),
    ],
    ('clothed-with-strength-and-dignity', 1): [
        ('The same God who made the mountains of Rwenzori, who spread the waters of Lake Victoria, who hung every star in the sky',
         'The same God who raised the great mountains, who spread the waters of every lake and sea, who hung every star in the sky'),
    ],
    ('clothed-with-strength-and-dignity', 2): [
        ('Closer to our own time and place, the East African Revival',
         'Closer to our own time, the East African Revival'),
    ],
    ('clothed-with-strength-and-dignity', 3): [
        ('And now, here in East Africa, we have the Bible in many of our own languages — Luganda, Swahili, Kinyarwanda, Runyankole, Luo, and many more. What a gift this is.',
         'And now the Bible has been translated into thousands of languages — in East Africa alone, Luganda, Swahili, Kinyarwanda, Runyankole, Luo, and many more; and across the world, very likely your own. What a gift this is.'),
    ],
    ('clothed-with-strength-and-dignity', 5): [
        ('the pressures many single women in East Africa face.',
         'the pressures many single women face — pressures felt keenly in East Africa and in many cultures around the world.'),
        ('Aunties ask when you will bring someone home. Women at the market whisper about why you are still alone.',
         'Relatives ask when you will bring someone home. Neighbours whisper about why you are still alone.'),
    ],
    ('clothed-with-strength-and-dignity', 6): [
        ('the next leaders of your village, your town, your nation. How they are raised will determine whether the gospel advances or retreats in East Africa',
         'the next leaders of your community and your nation. How they are raised will help determine whether the gospel advances or retreats in your land'),
        ('African mothers have always been great storytellers.',
         "Mothers have always been great storytellers, and few cultures more so than Africa's."),
        ('How do you raise godly children in the East Africa of today',
         'How do you raise godly children in the world of today'),
        ('and God knows East Africa has many orphans who need Christian aunties.',
         'and God knows this world has many orphans who need Christian mothers in the faith.'),
        ('Pray for Baba when he is away at work. Pray for the sick auntie.',
         'Pray for their father when he is away at work. Pray for a sick relative.'),
    ],
    ('clothed-with-strength-and-dignity', 7): [
        ('the foods of your people — matoke, beans, rice, ugali, sukuma wiki, groundnut stew, chapati.',
         'the foods of your people — whether that is matoke, ugali and sukuma wiki, or rice, beans and bread, or whatever nourishes the families of your land.'),
        ('In our culture, hospitality is a deep and beautiful value.',
         'In many cultures — and East African culture is rich in this — hospitality is a deep and beautiful value.'),
        ('In our culture, there is often a strong expectation that the wife and mother will serve without rest and without limit.',
         'In many cultures there is a strong expectation that the wife and mother will serve without rest and without limit.'),
        ('You can make a mud-brick house with an iron-sheet roof a peaceful sanctuary for your family.',
         'You can make even the humblest house — a single rented room, a mud-brick house with an iron-sheet roof — a peaceful sanctuary for your family.'),
    ],
    ('clothed-with-strength-and-dignity', 10): [
        ('In many African cultures, women do much of the hardest physical labor. We fetch water, we work the gardens, we carry heavy loads, we cook over fires, we wash clothes by hand.',
         'In many cultures, women do much of the hardest physical labor. In much of Africa they fetch water, work the gardens, carry heavy loads, cook over fires, and wash clothes by hand.'),
        ('Many women in East Africa are the economic backbone of their families.',
         'In many places women are the economic backbone of their families.'),
        ('You grow beans and matoke for sale.',
         'You grow crops for sale.'),
    ],
    ('clothed-with-strength-and-dignity', 11): [
        ('East African culture has always valued hospitality.',
         'Many cultures value hospitality, and East African culture especially so.'),
        ('This is a beautiful gift of our culture that aligns closely with biblical teaching.',
         'This is a beautiful gift that aligns closely with biblical teaching.'),
        ('Many people in our communities are sick',
         'Many people around you are sick'),
        ('Widows in our communities often face great struggles. They may lose their land.',
         'Widows often face great struggles. They may lose their land or their home.'),
        ('Uganda and East Africa have many orphans — some because of HIV and AIDS, some because of war, some because of poverty.',
         'Every land has its orphans — some because of HIV and AIDS, some because of war, some because of poverty; East Africa has known them in great number.'),
    ],
    ('clothed-with-strength-and-dignity', 13): [
        ('In our own land, we see the same pattern. When the gospel came to Uganda in the late 1800s',
         'In Uganda, we see the same pattern. When the gospel came there in the late 1800s'),
    ],
    ('clothed-with-strength-and-dignity', 14): [
        ('In our villages and on our farms, you have seen two oxen yoked together for plowing.',
         'On farms in many lands, two oxen are yoked together for plowing — a sight familiar in our own villages and fields.'),
    ],
    ('men-of-prayer-2', 1): [
        ('Why This Book is for Ugandan Pastors',
         'Why This Book is for Pastors'),
        ('Uganda is a nation with a remarkable Christian heritage.',
         'The Church has a remarkable heritage of prayer in every land.'),
        ('transformed thousands of lives across Uganda and neighbouring nations, and its fruit is still visible today.',
         'transformed thousands of lives across the region, and its fruit is still visible today.'),
        ('Uganda has been described by many as one of the most prayerful nations on earth.',
         'Wherever you serve, God has planted witnesses of prayer before you.'),
        ('It is not enough to inherit the prayers of our fathers.',
         'It is not enough to inherit the prayers of those who went before us.'),
        ('This book is written for Ugandan pastors and teachers because the responsibility of a pastor is unique.',
         'This book is written for pastors and teachers because the responsibility of a pastor is unique.'),
        ('Uganda needs men and women like that. Perhaps you are one of them.',
         'The Church needs men and women like that. Perhaps you are one of them.'),
    ],
    ('men-of-prayer-2', 17): [
        ('A Word to Ugandan Pastors',
         'A Word to Pastors Everywhere'),
        ('You are serving God in one of the most spiritually strategic places on earth. Uganda sits at the heart of the African continent, a nation with a history of Christian martyrdom, revival, and the extraordinary blessing of the Holy Spirit.',
         'You are serving God at a strategic moment in His story, wherever He has placed you. The Church has been built on the sacrifice of the faithful in every generation and every land.'),
        ('You are the heirs of all of that.',
         'Wherever you look in church history, you are an heir of that same praying inheritance.'),
        ('poverty and suffering among your people, family breakdown',
         'poverty and suffering among the people you serve, family breakdown'),
        ('You are also uniquely positioned for global influence. Uganda has given the world remarkable Christian leaders, preachers, and evangelists. Ugandan missionaries serve across Africa and beyond. Ugandan churches are sending churches.',
         'You are also positioned for influence far beyond your own walls. Across the world, churches once on the receiving end of mission have become sending churches, raising up remarkable leaders, preachers, and evangelists — and the churches of Africa are among the most vigorous of them.'),
        ('A Charge to the Pastors and Teachers of Uganda',
         'A Charge to Pastors and Teachers Everywhere'),
        ('Intercede for Uganda and the Nations',
         'Intercede for Your Nation and the Nations'),
        ('Pray for Uganda — for its leaders, its families, its schools, its churches, its missionaries.',
         'Pray for your own nation — for its leaders, its families, its schools, its churches, its missionaries.'),
        ('Pray for Africa. Pray for the unreached peoples',
         'Pray for your continent. Pray for the unreached peoples'),
    ],
}


def forwards(apps, schema_editor):
    from library.text import html_to_text, word_count

    Chapter = apps.get_model("library", "Chapter")
    for (slug, order), pairs in CHAPTER_EDITS.items():
        ch = (
            Chapter.objects.filter(
                book__slug=slug, book__language="en", order=order
            )
            .only("id", "body_html")
            .first()
        )
        if ch is None:
            # Fresh DB: the fixture (loaded after migrate) already carries the
            # settled text, so there is nothing to transform here.
            continue
        html = ch.body_html
        changed = False
        for old, new in pairs:
            if old in html:
                html = html.replace(old, new)
                changed = True
        if not changed:
            # Already globalized (idempotent re-run, or a fresh row seeded from
            # the new fixture).
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
        ("library", "0145_topic_qa"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
