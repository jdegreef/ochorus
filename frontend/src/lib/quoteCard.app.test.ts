import { beforeEach, describe, expect, it, vi } from 'vitest';

// The card hand-off as the phone app runs it: no downloads in its web view, so
// the native sheet or — when the image cannot go — the card's words.
const p = vi.hoisted(() => ({ shareFile: vi.fn(), share: vi.fn() }));
vi.mock('$lib/platform', () => ({ IS_APP: true, shareFile: p.shareFile, share: p.share }));

import { shareCardImage } from './quoteCard';

const blob = new Blob(['png'], { type: 'image/png' });

beforeEach(() => {
	p.shareFile.mockReset();
	p.share.mockReset();
});

describe('shareCardImage in the app', () => {
	it('shares the image', async () => {
		p.shareFile.mockResolvedValue('shared');
		expect(await shareCardImage(blob, 'c.png', 'words')).toBe('shared');
		expect(p.share).not.toHaveBeenCalled();
	});
	it('stops at a dismissed sheet', async () => {
		p.shareFile.mockResolvedValue('aborted');
		expect(await shareCardImage(blob, 'c.png', 'words')).toBe('dismissed');
		expect(p.share).not.toHaveBeenCalled();
	});
	it('falls back to sharing the words when the image cannot go', async () => {
		p.shareFile.mockResolvedValue('unavailable');
		p.share.mockResolvedValue('shared');
		expect(await shareCardImage(blob, 'c.png', 'words')).toBe('shared');
		expect(p.share).toHaveBeenCalledWith({ text: 'words' });
	});
	it('reports unavailable only when nothing could be shared', async () => {
		p.shareFile.mockResolvedValue('unavailable');
		p.share.mockResolvedValue('unavailable');
		expect(await shareCardImage(blob, 'c.png', 'words')).toBe('unavailable');
	});
});
