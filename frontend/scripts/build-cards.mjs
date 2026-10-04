/**
 * Run every share-card script over the build — the `postbuild` step after
 * build-404.
 *
 *     node scripts/build-cards.mjs [buildDir]    # default ./build
 *
 * By default, one after another in the order they have always run. With
 * PARALLEL_CARDS=1 (CI sets it), as three lanes at once — the order inside a
 * lane is the only order that matters:
 *
 *   share → plan     the plan card's shelf is made of the share cards'
 *                    `/og/covers/` files, and skips any not written yet
 *   verse            reads only the built pages and the static `/covers/`
 *   author → quote   likewise; kept in their old order
 *
 * Each script writes its own `/og/` paths, so the lanes never touch the same
 * file, and the cards come out byte-identical either way (all 3,470, compared
 * 2026-10-04). Each script already keeps 3–5 cores busy, so the gain depends on
 * the machine: 35 s -> 21 s on a 10-core Mac. Production keeps the sequential
 * default — whether the Render build machine has the memory for three
 * image-heavy processes at once is a decision about that machine.
 *
 * A script never fails the build over a card (runAsScript turns that into a
 * warning), so a non-zero exit here is a crash — and it fails the build, as
 * the `&&` chain this replaces did.
 */
import { spawn } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const buildDir = process.argv[2] ?? 'build';

const LANES = [
	['build-share-cards', 'build-plan-cards'],
	['build-verse-cards'],
	['build-author-cards', 'build-quote-cards']
];
/** The order these ran in as a `&&` chain, kept for the sequential default. */
const SEQUENTIAL = [
	'build-share-cards',
	'build-verse-cards',
	'build-author-cards',
	'build-quote-cards',
	'build-plan-cards'
];

function run(script) {
	return new Promise((resolve, reject) => {
		const child = spawn(process.execPath, [join(HERE, `${script}.mjs`), buildDir], {
			stdio: 'inherit'
		});
		child.on('error', reject);
		child.on('exit', (code, signal) =>
			code === 0 ? resolve() : reject(new Error(`${script} exited ${signal ?? code}`))
		);
	});
}

async function inOrder(scripts) {
	for (const script of scripts) await run(script);
}

try {
	if (process.env.PARALLEL_CARDS === '1') await Promise.all(LANES.map(inOrder));
	else await inOrder(SEQUENTIAL);
} catch (err) {
	console.error(`build-cards: ${err.message}`);
	process.exit(1);
}
