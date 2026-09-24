<script lang="ts">
	import { onMount } from 'svelte';
	import { authorPath } from '$lib/originals';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { localizeHref } from '$lib/href';
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { theme } from '$lib/theme.svelte';
	import { lang, localeName } from '$lib/lang.svelte';
	import {
		readerPrefs,
		fontLabel,
		FONT_STACK,
		MEASURE,
		READER_FONTS,
		type ReaderFont,
		type Measure
	} from '$lib/readerPrefs.svelte';
	import { siteFont, SITE_FONTS, type SiteFont } from '$lib/siteFont.svelte';
	import { listen, RATE_MIN, RATE_MAX } from '$lib/listen.svelte';
	import { readingSync } from '$lib/readingSync';
	import { SITE_URL } from '$lib/config';
	import { collectExport, toMarkdown, downloadFile } from '$lib/dataExport';
	import { collectReadingActivity, type ReadingStats, type HistoryItem } from '$lib/readingStats';
	import { readingActivity } from '$lib/readingActivity.svelte';
	import { readingGoal } from '$lib/readingGoal.svelte';
	import { offlineBooks } from '$lib/offlineBooks.svelte';
	import { currentStreak, longestStreak, localToday } from '$lib/streak';
	import { weekReadCount } from '$lib/heatmap';
	import ReadingHeatmap from '$lib/components/ReadingHeatmap.svelte';
	import StatTiles from '$lib/components/StatTiles.svelte';
	import { buildReminderICS } from '$lib/reminder';
	import { relativeTime } from '$lib/relativeTime';
	import Icon, { type IconName } from '$lib/components/Icon.svelte';

	const t = i18n.t;

	type Section = 'profile' | 'reading' | 'appearance' | 'activity';
	const SECTIONS: { id: Section; label: string; icon: IconName }[] = [
		{ id: 'profile', label: t('settings.navProfile'), icon: 'users' },
		{ id: 'reading', label: t('settings.navReading'), icon: 'book' },
		{ id: 'appearance', label: t('settings.navAppearance'), icon: 'sun' },
		{ id: 'activity', label: t('settings.navActivity'), icon: 'compass' }
	];
	// The active section lives in the URL (?section=…) so it survives the full
	// reload a language change triggers, and so it's shareable/back-navigable.
	const isSection = (s: string | null): s is Section =>
		s === 'profile' || s === 'reading' || s === 'appearance' || s === 'activity';
	const initial = $page.url.searchParams.get('section');
	let section = $state<Section>(isSection(initial) ? initial : 'profile');

	function selectSection(id: Section) {
		section = id;
		const url = new URL($page.url);
		url.searchParams.set('section', id);
		goto(url, { replaceState: true, keepFocus: true, noScroll: true });
	}

	const FONTS = READER_FONTS.map((id) => ({
		id,
		label: fontLabel(id, {
			serif: t('settings.fontSerif'),
			sans: t('settings.fontSans'),
			dyslexic: t('settings.fontDyslexic')
		})
	}));
	const SITE_FONT_LABEL: Record<SiteFont, string> = {
		house: t('settings.siteFontHouse'),
		classic: t('settings.siteFontClassic'),
		hyperlegible: t('settings.siteFontHyperlegible')
	};
	const WIDTHS = Object.keys(MEASURE) as Measure[];

	// Export my data — assemble the bundle (fetches catalogs for titles) then hand
	// the reader a JSON or Markdown file. Device-local; works signed in or out.
	let exporting = $state<'json' | 'md' | null>(null);
	async function exportData(format: 'json' | 'md') {
		if (exporting) return;
		exporting = format;
		try {
			const bundle = await collectExport(lang.current, new Date().toISOString());
			if (format === 'json') {
				downloadFile('ochorus-data.json', 'application/json', JSON.stringify(bundle, null, 2));
			} else {
				downloadFile('ochorus-reading.md', 'text/markdown;charset=utf-8', toMarkdown(bundle));
			}
		} finally {
			exporting = null;
		}
	}

	// Display name — editable profile field. Seeded from the profile until the
	// reader edits it (nameDirty), so a late profile load can't clobber typing.
	let nameInput = $state(auth.displayName);
	let nameDirty = $state(false);
	let nameSaving = $state(false);
	$effect(() => {
		if (!nameDirty) nameInput = auth.displayName;
	});
	const nameChanged = $derived(nameInput.trim() !== auth.displayName);
	async function saveName() {
		if (nameSaving || !nameChanged) return;
		nameSaving = true;
		try {
			await auth.setDisplayName(nameInput);
			nameDirty = false;
		} finally {
			nameSaving = false;
		}
	}

	// Sync visibility — surface the otherwise-invisible cross-device sync: when it
	// last succeeded and a manual "Sync now". `syncTick` re-reads the timestamp
	// after a sync and on the 'ochorus:sync' event a merge/pull dispatches.
	let syncing = $state(false);
	let syncTick = $state(0);
	const lastSynced = $derived.by(() => {
		syncTick; // reactive dependency
		return readingSync.readLastSynced();
	});
	// Localised relative time ("just now", "3 minutes ago", "yesterday").
	const relSynced = $derived.by(() => {
		syncTick; // re-evaluate after a manual sync / cache event
		const ts = lastSynced;
		return ts ? relativeTime(ts, lang.current, t('settings.syncJustNow')) : t('settings.syncNever');
	});
	async function syncNow() {
		if (syncing) return;
		syncing = true;
		try {
			await readingSync.syncNow();
		} finally {
			syncing = false;
			syncTick += 1;
		}
	}
	onMount(() => {
		const bump = () => (syncTick += 1);
		window.addEventListener('ochorus:sync', bump);
		return () => window.removeEventListener('ochorus:sync', bump);
	});

	// "Your reading" — stats + recent history, loaded when the section is first
	// opened (it fetches the catalogs to resolve titles) and refreshed on sync.
	let stats = $state<ReadingStats | null>(null);
	let history = $state<HistoryItem[]>([]);
	async function loadActivity() {
		const { stats: s, history: h } = await collectReadingActivity(lang.current);
		stats = s;
		history = h;
	}
	$effect(() => {
		syncTick; // reload after a sync/merge changes the local cache
		if (section === 'activity') loadActivity();
	});
	// Reading streak — derived from the synced activity log (see readingActivity).
	const activityDays = $derived(readingActivity.days());
	const streak = $derived(currentStreak(activityDays, localToday()));
	const longest = $derived(longestStreak(activityDays));
	// Weekly goal — the target lives in readingGoal (a device preference); progress
	// is this week's read-day count from the same activity log.
	const weekCount = $derived(weekReadCount(activityDays, localToday()));
	const goal = $derived(readingGoal.perWeek);
	const goalMet = $derived(weekCount >= goal);

	// Books saved for offline (manage / remove).
	const offlineList = $derived(offlineBooks.list());

	// Resume link for a history row (books deep-link to the chapter).
	const historyHref = (h: HistoryItem) =>
		h.kind === 'sermon'
			? localizeHref(`/sermons/${h.slug}`)
			: h.kind === 'bio'
				? localizeHref(authorPath(h.slug))
				: localizeHref(`/books/${h.slug}/${h.order}`);

	// Daily reminder — a time the reader picks, emitted as a repeating .ics event
	// they add to their own calendar (no server, works on every device).
	const REMINDER_KEY = 'ochorus:reminder-time';
	let reminderTime = $state('07:00');
	onMount(() => {
		const saved = localStorage.getItem(REMINDER_KEY);
		if (saved && /^\d{2}:\d{2}$/.test(saved)) reminderTime = saved;
	});
	function addReminder() {
		try {
			localStorage.setItem(REMINDER_KEY, reminderTime);
		} catch {
			/* private mode — the picker just won't be remembered */
		}
		const uid = `${crypto.randomUUID?.() ?? Date.now()}@ochorus.com`;
		const ics = buildReminderICS(reminderTime, {
			now: new Date(),
			uid,
			summary: t('settings.reminderSummary'),
			description: `${t('settings.reminderDescription')} ${SITE_URL}`,
			url: SITE_URL
		});
		downloadFile('ochorus-reading-reminder.ics', 'text/calendar;charset=utf-8', ics);
	}

	// Danger zone — destructive actions, each a two-click confirm (no modal).
	let clearConfirm = $state(false);
	let clearTimer: ReturnType<typeof setTimeout>;
	function clearDevice() {
		if (!clearConfirm) {
			clearConfirm = true;
			clearTimeout(clearTimer);
			clearTimer = setTimeout(() => (clearConfirm = false), 4000);
			return;
		}
		clearTimeout(clearTimer);
		clearConfirm = false;
		readingSync.clearDeviceData();
	}
	let deleteConfirm = $state(false);
	let deleteTimer: ReturnType<typeof setTimeout>;
	let deleting = $state(false);
	async function deleteAccount() {
		if (!deleteConfirm) {
			deleteConfirm = true;
			clearTimeout(deleteTimer);
			deleteTimer = setTimeout(() => (deleteConfirm = false), 4000);
			return;
		}
		clearTimeout(deleteTimer);
		deleteConfirm = false;
		deleting = true;
		try {
			if (await auth.deleteAccount()) goto(localizeHref('/'));
		} finally {
			deleting = false;
		}
	}

	// Reset preferences — restore reader comfort + theme to defaults. Two-click
	// (not a modal) so an accidental tap can't wipe a carefully-tuned setup; it
	// only touches preferences, never highlights/notes/reading places.
	let resetConfirm = $state(false);
	let resetTimer: ReturnType<typeof setTimeout>;
	function resetPrefs() {
		if (!resetConfirm) {
			resetConfirm = true;
			clearTimeout(resetTimer);
			resetTimer = setTimeout(() => (resetConfirm = false), 4000);
			return;
		}
		clearTimeout(resetTimer);
		resetConfirm = false;
		readerPrefs.reset();
		theme.set('system');
		siteFont.set('house');
	}

	// The device's TTS voices load asynchronously; init the store so they populate,
	// then show only the best few for the currently-selected language.
	onMount(() => listen.init());
	const voices = $derived(listen.supported ? listen.topVoices(lang.current, 4) : []);
	// If the saved voice isn't among this language's picks, fall back to the
	// first — topVoices leads with the language default (Google UK English Male
	// for English), so voices[0] is that default.
	const voiceValue = $derived(
		voices.some((v) => v.voiceURI === listen.voiceURI) ? listen.voiceURI : (voices[0]?.voiceURI ?? '')
	);

	// The speed slider mirrors this draft while dragging and only APPLIES on
	// release (onchange) — so tuning speed mid-listen doesn't restart the utterance
	// (cancel+speak) and rewrite localStorage on every drag tick. Kept in sync when
	// the rate changes elsewhere (e.g. the Listen bar's cycle button).
	let speedDraft = $state(listen.rate);
	$effect(() => {
		speedDraft = listen.rate;
	});
</script>

<svelte:head><title>{t('settings.title')} — Ochorus</title>
	<!-- A private, client-only utility page (ssr=false). robots.txt Disallows
	     /settings; this is the backstop for crawlers that reach it via a link
	     or ignore robots.txt, matching /login, /notebook and /reset-password. -->
	<meta name="robots" content="noindex" /></svelte:head>

<div class="page-col px-5 py-10">
	<header class="mb-8">
		<h1 class="text-h1 mb-2">{t('settings.title')}</h1>
		<p class="text-body text-muted">{t('settings.subtitle')}</p>
	</header>

	<div class="flex flex-col gap-6 sm:flex-row">
		<!-- Sidebar -->
		<nav class="flex shrink-0 gap-1 overflow-x-auto sm:w-48 sm:flex-col sm:overflow-visible" aria-label={t('settings.title')}>
			{#each SECTIONS as s (s.id)}
				<button
					class="flex items-center gap-2.5 whitespace-nowrap rounded-card px-4 py-2.5 text-small font-medium transition-colors"
					class:active-nav={section === s.id}
					class:text-muted={section !== s.id}
					aria-current={section === s.id ? 'page' : undefined}
					onclick={() => selectSection(s.id)}
				>
					<Icon name={s.icon} size={18} />{s.label}
				</button>
			{/each}
		</nav>

		<!-- Panel -->
		<section class="min-w-0 flex-1 rounded-card border border-border bg-surface p-6 sm:p-8">
			{#if section === 'profile'}
				<h2 class="text-h2 mb-1">{t('settings.profileTitle')}</h2>
				<p class="mb-6 text-small text-muted">{t('settings.profileSubtitle')}</p>
				{#if auth.user}
					<p class="text-body text-muted">
						{t('account.signedInAs')}
						<span class="font-semibold text-text">{auth.displayName || auth.user.email}</span>
					</p>
					{#if auth.displayName}
						<p class="text-small text-muted">{auth.user.email}</p>
					{/if}

					<!-- Display name -->
					<div class="mt-5">
						<label class="setting-label mb-1 block" for="displayName">{t('settings.displayName')}</label>
						<div class="flex flex-wrap items-center gap-2">
							<input
								id="displayName"
								class="field max-w-48 flex-1"
								bind:value={nameInput}
								oninput={() => (nameDirty = true)}
								placeholder={t('settings.displayNamePlaceholder')}
								maxlength="120"
								autocomplete="name"
							/>
							<button class="btn btn-sm btn-ghost" disabled={nameSaving || !nameChanged} onclick={saveName}>
								{nameSaving ? t('settings.saving') : t('settings.save')}
							</button>
						</div>
					</div>

					<p class="mt-5 text-small text-muted">{t('settings.syncWhat')}</p>
					<div class="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2">
						<span class="text-small text-muted">
							{t('settings.lastSynced')}: <span class="text-text">{relSynced}</span>
						</span>
						<button class="btn btn-sm btn-ghost" disabled={syncing} onclick={syncNow}>
							{syncing ? t('settings.syncing') : t('settings.syncNow')}
						</button>
					</div>
					<button class="btn btn-ghost mt-5" onclick={() => auth.signOut()}>{t('account.signOut')}</button>
				{:else if auth.enabled}
					<p class="text-body text-muted">{t('account.signedOutNote')}</p>
				{:else}
					<p class="text-body text-muted">{t('account.localNote')}</p>
				{/if}

				<!-- Export my data — the reader's own devotional record, portable. -->
				<div class="mt-8 border-t border-border pt-6">
					<div class="setting-label">{t('settings.exportTitle')}</div>
					<div class="setting-sub mb-4">{t('settings.exportSub')}</div>
					<div class="flex flex-wrap gap-3">
						<button class="btn btn-ghost" disabled={!!exporting} onclick={() => exportData('md')}>
							{exporting === 'md' ? t('settings.exportBusy') : t('settings.exportMarkdown')}
						</button>
						<button class="btn btn-ghost" disabled={!!exporting} onclick={() => exportData('json')}>
							{exporting === 'json' ? t('settings.exportBusy') : t('settings.exportJson')}
						</button>
					</div>
				</div>

				<!-- Danger zone — destructive, two-click confirm each. -->
				<div class="mt-8 rounded-card border border-danger/40 p-5">
					<div class="mb-4 text-small font-semibold text-danger">{t('settings.dangerZone')}</div>

					<div class="setting-label">{t('settings.clearDevice')}</div>
					<div class="setting-sub mb-3">
						{t('settings.clearDeviceSub')}{#if auth.user}{' '}{t('settings.clearDeviceSyncNote')}{/if}
					</div>
					<button class="btn btn-ghost" class:text-danger={clearConfirm} onclick={clearDevice}>
						{clearConfirm ? t('settings.resetConfirm') : t('settings.clearDeviceButton')}
					</button>

					{#if auth.user}
						<div class="mt-6 border-t border-border pt-5">
							<div class="setting-label">{t('settings.deleteAccount')}</div>
							<div class="setting-sub mb-3">{t('settings.deleteAccountSub')}</div>
							<button
								class="btn btn-ghost text-danger"
								class:font-semibold={deleteConfirm}
								disabled={deleting}
								onclick={deleteAccount}
							>
								{deleteConfirm ? t('settings.resetConfirm') : t('settings.deleteAccountButton')}
							</button>
						</div>
					{/if}
				</div>
			{:else if section === 'reading'}
				<h2 class="text-h2 mb-1">{t('settings.navReading')}</h2>
				<p class="mb-6 text-small text-muted">{t('settings.readingSubtitle')}</p>

				<!-- Language -->
				{#if lang.available.length > 1}
					<div class="setting-row">
						<div>
							<div class="setting-label">{t('nav.language')}</div>
							<div class="setting-sub">{t('settings.languageSub')}</div>
						</div>
						<select
							class="field max-w-48"
							aria-label={t('nav.language')}
							value={lang.current}
							onchange={(e) => lang.choose((e.currentTarget as HTMLSelectElement).value)}
						>
							{#each lang.available as l (l.code)}
								<option value={l.code}>{l.native_name}</option>
							{/each}
						</select>
					</div>
				{/if}

				<!-- Reading width -->
				<div class="setting-row">
					<div>
						<div class="setting-label">{t('nav.readingWidth')}</div>
						<div class="setting-sub">{t('settings.readingWidthSub')}</div>
					</div>
					<div class="seg">
						{#each WIDTHS as w (w)}
							<button class:active={readerPrefs.measure === w} onclick={() => readerPrefs.setMeasure(w)}>
								{t(`settings.width_${w}`)}
							</button>
						{/each}
					</div>
				</div>

				<!-- Text size — mirrors the reader's Aa stepper (same readerPrefs.scale). -->
				<div class="setting-row">
					<div>
						<div class="setting-label">{t('settings.textSize')}</div>
						<div class="setting-sub">{t('settings.textSizeSub')}</div>
					</div>
					<div class="flex items-center gap-1">
						<button
							class="btn btn-sm btn-ghost"
							onclick={() => readerPrefs.bumpScale(-0.1)}
							aria-label={t('a11y.smallerText')}>A−</button
						>
						<span class="w-12 text-center text-small text-muted">{Math.round(readerPrefs.scale * 100)}%</span>
						<button
							class="btn btn-sm btn-ghost text-body"
							onclick={() => readerPrefs.bumpScale(0.1)}
							aria-label={t('a11y.largerText')}>A+</button
						>
					</div>
				</div>

				<!-- Daily reminder — downloads a repeating .ics calendar event. -->
				<div class="setting-row">
					<div>
						<div class="setting-label">{t('settings.reminder')}</div>
						<div class="setting-sub">{t('settings.reminderSub')}</div>
					</div>
					<div class="flex items-center gap-2">
						<input
							type="time"
							class="field max-w-48"
							bind:value={reminderTime}
							aria-label={t('settings.reminder')}
						/>
						<button class="btn btn-sm btn-ghost whitespace-nowrap" onclick={addReminder}>
							{t('settings.reminderAdd')}
						</button>
					</div>
				</div>

				<!-- Default edition — carry the preference into the book page read CTAs. -->
				<div class="setting-row">
					<div>
						<div class="setting-label">{t('settings.defaultEdition')}</div>
						<div class="setting-sub">{t('settings.defaultEditionSub')}</div>
					</div>
					<div class="seg">
						<button class:active={!readerPrefs.preferModern} onclick={() => readerPrefs.setPreferModern(false)}>
							{t('reader.original')}
						</button>
						<button class:active={readerPrefs.preferModern} onclick={() => readerPrefs.setPreferModern(true)}>
							{t('reader.modern')}
						</button>
					</div>
				</div>

				<!-- Listen: voice + speed -->
				<div class="setting-row">
					<div>
						<div class="setting-label">{t('settings.voice')}</div>
						<div class="setting-sub">{t('settings.voiceSub')}</div>
					</div>
					{#if !listen.supported}
						<span class="text-small text-muted">{t('settings.voiceUnsupported')}</span>
					{:else if voices.length}
						<div class="flex items-center gap-2">
							<select
								class="field max-w-48"
								aria-label={t('settings.voice')}
								value={voiceValue}
								onchange={(e) => listen.setVoice((e.currentTarget as HTMLSelectElement).value)}
							>
								{#each voices as v (v.voiceURI)}
									<option value={v.voiceURI}>{v.name}</option>
								{/each}
							</select>
							<button
								class="btn btn-sm btn-ghost"
								aria-label={t('settings.preview')}
								title={t('settings.preview')}
								onclick={() => listen.preview(t('settings.voiceSample'), voiceValue)}
							>
								<Icon name="play" size={14} />
							</button>
						</div>
					{:else}
						<span class="text-small text-muted">{t('settings.voiceNone')}</span>
					{/if}
				</div>
				{#if listen.supported && voices.length}
					<div class="setting-row">
						<div>
							<div class="setting-label">{t('settings.speed')}</div>
							<div class="setting-sub">{t('settings.speedSub')}</div>
						</div>
						<div class="flex items-center gap-3">
							<input
								class="speed-range"
								type="range"
								min={RATE_MIN}
								max={RATE_MAX}
								step="0.05"
								bind:value={speedDraft}
								onchange={() => listen.setRate(speedDraft)}
								aria-label={t('settings.speed')}
							/>
							<span class="min-w-11 text-end tabular-nums text-small">{speedDraft}×</span>
						</div>
					</div>
				{/if}
			{:else if section === 'appearance'}
				<h2 class="text-h2 mb-1">{t('settings.navAppearance')}</h2>
				<p class="mb-6 text-small text-muted">{t('settings.appearanceSubtitle')}</p>

				<!-- Theme — preference (not the resolved theme): 'System' follows the OS. -->
				<div class="setting-row">
					<div>
						<div class="setting-label">{t('nav.theme')}</div>
						<div class="setting-sub">{t('settings.themeSub')}</div>
					</div>
					<div class="seg">
						<button class:active={theme.preference === 'system'} onclick={() => theme.set('system')}>{t('settings.themeSystem')}</button>
						<button class:active={theme.preference === 'light'} onclick={() => theme.set('light')}>{t('settings.themeLight')}</button>
						<button class:active={theme.preference === 'sepia'} onclick={() => theme.set('sepia')}>{t('settings.themeSepia')}</button>
						<button class:active={theme.preference === 'dark'} onclick={() => theme.set('dark')}>{t('settings.themeDark')}</button>
					</div>
				</div>

				<!-- Site style — the interface's typeface, not the book text's. -->
				<div class="setting-row">
					<div>
						<div class="setting-label">{t('settings.siteFont')}</div>
						<div class="setting-sub">{t('settings.siteFontSub')}</div>
					</div>
					<div class="seg">
						{#each SITE_FONTS as f (f)}
							<button class:active={siteFont.current === f} onclick={() => siteFont.set(f)}
								>{SITE_FONT_LABEL[f]}</button
							>
						{/each}
					</div>
				</div>

				<!-- Reading font -->
				<div class="setting-row">
					<div>
						<div class="setting-label">{t('settings.font')}</div>
						<div class="setting-sub">{t('settings.fontSub')}</div>
					</div>
					<select
						class="field max-w-48"
						aria-label={t('settings.font')}
						value={readerPrefs.font}
						onchange={(e) => readerPrefs.setFont((e.currentTarget as HTMLSelectElement).value as ReaderFont)}
					>
						{#each FONTS as f (f.id)}
							<option value={f.id}>{f.label}</option>
						{/each}
					</select>
				</div>
				<p class="pt-1 text-body text-text" style="font-family: {FONT_STACK[readerPrefs.font]}">
					{t('settings.fontSample')}
				</p>

				<!-- Reset preferences (theme + reader comfort; not reading data). -->
				<div class="mt-8 border-t border-border pt-6">
					<div class="setting-label">{t('settings.resetPrefs')}</div>
					<div class="setting-sub mb-4">{t('settings.resetPrefsSub')}</div>
					<button class="btn btn-ghost" class:text-danger={resetConfirm} onclick={resetPrefs}>
						{resetConfirm ? t('settings.resetConfirm') : t('settings.resetPrefsButton')}
					</button>
				</div>
			{:else if section === 'activity'}
				<h2 class="text-h2 mb-1">{t('settings.activityTitle')}</h2>
				<p class="mb-6 text-small text-muted">{t('settings.activitySubtitle')}</p>

				{#if stats}
					{#if activityDays.length}
						<!-- Reading streak -->
						<div class="mb-6 flex items-center gap-4 rounded-card border border-border bg-surface-2 px-5 py-4">
							<span class="text-gold"><Icon name="flame" size={30} /></span>
							<div>
								{#if streak > 0}
									<div class="text-text">
										<span class="font-display text-h1 font-semibold">{streak}</span>
										<span class="ms-1 text-body">{t('settings.streakLabel')}</span>
									</div>
								{:else}
									<div class="text-body text-text">{t('settings.streakNone')}</div>
								{/if}
								<div class="mt-0.5 text-small text-muted">
									{t('settings.streakLongest')} {longest} · {activityDays.length} {t('settings.streakDaysRead')}
								</div>
							</div>
						</div>

						<!-- Weekly goal -->
						<div class="mb-6 rounded-card border border-border bg-surface-2 px-5 py-4">
							<div class="flex items-center justify-between gap-3">
								<div>
									<div class="text-body text-text">{t('settings.goalTitle')}</div>
									<div class="mt-0.5 text-small text-muted">
										{#if goalMet}
											{t('settings.goalMet')}
										{:else}
											{weekCount} {t('settings.goalOf')} {goal} {t('settings.goalDaysThisWeek')}
										{/if}
									</div>
								</div>
								<label class="flex items-center gap-2 text-small text-muted">
									{t('settings.goalPerWeek')}
									<select
										class="field max-w-48"
										value={goal}
										onchange={(e) => readingGoal.set(+e.currentTarget.value)}
									>
										{#each [1, 2, 3, 4, 5, 6, 7] as n (n)}<option value={n}>{n}</option>{/each}
									</select>
								</label>
							</div>
							<!-- One pip per goal day, filled up to this week's read-day count. -->
							<div class="mt-3 flex gap-1.5">
								{#each Array(goal) as _, i (i)}
									<span class="h-2 flex-1 rounded-full {i < weekCount ? 'bg-gold' : 'bg-border'}"></span>
								{/each}
							</div>
						</div>

						<!-- Reading calendar (contribution-style heatmap) -->
						<h3 class="text-h3 mb-3">{t('settings.heatmapTitle')}</h3>
						<div class="mb-2">
							<ReadingHeatmap days={activityDays} today={localToday()} locale={lang.current} />
						</div>
					{/if}

					<!-- Stat tiles -->
					{#if stats}
						<StatTiles {stats} />
					{/if}

					<!-- Recently reading -->
					<h3 class="text-h3 mb-3 mt-8">{t('settings.recentReading')}</h3>
					{#if history.length}
						<ol class="divide-y divide-border">
							{#each history as h (h.kind + ':' + h.slug)}
								<li>
									<a href={historyHref(h)} class="flex items-baseline gap-3 py-2.5 hover:no-underline">
										<span class="flex-1 min-w-0">
											<span class="block truncate text-body text-text">{h.title}</span>
											<span class="block truncate text-small text-muted">
												{#if h.author}{h.author}{/if}{#if h.kind === 'book'} · {t('settings.chapterN')} {h.order}{/if}{#if h.finished} · {t('settings.statFinished')}{/if}
											</span>
										</span>
										<span class="shrink-0 text-small text-muted">{relativeTime(h.at, lang.current, t('settings.syncJustNow'))}</span>
									</a>
								</li>
							{/each}
						</ol>
					{:else}
						<p class="text-body text-muted">{t('settings.activityEmpty')}</p>
					{/if}
				{:else}
					<p class="text-small text-muted">…</p>
				{/if}

				{#if offlineList.length}
					<h3 class="text-h3 mb-3 mt-8">{t('settings.downloadsTitle')}</h3>
					<ol class="divide-y divide-border">
						{#each offlineList as b (`${b.slug}:${b.language}`)}
							<li class="flex items-baseline gap-3 py-2.5">
								<a href={localizeHref(`/books/${b.slug}`)} class="min-w-0 flex-1 hover:no-underline">
									<span class="block truncate text-body text-text">{b.title}</span>
									<!-- The language is named because a book downloaded in two of
									     them is now two rows, and without it they read as duplicates. -->
									<span class="block truncate text-small text-muted">
										{#if b.author}{b.author} · {/if}{localeName(b.language)} · {b.chapterCount}
										{t('settings.downloadsChapters')}
									</span>
								</a>
								<button
									class="shrink-0 text-small text-muted hover:text-danger"
									onclick={() => offlineBooks.remove(b.slug, b.language)}
								>
									{t('offline.remove')}
								</button>
							</li>
						{/each}
					</ol>
				{/if}
			{/if}
		</section>
	</div>
</div>

<style>
	.active-nav {
		background: var(--color-accent-soft);
		color: var(--color-accent);
	}
	.setting-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 0.9rem 0;
		border-top: 1px solid var(--color-border);
	}
	/* The label wraps; the control must not shrink. Flex shrinks both, and
	   `.seg` clips (overflow: hidden), so a long sub-line cut off the last
	   segment's label rather than wrapping itself. */
	.setting-row > .seg {
		flex-shrink: 0;
	}
	.setting-row:first-of-type {
		border-top: none;
		padding-top: 0;
	}
	.setting-label {
		font-weight: 600;
		color: var(--color-text);
	}
	.setting-sub {
		font-size: var(--fs-small);
		color: var(--color-muted);
		margin-top: 0.1rem;
	}
	/* `.seg` is the shared segmented control from app.css — no scoped copy here
	   (E1). On a narrow viewport the flush control can't share a row with its
	   label (the 4-option Reading width / Theme segs overflow, and more so in
	   longer-label locales), so the row stacks and the control spans the width
	   with equal segments — layout only (width/flex), not a fork of its look. */
	@media (max-width: 639.98px) {
		.setting-row {
			flex-direction: column;
			align-items: stretch;
			gap: 0.5rem;
		}
		.setting-row .seg {
			width: 100%;
		}
		.setting-row .seg button {
			flex: 1;
		}
	}
	/* Native range, themed via accent-color — thumb and filled track pick up the
	   brand accent in both light and dark with no per-browser pseudo-elements. */
	.speed-range {
		accent-color: var(--color-accent);
		inline-size: 9rem;
		max-inline-size: 55vw;
		cursor: pointer;
	}
</style>
