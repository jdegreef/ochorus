/**
 * A throwaway API for the web build to prerender against, instead of the live
 * one — OFF unless OCHORUS_BUILD_API=local. See docs/build-without-prod-api.md.
 *
 *     node scripts/local-api.mjs start   # prebuild: seed + serve, then return
 *     node scripts/local-api.mjs stop    # postbuild: shut it down
 *
 * WHY. The prerender crawl is thousands of API requests. Against production
 * that is ochorus-api's 512 MB instance serving the whole site in one burst,
 * and from 2026-11-16 to 11-19 it knocked that instance over and every web
 * deploy failed. CI never had the problem: it builds against an API it seeds
 * itself (.github/workflows/ci.yml, the "real API" job). This is that, for the
 * Render build.
 *
 * WHAT `start` DOES, in order, failing the build at the first error:
 *   1. finds `uv` (or installs a pinned one into the work dir with python3's
 *      pip) and installs ../backend's locked dependencies into its own venv
 *      in the work dir — never ../backend/.venv, a developer's dev env;
 *   2. runs `manage.py release` — the same deploy chain production runs —
 *      against a fresh SQLite file in the work dir;
 *   3. lays production's DB-owned facts over it (`apply_build_facts`): which
 *      languages are live, publish and review state, approved quotes and bios.
 *      OCHORUS_BUILD_FACTS names them: a file, an https URL, or `none`. On
 *      Render it is REQUIRED — without it the build would advertise the repo's
 *      idea of which languages are live, not the admin's — and `none` is the
 *      explicit, eyes-open way past that;
 *   4. starts gunicorn on 127.0.0.1:OCHORUS_BUILD_API_PORT (default 8765) under
 *      a small supervisor that outlives this script (npm runs prebuild, build
 *      and postbuild as separate processes) and kills it after
 *      OCHORUS_BUILD_API_TTL_MIN minutes (default 120) if `stop` never comes —
 *      a failed `vite build` skips postbuild;
 *   5. waits for /api/health/.
 *
 * The backend runs with a CLEAN environment: only PATH/HOME/locale/temp
 * variables pass through, and DATABASE_URL is always the SQLite file. So
 * whatever secrets the web service's environment ever holds, this server
 * cannot reach a real database.
 *
 * The site itself keeps PUBLIC_API_BASE_URL (production): hooks.server.ts moves
 * only the build's network hop here ($lib/buildApi).
 */

import { spawn, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, openSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { localBuildApiOrigin } from '../src/lib/buildApi.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const BACKEND = resolve(HERE, '..', '..', 'backend');
/** The uv the API image builds with (backend/Dockerfile). */
const UV_VERSION = '0.13.7';

const ORIGIN = localBuildApiOrigin(process.env);
const DIR = resolve(process.env.OCHORUS_BUILD_API_DIR || join(tmpdir(), 'ochorus-build-api'));
const VENV = join(DIR, 'venv');
const DB = join(DIR, 'api.sqlite3');
const PIDFILE = join(DIR, 'supervisor.pid');
const LOG = join(DIR, 'api.log');
const ON_RENDER = Boolean(process.env.RENDER);

const die = (what, detail = '') => {
	console.error(`\n✗ local build API: ${what}${detail ? `\n  ${detail}` : ''}\n`);
	console.error('  See docs/build-without-prod-api.md. Unset OCHORUS_BUILD_API to build');
	console.error('  against PUBLIC_API_BASE_URL as before.\n');
	process.exit(1);
};

/** The environment every backend process gets — nothing inherited but the basics. */
function backendEnv() {
	const keep = ['PATH', 'HOME', 'LANG', 'LC_ALL', 'TMPDIR', 'UV_CACHE_DIR', 'UV_PYTHON'];
	const env = Object.fromEntries(keep.filter((k) => process.env[k]).map((k) => [k, process.env[k]]));
	return {
		...env,
		// SQLite, local, debug: exactly what the CI build's API runs with.
		DJANGO_DEBUG: 'true',
		DATABASE_URL: `sqlite:///${DB}`,
		DJANGO_SECRET_KEY: 'local-build-api-only',
		UV_PROJECT_ENVIRONMENT: VENV,
		PYTHONUNBUFFERED: '1'
	};
}

function run(cmd, args, label) {
	const started = Date.now();
	console.log(`• local build API: ${label}…`);
	const r = spawnSync(cmd, args, { cwd: BACKEND, env: backendEnv(), stdio: 'inherit' });
	if (r.error) die(`${label} could not start`, r.error.message);
	if (r.status !== 0) die(`${label} failed (exit ${r.status ?? r.signal})`);
	console.log(`  ${label}: ${Math.round((Date.now() - started) / 1000)}s`);
}

const works = (cmd, args) => {
	const r = spawnSync(cmd, args, { stdio: 'ignore' });
	return !r.error && r.status === 0;
};

/** A uv to install the backend with: PATH's, or a pinned one we install. */
function findUv() {
	if (works('uv', ['--version'])) return 'uv';
	const local = join(DIR, 'uv-tool', 'bin', 'uv');
	if (existsSync(local)) return local;
	const python = ['python3', 'python'].find((p) => works(p, ['--version']));
	if (!python) {
		die(
			'neither uv nor python3 is on this build image',
			'The backend cannot run here. Use the GitHub Actions route in the doc instead.'
		);
	}
	run(python, ['-m', 'venv', join(DIR, 'uv-tool')], 'make a venv for uv');
	run(join(DIR, 'uv-tool', 'bin', 'pip'), ['install', '--quiet', `uv==${UV_VERSION}`], `install uv ${UV_VERSION}`);
	return local;
}

/** The facts file to apply, or null for none. Downloads an https URL first. */
async function factsFile() {
	const raw = (process.env.OCHORUS_BUILD_FACTS || '').trim();
	if (raw.toLowerCase() === 'none') {
		console.warn(
			'! local build API: OCHORUS_BUILD_FACTS=none — the build sees the REPO’s idea of which\n' +
				'  languages are live and what is published/reviewed, not production’s.'
		);
		return null;
	}
	if (!raw) {
		if (ON_RENDER) {
			die(
				'OCHORUS_BUILD_FACTS is unset',
				'Production’s live languages, publish and review state live only in its DB. Point\n' +
					'  this at an export (`manage.py export_build_facts`), or set it to `none` knowingly.'
			);
		}
		console.warn('! local build API: no OCHORUS_BUILD_FACTS — repo defaults only (fine off Render).');
		return null;
	}
	if (!/^https:\/\//.test(raw)) {
		if (!existsSync(raw)) die(`OCHORUS_BUILD_FACTS file not found: ${raw}`);
		return resolve(raw);
	}
	let res;
	try {
		// OCHORUS_BUILD_FACTS_TOKEN, when set, is sent as a bearer token — for an
		// export served behind a shared secret rather than at a signed URL.
		const token = (process.env.OCHORUS_BUILD_FACTS_TOKEN || '').trim();
		res = await fetch(raw, {
			headers: token ? { authorization: `Bearer ${token}` } : {},
			signal: AbortSignal.timeout(60_000)
		});
	} catch (e) {
		die('could not download OCHORUS_BUILD_FACTS', e instanceof Error ? e.message : String(e));
	}
	if (!res.ok) die(`OCHORUS_BUILD_FACTS answered ${res.status}`);
	const out = join(DIR, 'build-facts.json');
	writeFileSync(out, Buffer.from(await res.arrayBuffer()));
	return out;
}

async function waitForHealth(timeoutMs = 90_000) {
	const until = Date.now() + timeoutMs;
	while (Date.now() < until) {
		try {
			const res = await fetch(`${ORIGIN}/api/health/`, { signal: AbortSignal.timeout(5000) });
			if (res.ok) return true;
		} catch {
			// not up yet
		}
		await new Promise((r) => setTimeout(r, 1000));
	}
	return false;
}

async function start() {
	if (!ORIGIN) {
		console.log('• local build API: off — prerendering against PUBLIC_API_BASE_URL');
		return;
	}
	if (!existsSync(join(BACKEND, 'manage.py'))) die(`no backend at ${BACKEND}`);
	mkdirSync(DIR, { recursive: true });
	stopSupervisor(); // a previous build's, if it is somehow still around
	const facts = await factsFile();

	const uv = findUv();
	run(uv, ['sync', '--frozen', '--no-dev'], 'install backend dependencies');
	const python = join(VENV, 'bin', 'python');

	for (const f of [DB, `${DB}-journal`, `${DB}-wal`, `${DB}-shm`]) rmSync(f, { force: true });
	run(python, ['manage.py', 'release'], 'seed from this checkout (manage.py release)');
	run(python, ['manage.py', 'build_bible_store'], 'build the Bible store');
	if (facts) run(python, ['manage.py', 'apply_build_facts', facts], 'apply production facts');

	const out = openSync(LOG, 'a');
	const supervisor = spawn(process.execPath, [fileURLToPath(import.meta.url), 'serve'], {
		detached: true,
		stdio: ['ignore', out, out],
		env: process.env
	});
	supervisor.unref();
	writeFileSync(PIDFILE, String(supervisor.pid));

	if (!(await waitForHealth())) {
		stopSupervisor();
		const tail = existsSync(LOG) ? readFileSync(LOG, 'utf8').split('\n').slice(-30).join('\n') : '';
		die(`the API never answered ${ORIGIN}/api/health/`, tail);
	}
	console.log(`✓ local build API: serving this checkout at ${ORIGIN} (log: ${LOG})`);
}

/** Runs detached: gunicorn as a child, killed on SIGTERM or after the TTL. */
function serve() {
	const workers = process.env.OCHORUS_BUILD_API_WORKERS || '2';
	const ttlMin = Number(process.env.OCHORUS_BUILD_API_TTL_MIN) || 120;
	const port = new URL(ORIGIN).port;
	const child = spawn(
		join(VENV, 'bin', 'gunicorn'),
		[
			'config.wsgi:application',
			'--bind',
			`127.0.0.1:${port}`,
			'--workers',
			workers,
			'--timeout',
			'120'
		],
		{ cwd: BACKEND, env: backendEnv(), stdio: 'inherit' }
	);
	const shutdown = () => child.kill('SIGTERM');
	process.on('SIGTERM', shutdown);
	process.on('SIGINT', shutdown);
	setTimeout(() => {
		console.error(`local build API: TTL of ${ttlMin} min reached — shutting down`);
		shutdown();
	}, ttlMin * 60_000).unref();
	child.on('exit', (code) => process.exit(code ?? 0));
}

function stopSupervisor() {
	if (!existsSync(PIDFILE)) return false;
	const pid = Number(readFileSync(PIDFILE, 'utf8'));
	rmSync(PIDFILE, { force: true });
	try {
		process.kill(pid, 'SIGTERM');
		return true;
	} catch {
		return false; // already gone
	}
}

function stop() {
	if (!ORIGIN) return;
	console.log(
		stopSupervisor() ? '✓ local build API: stopped' : '• local build API: nothing to stop'
	);
}

const cmd = process.argv[2];
if (cmd === 'start') await start();
else if (cmd === 'stop') stop();
else if (cmd === 'serve') serve();
else die(`unknown command ${JSON.stringify(cmd)} (start | stop)`);
