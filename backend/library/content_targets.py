"""The Language Content Targets: the named set of works every language should
hold, by level.

A readiness threshold (``Language.min_books`` …) asks *how many*. A target asks
*which*: Level 1 is the 255 particular works that make a complete-feeling
library in any language. With a named list a new language can be steered at
it item by item, and two languages can be compared on the same shelf.

Level 1 is chosen to be **closed**:

* every author of a Level 1 book or sermon has a Level 1 biography, so no
  author page in the set is missing its bio (imprints such as Ochorus Originals
  have no biography; ``BIO_EXCEPTIONS`` names the one author still waiting for
  an English bio);
* every Level 1 plan draws only on Level 1 books and articles, because
  ``seed_plans`` builds a plan only in a language that has all of its sources.

``tests_content_targets`` enforces both, along with "every slug is a real
published English row" and "nothing copyright-blocked".

How the set was chosen: the most-read classics first; every stream of the
tradition (fathers, medieval, Reformation, Puritan, revival, holiness,
missions, Pentecostal, 20th century); women and voices from Africa, Asia and
the African-American and Native American churches; and shorter works where
two are otherwise equal. The very long works wait for Level 2.

Levels 2 and 3 are planned, not yet named (Level 3 = the whole translatable
catalogue). Add a level as another ``Level`` in ``LEVELS``; the admin reads
whatever is here.
"""

from __future__ import annotations

from dataclasses import dataclass

# (group label, slugs). Groups only organise the admin list; order within a
# group is the suggested working order.
Groups = tuple[tuple[str, tuple[str, ...]], ...]


@dataclass(frozen=True)
class Level:
    number: int
    name: str
    books: Groups
    sermons: Groups
    bios: Groups
    plans: tuple[str, ...]
    articles: Groups
    # Topic shelves have no English fallback, so the target is all of them.
    all_topics: bool = True

    def slugs(self, kind: str) -> list[str]:
        if kind == "plans":
            return list(self.plans)
        return [s for _, group in getattr(self, kind) for s in group]


LEVEL_1 = Level(
    number=1,
    name="Level 1",
    books=(
        (
            'Start here: the gospel & first steps',
            (
                'all-of-grace',
                'the-way-to-god',
                'a-call-to-the-unconverted',
                'around-the-wicket-gate',
                'how-to-succeed-in-the-christian-life',
                'pilgrims-progress',
                'orthodoxy',
            ),
        ),
        (
            'Prayer',
            (
                'school-of-prayer',
                'the-inner-chamber',
                'power-through-prayer',
                'necessity-of-prayer',
                'purpose-in-prayer',
                'prevailing-prayer',
                'answers-to-prayer',
                'prayer-the-pulse-of-life',
            ),
        ),
        (
            'The deeper life',
            (
                'absolute-surrender',
                'humility-2',
                'waiting-on-god',
                'true-vine',
                'the-practice-of-the-presence-of-god',
                'the-pursuit-of-god',
                'the-christians-secret-of-a-happy-life-4',
                'the-imitation-of-christ',
                'the-secret-of-guidance',
            ),
        ),
        (
            'The Holy Spirit & healing',
            (
                'baptism-with-the-holy-spirit',
                'the-person-and-work-of-the-holy-spirit',
                'divine-healing',
                'ever-increasing-faith',
            ),
        ),
        (
            'Comfort in suffering',
            (
                'the-god-of-all-comfort',
                'all-things-for-good',
                'he-holds-my-tomorrows',
            ),
        ),
        (
            'The great tradition',
            (
                'confessions',
                'on-the-incarnation',
                'epistles-of-ignatius',
                'on-loving-god',
                'pensees',
                'mortification-of-sin',
                'the-bruised-reed',
                'grace-abounding',
            ),
        ),
        (
            'Lives & witness',
            (
                'a-retrospect',
                'religious-experience-and-journal',
                'at-the-masters-feet',
                'tukutendereza',
                'women-who-moved-heaven-2',
                'men-of-prayer-2',
                'men-and-women-who-gave-everything-2',
            ),
        ),
        (
            'Ochorus originals',
            (
                'growing-in-wisdom',
                'clothed-with-strength-and-dignity',
            ),
        ),
        (
            'Children',
            (
                'pilgrims-progress-children',
                'talks-to-the-farmer-children',
                'the-life-of-trust-children',
                'a-retrospect-children',
                'amanda-smith-autobiography-children',
                'the-practice-of-the-presence-of-god-children',
                'brave-for-god',
                'brave-for-god-2',
                'brave-for-god-3',
                'brave-for-god-4',
            ),
        ),
        (
            'Teens',
            (
                'pilgrims-progress-teens',
                'rooted-1',
            ),
        ),
    ),
    # Grouped by preacher.
    sermons=(
        (
            'Charles H. Spurgeon',
            (
                'the-immutability-of-god',
                'christ-precious-to-believers',
                'free-grace',
                'compel-them-to-come-in',
                'christ-crucified',
                'the-golden-key-of-prayer',
                'order-and-argument-in-prayer',
                'songs-in-the-night',
                'the-sweet-uses-of-adversity',
                'the-ravens-cry',
            ),
        ),
        (
            'John Wesley',
            (
                'salvation-by-faith',
                'the-almost-christian',
                'the-circumcision-of-the-heart',
                'the-scripture-way-of-salvation',
                'catholic-spirit',
            ),
        ),
        (
            'George Whitefield',
            (
                'the-method-of-grace',
                'marks-of-a-true-conversion',
                'walking-with-god',
                'the-lord-our-righteousness',
                'intercession-every-christians-duty',
            ),
        ),
        (
            'Jonathan Edwards',
            (
                'sinners-in-the-hands-of-an-angry-god',
                'a-divine-and-supernatural-light',
                'god-glorified-in-mans-dependence',
                'the-excellency-of-christ',
                'the-christian-pilgrim',
            ),
        ),
        (
            'Dwight L. Moody',
            (
                'christs-boundless-compassion',
                'christ-all-in-all',
                'eight-i-wills-of-christ',
                'the-dying-thief',
                'rest',
                'the-new-birth',
            ),
        ),
        (
            'Charles G. Finney',
            (
                'gods-love-for-a-sinning-world',
                'breaking-up-the-fallow-ground',
                'prevailing-prayer',
            ),
        ),
        (
            'A. B. Simpson',
            (
                'himself',
                'the-power-of-stillness',
                'the-possibilities-of-faith',
                'the-joy-of-the-lord',
            ),
        ),
        (
            'Catherine Booth',
            (
                'aggressive-christianity',
                'the-worlds-need',
                'witnessing-for-christ',
                'the-holy-ghost',
            ),
        ),
        (
            'Hudson Taylor',
            (
                'unfailing-springs',
                'blessed-adversity',
                'a-ribband-of-blue',
                'a-full-reward',
            ),
        ),
        (
            'Martin Luther',
            (
                'pauls-praise-of-christian-love',
                'of-christs-resurrection',
                'the-story-of-the-birth-of-jesus',
            ),
        ),
        (
            'John Calvin',
            (
                'enduring-persecution-for-christ',
                'all-scripture-is-given-by-inspiration',
            ),
        ),
        (
            'John Chrysostom',
            (
                'against-eutropius',
                'homily-on-the-paralytic',
            ),
        ),
        (
            'John Newton',
            (
                'behold-the-lamb-of-god',
                'unto-us-a-child-is-born',
                'i-know-that-my-redeemer-liveth',
            ),
        ),
        (
            'Robert Murray M’Cheyne',
            (
                'the-good-way-of-coming-before-the-lord',
                'why-is-god-a-stranger-in-the-land',
            ),
        ),
        (
            'J. C. Ryle',
            (
                'are-you-born-again',
                'christ-is-all',
                'do-you-pray',
            ),
        ),
        (
            'R. A. Torrey',
            (
                'every-mans-need-of-a-refuge',
                'the-greatest-sentence-ever-written',
                'the-way-of-salvation-made-plain',
            ),
        ),
        (
            'Gareth Evans',
            (
                'abiding-in-christ',
                'caleb-a-different-spirit',
                'broken-before-the-throne',
            ),
        ),
        (
            'A. W. Tozer',
            (
                'god-made-man-to-worship',
                'the-infinite-god',
                'how-to-cultivate-the-holy-spirits-companionship',
            ),
        ),
        (
            'Martyn Lloyd-Jones',
            (
                'what-is-revival',
                'the-parable-of-the-prodigal-son',
            ),
        ),
        (
            'Corrie ten Boom',
            (
                'how-to-forgive',
                'the-greatest-of-these-is-love',
            ),
        ),
        (
            'Elisabeth Elliot',
            (
                'i-keep-a-quiet-heart',
                'hearts-set-on-pilgrimage',
            ),
        ),
        (
            'William J. Seymour',
            (
                'river-of-living-water',
                'the-precious-atonement',
            ),
        ),
        (
            'Absalom Jones',
            (
                'thanksgiving-sermon-abolition-of-the-slave-trade',
            ),
        ),
        (
            'Samson Occom',
            (
                'sermon-at-the-execution-of-moses-paul',
            ),
        ),
    ),
    bios=(
        (
            "Authors of Level 1 books and sermons",
            (
                'charles-h-spurgeon',
                'dwight-l-moody',
                'richard-baxter',
                'r-a-torrey',
                'john-bunyan',
                'g-k-chesterton',
                'andrew-murray',
                'e-m-bounds',
                'george-muller',
                'brother-lawrence',
                'a-w-tozer',
                'hannah-whitall-smith',
                'thomas-a-kempis',
                'frederick-brotherton-meyer',
                'smith-wigglesworth',
                'thomas-watson',
                'gareth-evans',
                'augustine-of-hippo',
                'athanasius-of-alexandria',
                'ignatius-of-antioch',
                'bernard-of-clairvaux',
                'blaise-pascal',
                'john-owen',
                'richard-sibbes',
                'hudson-taylor',
                'jarena-lee',
                'sadhu-sundar-singh',
                'amanda-berry-smith',
                'john-wesley',
                'george-whitefield',
                'jonathan-edwards',
                'charles-finney',
                'a-b-simpson',
                'catherine-booth',
                'martin-luther',
                'john-calvin',
                'john-chrysostom',
                'john-newton',
                'robert-murray-mcheyne',
                'j-c-ryle',
                'martyn-lloyd-jones',
                'corrie-ten-boom',
                'elisabeth-elliot',
                'william-j-seymour',
                'absalom-jones',
                'samson-occom',
            ),
        ),
        (
            "Lives that stand on their own",
            (
                'samuel-ajayi-crowther',
                'festo-kivengere',
                'janani-luwum',
                'josephine-bakhita',
                'pandita-ramabai',
                'john-hyde',
                'amy-carmichael',
                'mary-slessor',
                'gladys-aylward',
                'susanna-wesley',
                'watchman-nee',
                'dietrich-bonhoeffer',
                'c-s-lewis',
                'william-carey',
            ),
        ),
    ),
    plans=(
        'grace-for-every-sinner',
        'new-to-the-faith',
        'humility-12-days',
        'school-of-prayer-31-days',
        'the-inner-chamber-month',
        'praying-men',
        'power-from-on-high',
        'faith-in-the-fire',
        'the-puritan-heart',
        'the-pilgrims-way',
        'growing-in-wisdom-18-days',
        'first-steps-for-teens',
        'brave-for-god-24-true-stories',
        'family-devotions-pilgrims-journey',
        'family-devotions-heroes-who-trusted-god',
    ),
    articles=(
        (
            "New to the Faith (the plan's 13 days)",
            (
                'what-is-the-gospel',
                'why-did-jesus-die',
                'what-is-grace',
                'what-is-repentance',
                'what-is-baptism',
                'who-is-the-holy-spirit',
                'what-is-the-church',
                'what-is-the-lords-supper',
                'how-to-read-the-bible-for-beginners',
                'the-morning-watch',
                'how-to-share-your-faith',
                'how-to-overcome-sin-and-temptation',
                'how-to-grow-in-your-faith',
            ),
        ),
        (
            'Big questions',
            (
                'how-to-be-born-again',
                'what-is-faith',
                'what-is-the-trinity',
                'what-is-justification-by-faith',
                'how-to-have-assurance-of-salvation',
                'is-jesus-the-only-way',
                'is-the-bible-reliable',
                'how-do-we-know-jesus-rose',
                'why-would-a-good-god-allow-suffering',
                'how-to-overcome-fear-and-anxiety-with-faith',
                'how-to-forgive-someone-who-hurt-you',
                'how-to-find-comfort-in-grief-and-loss',
            ),
        ),
        (
            'Guides to Level 1 books',
            (
                'pilgrims-progress-guide',
                'all-of-grace-guide',
                'the-way-to-god-guide',
                'augustines-confessions-guide',
                'on-the-incarnation-guide',
                'absolute-surrender-guide',
                'waiting-on-god-guide',
                'true-vine-guide',
                'power-through-prayer-guide',
                'the-imitation-of-christ-guide',
                'the-christians-secret-of-a-happy-life-guide',
                'the-god-of-all-comfort-guide',
                'he-holds-my-tomorrows-guide',
                'mortification-of-sin-guide',
                'the-bruised-reed-guide',
            ),
        ),
    ),
)

LEVELS: tuple[Level, ...] = (LEVEL_1,)

# Authors of Level 1 works who have no English biography yet, so the closure
# rule can't hold for them until one is written. Remove a name once its bio
# lands, and add it to LEVEL_1.bios.
BIO_EXCEPTIONS: frozenset[str] = frozenset({"hannah-buyinza"})

KINDS = ("bios", "books", "sermons", "plans", "articles")
