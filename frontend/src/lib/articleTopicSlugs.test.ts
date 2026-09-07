import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

/**
 * Article slugs and topic slugs must be disjoint.
 *
 * `/articles/<slug>/` serves BOTH an article and a topic-filtered shelf under
 * one route: the loader tries the article first and only falls through to the
 * topic on a 404 (see routes/articles/[slug]/+page.ts). That is safe ONLY while
 * the two slug sets never overlap — an article whose slug equalled a topic slug
 * would silently shadow that topic's shelf (article wins), and entries()/the
 * sitemap would dedupe the two into one built page, so the shelf would just
 * vanish with no error. The design leans on "article slugs are long title
 * phrases, topic slugs are short curated labels" — this turns that assumption
 * into a build gate, the way the repo guards every other cross-set assumption.
 *
 * Reads the backend fixtures/seed directly (the same cross-tree approach as
 * renderRoutes.test.ts), so it fails at CI time, before a colliding slug ships.
 */
const REPO = join(process.cwd(), '..');
const ARTICLES_DIR = join(REPO, 'backend', 'library', 'fixtures', 'content', 'articles');
const TOPIC_SEED = join(REPO, 'backend', 'library', 'topic_seed.py');

/** Article slugs: one file per work, `<slug>.<lang>.json`. */
function articleSlugs(): Set<string> {
	const slugs = new Set<string>();
	for (const name of readdirSync(ARTICLES_DIR)) {
		const m = /^(.+)\.[a-z]{2}\.json$/.exec(name);
		if (m) slugs.add(m[1]);
	}
	return slugs;
}

/** Topic slugs: the first string of each tuple in `topic_seed.py`'s TOPICS
 *  list — `("prayer", "On Prayer", …)`. Member dicts (`"prayer": [ … ]`) carry a
 *  colon and don't match this `(slug, title,` shape. */
function topicSlugs(): Set<string> {
	const src = readFileSync(TOPIC_SEED, 'utf-8');
	const slugs = new Set<string>();
	for (const m of src.matchAll(/\(\s*"([a-z0-9-]+)",\s*\n\s*"[^"]+",/g)) slugs.add(m[1]);
	return slugs;
}

describe('article and topic slugs are disjoint', () => {
	it('parses both sets (guards against a broken reader passing vacuously)', () => {
		expect(articleSlugs().size).toBeGreaterThan(20);
		expect(topicSlugs().size).toBeGreaterThanOrEqual(8);
	});

	it('no article slug collides with a topic slug', () => {
		const topics = topicSlugs();
		const collisions = [...articleSlugs()].filter((s) => topics.has(s));
		expect(
			collisions,
			`These slugs are BOTH an article and a topic, so /articles/<slug>/ would ` +
				`serve the article and hide the topic shelf. Rename one side.`
		).toEqual([]);
	});
});
