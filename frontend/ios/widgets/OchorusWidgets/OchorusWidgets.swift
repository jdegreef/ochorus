import SwiftUI
import WidgetKit

// The Ochorus home-screen widgets (design #46) — the iOS twin of
// android/app/src/main/java/com/ochorus/app/widgets/. They draw the snapshot the
// app stores in the App Group (frontend/src/lib/widgetSnapshot.ts: words already
// in the reader's language, the next few days' verses, the current book).
//
// NOT YET IN THE XCODE PROJECT — see frontend/MOBILE.md, "Home-screen widgets →
// iOS setup". Written on Linux and never compiled: check it in Xcode.

private let appGroup = "group.com.ochorus.app"

// MARK: - The snapshot

struct WidgetVerse: Decodable {
    let date: String
    let text: String
    let ref: String
    let lang: String
}

struct WidgetBook: Decodable {
    let title: String
    let author: String
    let chapter: String
    let pct: Int
    let url: String
    let coverUrl: String?
    let coverColor: String?
    let lang: String
    let description: String
}

struct WidgetSnapshot: Decodable {
    struct Labels: Decodable {
        let today: String
        let `continue`: String
        let start: String
    }

    struct Urls: Decodable {
        let today: String
        let home: String
        let books: String
    }

    let v: Int
    let locale: String
    let rtl: Bool
    let labels: Labels
    let urls: Urls
    let verses: [WidgetVerse]
    let book: WidgetBook?

    static func load() -> WidgetSnapshot? {
        guard let json = UserDefaults(suiteName: appGroup)?.string(forKey: "snapshot"),
              let snapshot = try? JSONDecoder().decode(WidgetSnapshot.self, from: Data(json.utf8)),
              snapshot.v == 1
        else { return nil }
        return snapshot
    }

    static func cover() -> UIImage? {
        guard let dir = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: appGroup) else { return nil }
        return UIImage(contentsOfFile: dir.appendingPathComponent("widget-cover.png").path)
    }
}

/// The reader's local `YYYY-MM-DD` for `date`, as the snapshot dates its verses.
func dayKey(_ date: Date) -> String {
    let formatter = DateFormatter()
    formatter.calendar = Calendar(identifier: .gregorian)
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.timeZone = .current
    formatter.dateFormat = "yyyy-MM-dd"
    return formatter.string(from: date)
}

/// pickVerseDay in frontend/src/lib/widgetSnapshot.ts (and Android's VersePicker):
/// today's verse; else the latest before today, stale (no "today" eyebrow); else none.
func pickVerse(_ verses: [WidgetVerse], today: String) -> (verse: WidgetVerse, stale: Bool)? {
    if let exact = verses.first(where: { $0.date == today }) { return (exact, false) }
    guard let earlier = verses.filter({ $0.date < today }).max(by: { $0.date < $1.date }) else { return nil }
    return (earlier, true)
}

// MARK: - Colours (paper by day, lamplight by night — frontend/src/app.css)

private func dynamic(_ light: UInt32, _ dark: UInt32) -> Color {
    func rgb(_ hex: UInt32) -> UIColor {
        UIColor(red: CGFloat((hex >> 16) & 0xff) / 255, green: CGFloat((hex >> 8) & 0xff) / 255, blue: CGFloat(hex & 0xff) / 255, alpha: 1)
    }
    return Color(UIColor { $0.userInterfaceStyle == .dark ? rgb(dark) : rgb(light) })
}

private enum Palette {
    static let ground = dynamic(0xfaf6ef, 0x201b15)
    static let text = dynamic(0x221c15, 0xece3d4)
    static let muted = dynamic(0x6e6358, 0xab9f8b)
    static let accent = dynamic(0x3f3d9a, 0x9c9af2)
    static let track = dynamic(0xe8dfcf, 0x3a3228)
    static let coverGround = dynamic(0xecebf7, 0x221f33)
}

private func hexColor(_ hex: String?) -> Color? {
    guard let hex = hex, hex.count == 7, hex.hasPrefix("#"), let value = UInt32(hex.dropFirst(), radix: 16) else { return nil }
    return dynamic(value, value)
}

private struct Eyebrow: View {
    let text: String
    var body: some View {
        Text(text.uppercased())
            .font(.system(size: 11, weight: .semibold))
            .tracking(1.1)
            .foregroundColor(Palette.accent)
            .lineLimit(1)
    }
}

extension View {
    /// iOS 17 draws a widget's background through containerBackground.
    @ViewBuilder func widgetGround() -> some View {
        if #available(iOSApplicationExtension 17.0, *) {
            containerBackground(Palette.ground, for: .widget)
        } else {
            padding().background(Palette.ground)
        }
    }
}

// MARK: - Today

struct TodayEntry: TimelineEntry {
    let date: Date
    let snapshot: WidgetSnapshot?
}

struct TodayProvider: TimelineProvider {
    func placeholder(in context: Context) -> TodayEntry { TodayEntry(date: Date(), snapshot: nil) }

    func getSnapshot(in context: Context, completion: @escaping (TodayEntry) -> Void) {
        completion(TodayEntry(date: Date(), snapshot: WidgetSnapshot.load()))
    }

    /// One entry now and one at each coming local midnight the stored verses
    /// cover, so the verse turns over at midnight with the app closed; then a
    /// reload the midnight after, which shows the last verse undated until the
    /// app sends more.
    func getTimeline(in context: Context, completion: @escaping (Timeline<TodayEntry>) -> Void) {
        let snapshot = WidgetSnapshot.load()
        let calendar = Calendar.current
        let now = Date()
        var entries = [TodayEntry(date: now, snapshot: snapshot)]
        var midnight = calendar.startOfDay(for: now)
        for _ in 0..<(snapshot?.verses.count ?? 0) {
            guard let next = calendar.date(byAdding: .day, value: 1, to: midnight) else { break }
            midnight = next
            entries.append(TodayEntry(date: midnight, snapshot: snapshot))
        }
        let reload = calendar.date(byAdding: .day, value: 1, to: midnight) ?? midnight
        completion(Timeline(entries: entries, policy: .after(reload)))
    }
}

struct TodayView: View {
    let entry: TodayEntry

    var body: some View {
        content
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
            .environment(\.layoutDirection, entry.snapshot?.rtl == true ? .rightToLeft : .leftToRight)
            .widgetGround()
    }

    @ViewBuilder private var content: some View {
        if let snapshot = entry.snapshot {
            if let pick = pickVerse(snapshot.verses, today: dayKey(entry.date)) {
                VStack(alignment: .leading, spacing: 6) {
                    if !pick.stale { Eyebrow(text: snapshot.labels.today) }
                    Text(pick.verse.text)
                        .font(.system(.body, design: .serif))
                        .foregroundColor(Palette.text)
                        .lineLimit(4)
                    Text(pick.verse.ref)
                        .font(.footnote)
                        .foregroundColor(Palette.muted)
                        .lineLimit(1)
                }
                .accessibilityElement(children: .ignore)
                .accessibilityLabel(pick.stale
                    ? "\(pick.verse.text) — \(pick.verse.ref)"
                    : "\(snapshot.labels.today). \(pick.verse.text) — \(pick.verse.ref)")
                .widgetURL(URL(string: snapshot.urls.today))
            } else {
                VStack(alignment: .leading, spacing: 6) {
                    Eyebrow(text: "Ochorus")
                    Text(snapshot.labels.start).font(.system(.body, design: .serif)).foregroundColor(Palette.text)
                }
                .widgetURL(URL(string: snapshot.urls.home))
            }
        } else {
            VStack(alignment: .leading, spacing: 6) {
                Eyebrow(text: NSLocalizedString("widget.today.name", value: "Verse for today", comment: ""))
                Text(NSLocalizedString("widget.placeholder", value: "Open Ochorus to begin.", comment: ""))
                    .font(.system(.body, design: .serif))
                    .foregroundColor(Palette.text)
            }
        }
    }
}

struct TodayWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "OchorusToday", provider: TodayProvider()) { TodayView(entry: $0) }
            .configurationDisplayName(NSLocalizedString("widget.today.name", value: "Verse for today", comment: ""))
            .description(NSLocalizedString("widget.today.description", value: "Today’s verse from Ochorus, new each day.", comment: ""))
            .supportedFamilies([.systemMedium, .systemSmall])
    }
}

// MARK: - Continue

struct ContinueEntry: TimelineEntry {
    let date: Date
    let snapshot: WidgetSnapshot?
    let cover: UIImage?
}

struct ContinueProvider: TimelineProvider {
    func placeholder(in context: Context) -> ContinueEntry { ContinueEntry(date: Date(), snapshot: nil, cover: nil) }

    func getSnapshot(in context: Context, completion: @escaping (ContinueEntry) -> Void) {
        completion(ContinueEntry(date: Date(), snapshot: WidgetSnapshot.load(), cover: WidgetSnapshot.cover()))
    }

    /// The reader's place changes only in the app, which reloads this.
    func getTimeline(in context: Context, completion: @escaping (Timeline<ContinueEntry>) -> Void) {
        let entry = ContinueEntry(date: Date(), snapshot: WidgetSnapshot.load(), cover: WidgetSnapshot.cover())
        completion(Timeline(entries: [entry], policy: .never))
    }
}

struct ContinueView: View {
    let entry: ContinueEntry

    var body: some View {
        content
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
            .environment(\.layoutDirection, entry.snapshot?.rtl == true ? .rightToLeft : .leftToRight)
            .widgetGround()
    }

    @ViewBuilder private var content: some View {
        if let snapshot = entry.snapshot, let book = snapshot.book {
            HStack(alignment: .center, spacing: 12) {
                ZStack {
                    hexColor(book.coverColor) ?? Palette.coverGround
                    if let cover = entry.cover {
                        Image(uiImage: cover).resizable().scaledToFill()
                    }
                }
                .frame(width: 48, height: 72)
                .clipShape(RoundedRectangle(cornerRadius: 3))
                VStack(alignment: .leading, spacing: 3) {
                    Eyebrow(text: snapshot.labels.continue)
                    Text(book.title)
                        .font(.system(.headline, design: .serif))
                        .foregroundColor(Palette.text)
                        .lineLimit(2)
                    Text(book.chapter).font(.footnote).foregroundColor(Palette.muted).lineLimit(1)
                    ProgressView(value: Double(book.pct), total: 100)
                        .tint(Palette.accent)
                        .padding(.top, 6)
                }
            }
            .accessibilityElement(children: .ignore)
            .accessibilityLabel(book.description)
            .widgetURL(URL(string: book.url))
        } else if let snapshot = entry.snapshot {
            VStack(alignment: .leading, spacing: 6) {
                Eyebrow(text: snapshot.labels.continue)
                Text(snapshot.labels.start).font(.system(.body, design: .serif)).foregroundColor(Palette.text)
            }
            .widgetURL(URL(string: snapshot.urls.books))
        } else {
            VStack(alignment: .leading, spacing: 6) {
                Eyebrow(text: NSLocalizedString("widget.continue.name", value: "Continue reading", comment: ""))
                Text(NSLocalizedString("widget.placeholder", value: "Open Ochorus to begin.", comment: ""))
                    .font(.system(.body, design: .serif))
                    .foregroundColor(Palette.text)
            }
        }
    }
}

struct ContinueWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "OchorusContinue", provider: ContinueProvider()) { ContinueView(entry: $0) }
            .configurationDisplayName(NSLocalizedString("widget.continue.name", value: "Continue reading", comment: ""))
            .description(NSLocalizedString("widget.continue.description", value: "Your book, one tap from your place.", comment: ""))
            .supportedFamilies([.systemMedium, .systemSmall])
    }
}

@main
struct OchorusWidgets: WidgetBundle {
    var body: some Widget {
        TodayWidget()
        ContinueWidget()
    }
}
