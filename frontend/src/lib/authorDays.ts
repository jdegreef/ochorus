/**
 * The days of the year the library's writers were born and died, for the
 * birthday candle: on one of them a small candle burns by the writer's name on
 * their page (AuthorCandle) and on the home dashboard (OnThisDay).
 *
 * The fixture holds only years (`birth_year` / `death_year`), so the day is
 * curated here, and only where it is well attested — a writer with a baptism
 * date, a disputed day or a feast day standing in for an unknown one is left
 * out rather than guessed. Dates are the ones commonly cited (New Style for the
 * English born before 1752, as their biographers give them). `name` is the
 * fixture's, copied so the home line needs no request; `authorDays.test.ts`
 * holds every slug, name and year to `authors.json`.
 */
export interface AuthorDays {
	name: string;
	/** ISO `YYYY-MM-DD`. */
	born?: string;
	died?: string;
}

export const AUTHOR_DAYS: Record<string, AuthorDays> = {
	'a-b-simpson': { name: "A. B. Simpson", born: '1843-12-15', died: '1919-10-29' },
	'a-w-tozer': { name: "A. W. Tozer", born: '1897-04-21', died: '1963-05-12' },
	'absalom-jones': { name: "Absalom Jones", born: '1746-11-07', died: '1818-02-13' },
	'alexander-maclaren': { name: "Alexander Maclaren", born: '1826-02-11', died: '1910-05-05' },
	'amanda-berry-smith': { name: "Amanda Berry Smith", born: '1837-01-23', died: '1915-02-24' },
	'amy-carmichael': { name: "Amy Carmichael", born: '1867-12-16', died: '1951-01-18' },
	'andrew-murray': { name: "Andrew Murray", born: '1828-05-09', died: '1917-01-18' },
	'anselm-of-canterbury': { name: "Anselm of Canterbury", died: '1109-04-21' },
	'arthur-t-pierson': { name: "Arthur T. Pierson", born: '1837-03-06', died: '1911-06-03' },
	'athanasius-of-alexandria': { name: "Athanasius of Alexandria", died: '0373-05-02' },
	'augustine-of-hippo': { name: "Augustine of Hippo", born: '0354-11-13', died: '0430-08-28' },
	'basil-of-caesarea': { name: "Basil of Caesarea", died: '0379-01-01' },
	'bernard-of-clairvaux': { name: "Bernard of Clairvaux", died: '1153-08-20' },
	'bill-bright': { name: "Bill Bright", born: '1921-10-19', died: '2003-07-19' },
	'billy-graham': { name: "Billy Graham", born: '1918-11-07', died: '2018-02-21' },
	'billy-sunday': { name: "Billy Sunday", born: '1862-11-19', died: '1935-11-06' },
	'blaise-pascal': { name: "Blaise Pascal", born: '1623-06-19', died: '1662-08-19' },
	'brother-lawrence': { name: "Brother Lawrence", died: '1691-02-12' },
	'c-s-lewis': { name: "C. S. Lewis", born: '1898-11-29', died: '1963-11-22' },
	'c-t-studd': { name: "C. T. Studd", born: '1860-12-02', died: '1931-07-16' },
	'catherine-booth': { name: "Catherine Booth", born: '1829-01-17', died: '1890-10-04' },
	'catherine-of-siena': { name: "Catherine of Siena", born: '1347-03-25', died: '1380-04-29' },
	'charles-finney': { name: "Charles G. Finney", born: '1792-08-29', died: '1875-08-16' },
	'charles-h-spurgeon': { name: "Charles H. Spurgeon", born: '1834-06-19', died: '1892-01-31' },
	'christmas-evans': { name: "Christmas Evans", born: '1766-12-25', died: '1838-07-19' },
	'corrie-ten-boom': { name: "Corrie ten Boom", born: '1892-04-15', died: '1983-04-15' },
	'cyprian-of-carthage': { name: "Cyprian of Carthage", died: '0258-09-14' },
	'david-brainerd': { name: "David Brainerd", born: '1718-04-20', died: '1747-10-09' },
	'david-livingstone': { name: "David Livingstone", born: '1813-03-19', died: '1873-05-01' },
	'derek-prince': { name: "Derek Prince", born: '1915-08-14', died: '2003-09-24' },
	'dietrich-bonhoeffer': { name: "Dietrich Bonhoeffer", born: '1906-02-04', died: '1945-04-09' },
	'dwight-l-moody': { name: "Dwight L. Moody", born: '1837-02-05', died: '1899-12-22' },
	'e-m-bounds': { name: "E. M. Bounds", born: '1835-08-15', died: '1913-08-24' },
	'elisabeth-elliot': { name: "Elisabeth Elliot", born: '1926-12-21', died: '2015-06-15' },
	'festo-kivengere': { name: "Festo Kivengere", died: '1988-05-18' },
	'frances-ridley-havergal': { name: "Frances Ridley Havergal", born: '1836-12-14', died: '1879-06-03' },
	'francis-de-sales': { name: "Francis de Sales", born: '1567-08-21', died: '1622-12-28' },
	'frederick-brotherton-meyer': { name: "F. B. Meyer", born: '1847-04-08', died: '1929-03-28' },
	'frederick-w-robertson': { name: "Frederick W. Robertson", born: '1816-02-03', died: '1853-08-15' },
	'g-k-chesterton': { name: "G. K. Chesterton", born: '1874-05-29', died: '1936-06-14' },
	'george-herbert': { name: "George Herbert", born: '1593-04-03', died: '1633-03-01' },
	'george-macdonald': { name: "George MacDonald", born: '1824-12-10', died: '1905-09-18' },
	'george-muller': { name: "George Müller", born: '1805-09-27', died: '1898-03-10' },
	'george-whitefield': { name: "George Whitefield", born: '1714-12-27', died: '1770-09-30' },
	'gladys-aylward': { name: "Gladys Aylward", born: '1902-02-24', died: '1970-01-03' },
	'gregory-the-great': { name: "Gregory the Great", died: '0604-03-12' },
	'hannah-whitall-smith': { name: "Hannah Whitall Smith", born: '1832-02-07', died: '1911-05-01' },
	'harriet-tubman': { name: "Harriet Tubman", died: '1913-03-10' },
	'helen-roseveare': { name: "Helen Roseveare", born: '1925-09-21', died: '2016-12-07' },
	'henry-drummond': { name: "Henry Drummond", born: '1851-08-17', died: '1897-03-11' },
	'horatius-bonar': { name: "Horatius Bonar", born: '1808-12-19', died: '1889-07-31' },
	'hudson-taylor': { name: "Hudson Taylor", born: '1832-05-21', died: '1905-06-03' },
	'ignatius-of-loyola': { name: "Ignatius of Loyola", died: '1556-07-31' },
	'isaac-watts': { name: "Isaac Watts", born: '1674-07-17', died: '1748-11-25' },
	'j-c-ryle': { name: "J. C. Ryle", born: '1816-05-10', died: '1900-06-10' },
	'janani-luwum': { name: "Janani Luwum", died: '1977-02-16' },
	'jeanne-guyon': { name: "Jeanne Guyon", born: '1648-04-13', died: '1717-06-09' },
	'jeremy-taylor': { name: "Jeremy Taylor", died: '1667-08-13' },
	'jerome': { name: "Jerome", died: '0420-09-30' },
	'jim-elliot': { name: "Jim Elliot", born: '1927-10-08', died: '1956-01-08' },
	'john-bunyan': { name: "John Bunyan", died: '1688-08-31' },
	'john-calvin': { name: "John Calvin", born: '1509-07-10', died: '1564-05-27' },
	'john-chrysostom': { name: "John Chrysostom", died: '0407-09-14' },
	'john-g-lake': { name: "John G. Lake", born: '1870-03-18', died: '1935-09-16' },
	'john-henry-newman': { name: "John Henry Newman", born: '1801-02-21', died: '1890-08-11' },
	'john-hyde': { name: "John Hyde", born: '1865-11-09', died: '1912-02-17' },
	'john-milton': { name: "John Milton", born: '1608-12-09', died: '1674-11-08' },
	'john-newton': { name: "John Newton", born: '1725-07-24', died: '1807-12-21' },
	'john-owen': { name: "John Owen", died: '1683-08-24' },
	'john-r-mott': { name: "John R. Mott", born: '1865-05-25', died: '1955-01-31' },
	'john-stott': { name: "John Stott", born: '1921-04-27', died: '2011-07-27' },
	'john-wesley': { name: "John Wesley", born: '1703-06-28', died: '1791-03-02' },
	'jonathan-edwards': { name: "Jonathan Edwards", born: '1703-10-05', died: '1758-03-22' },
	'josephine-bakhita': { name: "Josephine Bakhita", died: '1947-02-08' },
	'kanzo-uchimura': { name: "Kanzo Uchimura", born: '1861-03-26', died: '1930-03-28' },
	'kateri-tekakwitha': { name: "Kateri Tekakwitha", died: '1680-04-17' },
	'lemuel-haynes': { name: "Lemuel Haynes", born: '1753-07-18', died: '1833-09-28' },
	'loren-cunningham': { name: "Loren Cunningham", born: '1935-06-30', died: '2023-10-06' },
	'lottie-moon': { name: "Lottie Moon", born: '1840-12-12', died: '1912-12-24' },
	'maria-w-stewart': { name: "Maria W. Stewart", died: '1879-12-17' },
	'martin-luther': { name: "Martin Luther", born: '1483-11-10', died: '1546-02-18' },
	'martyn-lloyd-jones': { name: "Martyn Lloyd-Jones", born: '1899-12-20', died: '1981-03-01' },
	'mary-slessor': { name: "Mary Slessor", born: '1848-12-02', died: '1915-01-13' },
	'nancy-prince': { name: "Nancy Prince", born: '1799-09-15' },
	'pandita-ramabai': { name: "Pandita Ramabai", born: '1858-04-23', died: '1922-04-05' },
	'philip-doddridge': { name: "Philip Doddridge", born: '1702-06-26', died: '1751-10-26' },
	'phillips-brooks': { name: "Phillips Brooks", born: '1835-12-13', died: '1893-01-23' },
	'phillis-wheatley': { name: "Phillis Wheatley", died: '1784-12-05' },
	'polycarp': { name: "Polycarp of Smyrna", died: '0155-02-23' },
	'r-a-torrey': { name: "R. A. Torrey", born: '1856-01-28', died: '1928-10-26' },
	'rees-howells': { name: "Rees Howells", born: '1879-10-10', died: '1950-02-13' },
	'richard-allen': { name: "Richard Allen", born: '1760-02-14', died: '1831-03-26' },
	'richard-baxter': { name: "Richard Baxter", born: '1615-11-12', died: '1691-12-08' },
	'richard-sibbes': { name: "Richard Sibbes", died: '1635-07-05' },
	'robert-murray-mcheyne': { name: "Robert Murray M’Cheyne", born: '1813-05-21', died: '1843-03-25' },
	'sadhu-sundar-singh': { name: "Sadhu Sundar Singh", born: '1889-09-03' },
	'samson-occom': { name: "Samson Occom", died: '1792-07-14' },
	'samuel-ajayi-crowther': { name: "Samuel Ajayi Crowther", died: '1891-12-31' },
	'samuel-davies': { name: "Samuel Davies", born: '1723-11-03', died: '1761-02-04' },
	'smith-wigglesworth': { name: "Smith Wigglesworth", born: '1859-06-08', died: '1947-03-12' },
	'susanna-wesley': { name: "Susanna Wesley", born: '1669-01-20', died: '1742-07-23' },
	'teresa-of-avila': { name: "Teresa of Ávila", born: '1515-03-28', died: '1582-10-04' },
	'thomas-boston': { name: "Thomas Boston", born: '1676-03-17', died: '1732-05-20' },
	'thomas-chalmers': { name: "Thomas Chalmers", born: '1780-03-17', died: '1847-05-31' },
	'timothy-keller': { name: "Timothy Keller", born: '1950-09-23', died: '2023-05-19' },
	'watchman-nee': { name: "Watchman Nee", born: '1903-11-04', died: '1972-05-30' },
	'william-booth': { name: "William Booth", born: '1829-04-10', died: '1912-08-20' },
	'william-carey': { name: "William Carey", born: '1761-08-17', died: '1834-06-09' },
	'william-j-seymour': { name: "William J. Seymour", born: '1870-05-02', died: '1922-09-28' },
	'william-law': { name: "William Law", died: '1761-04-09' },
	'william-wilberforce': { name: "William Wilberforce", born: '1759-08-24', died: '1833-07-29' }
};

export interface Anniversary {
	slug: string;
	name: string;
	kind: 'born' | 'died';
	/** ISO `YYYY-MM-DD`: the day itself, year and all. */
	date: string;
}

const monthDay = (d: Date) =>
	`${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

/**
 * The writer's anniversary on the reader's local day, if it is one: their
 * birth before their death (Corrie ten Boom has both on 15 April).
 */
export function anniversaryOn(slug: string, date: Date): Anniversary | null {
	const days = AUTHOR_DAYS[slug];
	if (!days) return null;
	const md = monthDay(date);
	for (const kind of ['born', 'died'] as const) {
		const iso = days[kind];
		if (iso?.endsWith(md)) return { slug, name: days.name, kind, date: iso };
	}
	return null;
}

/** Every writer with an anniversary on the reader's local day, in name order. */
export function anniversariesOn(date: Date): Anniversary[] {
	return Object.keys(AUTHOR_DAYS)
		.map((slug) => anniversaryOn(slug, date))
		.filter((a): a is Anniversary => a !== null)
		.sort((x, y) => x.name.localeCompare(y.name));
}

/** "13 November 354" in the reader's language — the day as it was, year and all. */
export function anniversaryDate(iso: string, lang: string): string {
	const [y, m, d] = iso.split('-').map(Number);
	const day = new Date(2000, m - 1, d);
	day.setFullYear(y); // not the Date(y, …) constructor, which reads 0–99 as 1900–1999
	return new Intl.DateTimeFormat(lang, { day: 'numeric', month: 'long', year: 'numeric' }).format(day);
}
