import Capacitor
import UIKit

/// The app's web view controller, so the app's own plugins (no npm package, so
/// `cap sync` cannot list them) are registered as the bridge starts.
/// SceneDelegate's `CAPBridgeViewController()` becomes `OchorusBridgeViewController()`.
///
/// NOT YET IN THE XCODE PROJECT — see frontend/MOBILE.md, "Home-screen widgets
/// → iOS setup". Written on Linux and never compiled: check it in Xcode.
class OchorusBridgeViewController: CAPBridgeViewController {
    override open func capacitorDidLoad() {
        bridge?.registerPluginInstance(OchorusWidgetsPlugin())
    }
}
