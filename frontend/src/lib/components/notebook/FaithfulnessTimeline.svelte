<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import * as m from '$lib/paraglide/messages.js';
	import { daysWaited, type TimelineMonth } from '$lib/journal';

	/**
	 * The faithfulness timeline — every answered prayer on one line, month by
	 * month, newest first: what was asked, for whom, how long it was prayed,
	 * and how it was answered. A record to look back on, so it is read-only;
	 * the "By date" view keeps each prayer's full card for editing.
	 */
	let { months, locale }: { months: TimelineMonth[]; locale: string } = $props();

	const t = i18n.t;
	const monthName = (at: number) => new Date(at).toLocaleDateString(locale, { month: 'long', year: 'numeric' });
	const dayName = (at: number) => new Date(at).toLocaleDateString(locale, { day: 'numeric', month: 'short' });

	function waited(n: number | null): string {
		if (n === null) return '';
		if (n === 0) return t('notebook.answeredSameDay');
		if (n === 1) return t('notebook.answeredAfterOneDay');
		return m.notebook_answered_after_days({ n: String(n) });
	}
</script>

<ol class="timeline">
	{#each months as mo (mo.month)}
		<li class="month">
			<h3 class="month-name">{monthName(mo.at)}</h3>
			<ol>
				{#each mo.prayers as p (p.id)}
					{@const days = daysWaited(p)}
					<li class="stone" class:long={days !== null && days >= 30}>
						<span class="dot" aria-hidden="true"></span>
						<p class="when text-micro">
							<time datetime={new Date(p.answeredAt!).toISOString()}>{dayName(p.answeredAt!)}</time>
							{#if p.person}· {t('notebook.prayingFor')} <strong>{p.person}</strong>{/if}
						</p>
						<p class="asked">{p.title || p.body}</p>
						{#if p.answer}<p class="answer">{p.answer}</p>{/if}
						<p class="waited text-micro">{waited(days)}</p>
					</li>
				{/each}
			</ol>
		</li>
	{/each}
</ol>

<style>
	.timeline {
		--line: color-mix(in srgb, var(--hl-green) 55%, transparent);
		--ink: color-mix(in srgb, var(--hl-green) 65%, var(--text));
		margin-top: 1.5rem;
		padding-inline-start: 1.4rem;
		border-inline-start: 2px solid var(--line);
	}
	.month + .month {
		margin-top: 1.75rem;
	}
	.month-name {
		margin-bottom: 0.75rem;
		font-family: var(--font-display);
		font-size: var(--fs-small);
		font-style: italic;
		font-weight: 600;
		color: var(--accent);
	}
	.stone {
		position: relative;
	}
	.stone + .stone {
		margin-top: 1.1rem;
	}
	/* A stone of remembrance on the line; the long-awaited ones are set larger. */
	.dot {
		position: absolute;
		top: 0.3rem;
		inset-inline-start: calc(-1.4rem - 1px - 0.4rem);
		width: 0.8rem;
		height: 0.8rem;
		border-radius: 50%;
		background: var(--hl-green);
		box-shadow: 0 0 0 3px var(--surface);
	}
	.long .dot {
		inset-inline-start: calc(-1.4rem - 1px - 0.55rem);
		width: 1.1rem;
		height: 1.1rem;
		top: 0.15rem;
		background: var(--gold);
	}
	.when {
		color: var(--muted);
	}
	.when strong {
		color: var(--text);
		font-weight: 600;
	}
	.asked {
		margin-top: 0.1rem;
		font-family: var(--font-display);
		font-size: var(--fs-body);
		line-height: 1.5;
		color: var(--text);
		display: -webkit-box;
		-webkit-line-clamp: 3;
		line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.answer {
		margin-top: 0.25rem;
		font-family: var(--font-display);
		font-style: italic;
		line-height: 1.5;
		color: var(--ink);
	}
	.answer::before {
		content: '✓ ';
		font-style: normal;
	}
	.waited {
		margin-top: 0.2rem;
		color: var(--muted);
	}
</style>
