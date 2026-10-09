/**
 * Korean particles, stripped from a typed search word so the reader's arrival
 * highlight finds the same words the server matched.
 *
 * Korean writes particles onto the word (은혜를, 은혜는, 은혜의 are all "grace").
 * The server strips one from each typed word and matches the rest as a prefix
 * (`backend/library/fts.py`), so a search for 은혜는 finds a chapter that says
 * 은혜를. The highlight looks for the typed words as substrings; left alone it
 * would look for 은혜는, find nothing, and open that chapter at the top. With
 * the particle off it looks for 은혜, which is inside every form.
 *
 * MUST match `KO_PARTICLES` in fts.py — `tests_search.KoreanParticleParityTests`
 * reads this file and fails if the two sets differ.
 */
export const KO_PARTICLES: readonly string[] = [
	'께서는', '에게는', '에서는', '에서도', '에게서', '으로는', '으로써', '으로서',
	'께서', '에서', '에게', '에는', '에도', '으로', '로써', '로서',
	'까지', '부터', '처럼', '보다', '마다',
	'께', '은', '는', '이', '가', '을', '를', '의', '에', '로', '와', '과'
].sort((a, b) => b.length - a.length);

const HANGUL = /^[가-힣]+$/;

/** `word` without one trailing particle, if two syllables remain (as the server does). */
export function stripParticle(word: string): string {
	if (!HANGUL.test(word)) return word;
	for (const particle of KO_PARTICLES) {
		if (word.endsWith(particle) && word.length - particle.length >= 2) {
			return word.slice(0, -particle.length);
		}
	}
	return word;
}
