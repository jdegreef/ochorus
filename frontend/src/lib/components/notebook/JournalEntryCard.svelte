<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import * as m from '$lib/paraglide/messages.js';
	import {
		ANSWER_MAX,
		DAILY_STEPS,
		UPDATE_MAX,
		daysWaited,
		formatRemind,
		parseRemind,
		type JournalEntry
	} from '$lib/journal';
	import { journal } from '$lib/journal.svelte';
	import { auth } from '$lib/auth.svelte';
	import { journalSync } from '$lib/journalSyncState.svelte';
	import { sourceHref } from '$lib/editionHref';
	import { downloadRemindCalendar, remindLabel, weekdayName } from '$lib/prayerRemind';
	import EntryComposer from './EntryComposer.svelte';

	/**
	 * One entry on the Notebook's page. A prayer carries its own "answered"
	 * flow: mark it answered, say how (optional), and it gains the stamp and
	 * the time it was prayed for — the request and the answer stay one entry.
	 */
	let { entry, locale }: { entry: JournalEntry; locale: string } = $props();

	const t = i18n.t;
	/** The daily prayer's movement names, to set them apart in its text. */
	const stepNames = new Set(DAILY_STEPS.map((s) => t(`notebook.step_${s}`)));

	/** What the card is showing: the entry, or one of its editors (never two at once). */
	let mode = $state<'view' | 'edit' | 'answer' | 'update' | 'remind'>('view');
	let answerText = $state('');
	let updateText = $state('');
	let remFreq = $state<'daily' | 'weekly'>('daily');
	let remDay = $state(0);
	let remTime = $state('07:00');

	const weekdays = $derived(Array.from({ length: 7 }, (_, d) => weekdayName(d, locale)));

	function startRemind() {
		const cur = parseRemind(entry.remind);
		remFreq = cur?.freq ?? 'daily';
		remDay = cur?.day ?? 0;
		remTime = cur?.time ?? '07:00';
		mode = 'remind';
	}
	function saveRemind() {
		const r = formatRemind(remFreq, remDay, remTime);
		journal.setRemind(entry.id, r);
		downloadRemindCalendar(entry, r);
		mode = 'view';
	}
	function saveUpdate() {
		journal.addUpdate(entry.id, updateText);
		updateText = '';
		mode = 'view';
	}
	const shortDate = (at: number) =>
		new Date(at).toLocaleDateString(locale, { day: 'numeric', month: 'short' });

	const time = (at: number) =>
		new Date(at).toLocaleTimeString(locale, { hour: 'numeric', minute: '2-digit' });
	const date = (at: number) =>
		new Date(at).toLocaleDateString(locale, { day: 'numeric', month: 'long', year: 'numeric' });

	const waited = $derived(daysWaited(entry));
	const waitedLabel = $derived(
		waited === null
			? ''
			: waited === 0
				? t('notebook.answeredSameDay')
				: waited === 1
					? t('notebook.answeredAfterOneDay')
					: m.notebook_answered_after_days({ n: String(waited) })
	);

	function startAnswer() {
		answerText = entry.answer;
		mode = 'answer';
	}
	function confirmAnswer() {
		journal.setAnswered(entry.id, true, answerText);
		mode = 'view';
	}
</script>

{#if mode === 'edit'}
	<EntryComposer
		editing
		initial={{
			kind: entry.kind,
			title: entry.title,
			body: entry.body,
			ref: entry.ref,
			person: entry.person,
			group: entry.group
		}}
		onsave={(d) => {
			journal.update(entry.id, d);
			mode = 'view';
		}}
		oncancel={() => (mode = 'view')}
	/>
{:else}
	<article id="entry-{entry.id}" class="entry" class:prayer={entry.kind === 'prayer'} class:answered={!!entry.answeredAt}>
		<header class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
			<span class="kind eyebrow">
				{#if entry.kind === 'note'}✎ {t('reader.note')}{:else if entry.kind === 'daily'}☀ {t('notebook.dailyKind')}{:else if entry.answeredAt}✓ {t('notebook.answeredPrayer')}{:else}🙏 {t('notebook.prayer')}{/if}
			</span>
			<time class="text-micro text-muted" datetime={new Date(entry.createdAt).toISOString()}>
				{time(entry.createdAt)}
			</time>
			{#if entry.ref}<span class="ref text-small">{entry.ref}</span>{/if}
			<!-- Where this entry is: only here until the account has it. Signed out,
			     the page says so once instead of on every entry. -->
			{#if auth.enabled && auth.user}
				{#if journalSync.isPending(entry.id)}
					<span class="sync-mark pending text-micro" title={t('notebook.syncEntryPendingHint')}
						><span aria-hidden="true" class="me-1">📱</span>{t('notebook.syncEntryPending')}</span
					>
				{:else}
					<span class="sync-mark text-micro" title={t('notebook.syncEntryDone')} aria-label={t('notebook.syncEntryDone')}
						>☁</span
					>
				{/if}
			{/if}
		</header>

		{#if entry.person || entry.group}
			<p class="for text-small">
				{#if entry.person}{t('notebook.prayingFor')} <strong>{entry.person}</strong>{/if}
				{#if entry.group}<span class="chip-static">{t(`notebook.group_${entry.group}`)}</span>{/if}
			</p>
		{/if}

		{#if entry.source}
			<!-- The passage this was written from, linked back into its own edition. -->
			<a class="source" href={sourceHref(entry.source)}>
				{#if entry.source.quote}<span class="source-quote">“{entry.source.quote}”</span>{/if}
				<span class="source-title text-micro">{entry.source.title} →</span>
			</a>
		{/if}

		{#if entry.title}<h3 class="entry-title">{entry.title}</h3>{/if}
		{#if entry.kind === 'daily'}
			<!-- The daily prayer's movements, each under its name (see composeDaily). -->
			<div class="entry-body">
				{#each entry.body.split('\n') as line, i (i)}
					{#if stepNames.has(line.trim())}<strong class="step-name">{line}</strong>{:else}{line}{/if}{'\n'}
				{/each}
			</div>
		{:else if entry.body}<p class="entry-body">{entry.body}</p>{/if}

		{#if entry.updates.length}
			<ol class="updates">
				{#each entry.updates as u (u.at)}
					<li>
						<time class="text-micro text-muted" datetime={new Date(u.at).toISOString()}>{shortDate(u.at)}</time>
						<span class="text-small text-text">{u.text}</span>
						<button
							class="upd-remove text-micro text-muted"
							onclick={() => journal.removeUpdate(entry.id, u.at)}
							aria-label={t('notebook.delete')}>×</button
						>
					</li>
				{/each}
			</ol>
		{/if}

		{#if entry.remind && !entry.answeredAt}
			<p class="remind text-micro"><span aria-hidden="true" class="me-1">🔔</span>{remindLabel(entry.remind, locale)}</p>
		{/if}

		{#if entry.answeredAt}
			<div class="answer">
				<span class="stamp" aria-hidden="true">{t('notebook.answeredStamp')}</span>
				<p class="text-small font-semibold text-text">
					{date(entry.answeredAt)} · <span class="font-normal text-muted">{waitedLabel}</span>
				</p>
				{#if entry.answer}<p class="entry-body answer-body">{entry.answer}</p>{/if}
			</div>
		{/if}

		{#if mode === 'update'}
			<form
				class="mt-3 flex gap-2"
				onsubmit={(e) => {
					e.preventDefault();
					saveUpdate();
				}}
			>
				<!-- svelte-ignore a11y_autofocus -- opened by the reader's own tap -->
				<input
					class="field grow"
					bind:value={updateText}
					maxlength={UPDATE_MAX}
					placeholder={t('notebook.updatePlaceholder')}
					aria-label={t('notebook.addUpdate')}
					autofocus
				/>
				<button type="button" class="btn btn-ghost btn-sm" onclick={() => (mode = 'view')}>{t('common.cancel')}</button>
				<button type="submit" class="btn btn-primary btn-sm" disabled={!updateText.trim()}>{t('notebook.addUpdate')}</button>
			</form>
		{:else if mode === 'remind'}
			<div class="remind-panel mt-3">
				<p class="mb-2 text-small font-semibold text-text">{t('notebook.remindTitle')}</p>
				<div class="flex flex-wrap items-center gap-2">
					<div class="seg" role="group" aria-label={t('notebook.remindTitle')}>
						<button type="button" class:active={remFreq === 'daily'} aria-pressed={remFreq === 'daily'} onclick={() => (remFreq = 'daily')}>{t('notebook.remindDaily')}</button>
						<button type="button" class:active={remFreq === 'weekly'} aria-pressed={remFreq === 'weekly'} onclick={() => (remFreq = 'weekly')}>{t('notebook.remindWeekly')}</button>
					</div>
					{#if remFreq === 'weekly'}
						<select class="field" bind:value={remDay} aria-label={t('notebook.remindDay')}>
							{#each weekdays as name, d (d)}<option value={d}>{name}</option>{/each}
						</select>
					{/if}
					<input class="field" type="time" bind:value={remTime} aria-label={t('notebook.remindTime')} />
				</div>
				<p class="mt-2 text-micro text-muted">{t('notebook.remindHint')}</p>
				<div class="mt-2 flex flex-wrap justify-end gap-2">
					{#if entry.remind}
						<button
							class="btn btn-ghost btn-sm"
							onclick={() => {
								journal.setRemind(entry.id, '');
								mode = 'view';
							}}>{t('notebook.remindRemove')}</button
						>
					{/if}
					<button class="btn btn-ghost btn-sm" onclick={() => (mode = 'view')}>{t('common.cancel')}</button>
					<button class="btn btn-primary btn-sm" onclick={saveRemind} disabled={!remTime}>{t('notebook.remindSave')}</button>
				</div>
			</div>
		{:else if mode === 'answer'}
			<div class="mt-3">
				<label class="text-small font-semibold text-text" for="ans-{entry.id}">{t('notebook.howAnswered')}</label>
				<textarea
					id="ans-{entry.id}"
					class="field mt-1 w-full"
					rows="3"
					maxlength={ANSWER_MAX}
					bind:value={answerText}
					placeholder={t('notebook.howAnsweredPlaceholder')}
				></textarea>
				<div class="mt-2 flex justify-end gap-2">
					<button class="btn btn-ghost btn-sm" onclick={() => (mode = 'view')}>{t('common.cancel')}</button>
					<button class="btn btn-primary btn-sm" onclick={confirmAnswer}>{t('notebook.markAnswered')}</button>
				</div>
			</div>
		{:else}
			<div class="actions">
				{#if entry.kind === 'prayer' && !entry.answeredAt}
					<button class="btn btn-sm answer-btn" onclick={startAnswer}>✓ {t('notebook.markAnswered')}</button>
					<button class="btn btn-ghost btn-sm" onclick={() => (mode = 'update')}>+ {t('notebook.addUpdate')}</button>
					<button class="btn btn-ghost btn-sm" onclick={startRemind}><span aria-hidden="true" class="me-1">🔔</span>{t('notebook.remindMe')}</button>
				{:else if entry.answeredAt}
					<button class="btn btn-ghost btn-sm" onclick={startAnswer}>{t('notebook.editAnswer')}</button>
					<button class="btn btn-ghost btn-sm" onclick={() => journal.setAnswered(entry.id, false)}>
						{t('notebook.stillPraying')}
					</button>
				{/if}
				<button class="btn btn-ghost btn-sm" onclick={() => (mode = 'edit')}>{t('notebook.edit')}</button>
				<button class="btn btn-ghost btn-sm" onclick={() => journal.remove(entry.id)}>{t('notebook.delete')}</button>
			</div>
		{/if}
	</article>
{/if}

<style>
	.entry {
		--rule-gap: 2rem;
		/* Arriving from an "On this day" link: clear the sticky header. */
		scroll-margin-top: 5rem;
		/* Green ink pulled toward the text colour: darker on paper, lighter in
		   lamplight, so small "answered" text keeps its contrast in every theme. */
		--answered-ink: color-mix(in srgb, var(--hl-green) 65%, var(--text));
		position: relative;
	}
	.sync-mark {
		margin-inline-start: auto;
		color: var(--muted);
		opacity: 0.7;
	}
	.sync-mark.pending {
		color: var(--warning);
		font-weight: 600;
		opacity: 1;
	}
	.kind {
		color: var(--accent);
	}
	.step-name {
		font-family: var(--font-sans);
		font-size: var(--fs-small);
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: var(--warning);
	}
	.prayer .kind {
		color: var(--warning);
	}
	.answered .kind {
		color: var(--answered-ink);
	}
	.ref {
		font-family: var(--font-display);
		font-style: italic;
		color: var(--muted);
	}
	.ref::before {
		content: '— ';
	}
	.for {
		margin-top: 0.35rem;
		color: var(--muted);
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem;
	}
	.for strong {
		color: var(--text);
		font-weight: 600;
	}
	.chip-static {
		border: 1px solid var(--accent-soft-border);
		background: var(--accent-soft);
		color: var(--accent);
		border-radius: 999px;
		padding: 0 0.55rem;
		font-size: var(--fs-micro);
		font-weight: 600;
	}
	/* The source passage: a quotation set in from the margin, like one copied
	   into the notebook by hand, with its reference underneath. */
	.source {
		display: block;
		margin-top: 0.6rem;
		padding: 0.35rem 0 0.35rem 0.9rem;
		border-inline-start: 3px solid color-mix(in srgb, var(--gold) 60%, transparent);
		color: inherit;
	}
	.source:hover {
		text-decoration: none;
	}
	.source:hover .source-title {
		text-decoration: underline;
	}
	.source-quote {
		display: block;
		font-family: var(--font-display);
		font-style: italic;
		color: var(--text);
		line-height: 1.6;
	}
	.source-title {
		display: block;
		margin-top: 0.2rem;
		color: var(--accent);
		font-weight: 600;
	}
	.updates {
		margin-top: 0.75rem;
		padding-inline-start: 0.9rem;
		border-inline-start: 1px dashed var(--border-strong);
		display: grid;
		gap: 0.35rem;
	}
	.updates li {
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
	}
	.updates time {
		flex: none;
		min-width: 3.5rem;
	}
	.upd-remove {
		margin-inline-start: auto;
		padding: 0 0.3rem;
		opacity: 0;
		cursor: pointer;
	}
	.updates li:hover .upd-remove,
	.upd-remove:focus-visible {
		opacity: 1;
	}
	.remind {
		margin-top: 0.5rem;
		color: var(--warning);
		font-weight: 600;
	}
	.remind-panel {
		padding: 0.85rem 1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--surface-2);
	}
	.entry-title {
		margin-top: 0.35rem;
		font-size: var(--fs-h3);
		line-height: var(--rule-gap);
	}
	/* The words sit on the page's rules: line-height is the rule gap, and the
	   rules are drawn under the text block itself so they always line up. */
	.entry-body {
		margin-top: 0.25rem;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		font-family: var(--font-display);
		font-size: var(--fs-body);
		line-height: var(--rule-gap);
		color: var(--text);
		background-image: linear-gradient(
			to bottom,
			transparent calc(var(--rule-gap) - 1px),
			color-mix(in srgb, var(--accent) 16%, transparent) calc(var(--rule-gap) - 1px)
		);
		background-size: 100% var(--rule-gap);
	}
	.answer {
		position: relative;
		margin-top: 1rem;
		padding: 0.85rem 1rem;
		border-radius: var(--radius-sm);
		background: color-mix(in srgb, var(--hl-green) 9%, transparent);
		border: 1px solid color-mix(in srgb, var(--hl-green) 30%, transparent);
	}
	.answer-body {
		background-image: none;
		line-height: 1.7;
	}
	/* The rubber stamp: set askew in the corner, like an ink stamp pressed on
	   a page. Decorative — the kind label above already says "Answered". */
	.stamp {
		position: absolute;
		top: -0.9rem;
		inset-inline-end: 0.75rem;
		padding: 0.1rem 0.55rem;
		border: 2px solid var(--answered-ink);
		border-radius: 4px;
		color: var(--answered-ink);
		background: var(--surface);
		font-size: var(--fs-micro);
		font-weight: 800;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		transform: rotate(-6deg);
		opacity: 0.9;
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem;
		margin-top: 0.6rem;
		opacity: 0.75;
		transition: opacity var(--duration-fast) ease;
	}
	.entry:hover .actions,
	.entry:focus-within .actions {
		opacity: 1;
	}
	.answer-btn {
		border: 1px solid color-mix(in srgb, var(--hl-green) 45%, transparent);
		color: var(--answered-ink);
	}
</style>
