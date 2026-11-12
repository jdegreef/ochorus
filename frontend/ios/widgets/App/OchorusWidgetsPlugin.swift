import Capacitor
import Foundation
import UIKit
import WidgetKit

/// The web view's way to the home-screen widgets: `setSnapshot({ json })` from
/// $lib/platform (setWidgetSnapshot) stores what the widgets draw in the App
/// Group both the app and the widget extension can read, downloads the current
/// book's cover beside it, and asks WidgetKit to redraw.
///
/// NOT YET IN THE XCODE PROJECT — see frontend/MOBILE.md, "Home-screen widgets
/// → iOS setup". Written on Linux and never compiled: check it in Xcode.
@objc(OchorusWidgetsPlugin)
public class OchorusWidgetsPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "OchorusWidgetsPlugin"
    public let jsName = "OchorusWidgets"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "setSnapshot", returnType: CAPPluginReturnPromise)
    ]

    /// Must match the App Group added to BOTH targets in Xcode.
    static let appGroup = "group.com.ochorus.app"
    static let snapshotKey = "snapshot"
    static let coverURLKey = "cover_url"
    static let coverFile = "widget-cover.png"
    static let version = 1

    @objc func setSnapshot(_ call: CAPPluginCall) {
        guard let json = call.getString("json"), json.utf8.count <= 64 * 1024,
              let data = json.data(using: .utf8),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              object["v"] as? Int == Self.version
        else {
            call.reject("Not a snapshot")
            return
        }
        guard let defaults = UserDefaults(suiteName: Self.appGroup),
              let container = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: Self.appGroup)
        else {
            call.reject("No App Group")
            return
        }
        defaults.set(json, forKey: Self.snapshotKey)
        call.resolve()

        let book = object["book"] as? [String: Any]
        let coverURL = (book?["coverUrl"] as? String).flatMap { $0.hasPrefix("https://") ? URL(string: $0) : nil }
        let file = container.appendingPathComponent(Self.coverFile)
        if coverURL?.absoluteString == defaults.string(forKey: Self.coverURLKey),
           FileManager.default.fileExists(atPath: file.path) {
            WidgetCenter.shared.reloadAllTimelines()
            return
        }
        // Better no cover than another book's.
        try? FileManager.default.removeItem(at: file)
        defaults.removeObject(forKey: Self.coverURLKey)
        guard let url = coverURL else {
            WidgetCenter.shared.reloadAllTimelines()
            return
        }
        var request = URLRequest(url: url)
        request.timeoutInterval = 15
        URLSession.shared.dataTask(with: request) { data, response, _ in
            if let data = data, data.count <= 4 * 1024 * 1024,
               (response as? HTTPURLResponse)?.statusCode == 200,
               let image = UIImage(data: data),
               let png = Self.scaled(image, maxWidth: 240).pngData(),
               (try? png.write(to: file, options: .atomic)) != nil {
                defaults.set(url.absoluteString, forKey: Self.coverURLKey)
            }
            WidgetCenter.shared.reloadAllTimelines()
        }.resume()
    }

    /// Widgets have a tight memory budget: keep the cover small.
    private static func scaled(_ image: UIImage, maxWidth: CGFloat) -> UIImage {
        guard image.size.width > maxWidth else { return image }
        let size = CGSize(width: maxWidth, height: (image.size.height * maxWidth / image.size.width).rounded())
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        return UIGraphicsImageRenderer(size: size, format: format).image { _ in
            image.draw(in: CGRect(origin: .zero, size: size))
        }
    }
}
