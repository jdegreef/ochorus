/**
 * The webmail inbox for an address, so the "check your email" step can offer a
 * button straight to it instead of leaving the reader to go and find it.
 * Only the big public providers, matched on the exact domain; anything else
 * (a work or church address) gets no button rather than a wrong one.
 */
const INBOXES: { name: string; url: string; domains: string[] }[] = [
	{ name: 'Gmail', url: 'https://mail.google.com/', domains: ['gmail.com', 'googlemail.com'] },
	{
		name: 'Outlook',
		url: 'https://outlook.live.com/mail/',
		domains: ['outlook.com', 'hotmail.com', 'live.com', 'msn.com', 'hotmail.co.uk']
	},
	{ name: 'Yahoo Mail', url: 'https://mail.yahoo.com/', domains: ['yahoo.com', 'ymail.com', 'yahoo.co.uk'] },
	{ name: 'iCloud Mail', url: 'https://www.icloud.com/mail', domains: ['icloud.com', 'me.com', 'mac.com'] },
	{ name: 'Proton Mail', url: 'https://mail.proton.me/', domains: ['proton.me', 'protonmail.com', 'pm.me'] }
];

export function inboxFor(email: string): { name: string; url: string } | null {
	const domain = email.trim().toLowerCase().split('@')[1] ?? '';
	const hit = INBOXES.find((i) => i.domains.includes(domain));
	return hit ? { name: hit.name, url: hit.url } : null;
}
