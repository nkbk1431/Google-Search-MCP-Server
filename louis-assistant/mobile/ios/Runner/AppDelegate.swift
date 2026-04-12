import UIKit
import Flutter

@UIApplicationMain
@objc class AppDelegate: FlutterAppDelegate {

    private let channelName = "com.yourname.louis/intents"

    override func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {

        GeneratedPluginRegistrant.register(with: self)

        guard let controller = window?.rootViewController as? FlutterViewController else {
            return super.application(application, didFinishLaunchingWithOptions: launchOptions)
        }

        let channel = FlutterMethodChannel(
            name: channelName,
            binaryMessenger: controller.binaryMessenger
        )

        channel.setMethodCallHandler { [weak self] call, result in
            self?.handle(call: call, result: result)
        }

        return super.application(application, didFinishLaunchingWithOptions: launchOptions)
    }

    // MARK: - Method Handler

    private func handle(call: FlutterMethodCall, result: @escaping FlutterResult) {
        let args = call.arguments as? [String: Any] ?? [:]

        switch call.method {

        // ── 전화 걸기 ─────────────────────────────────────────────────
        case "makePhoneCall":
            let contact = args["contact"] as? String ?? ""
            if let url = buildPhoneURL(contact: contact) {
                UIApplication.shared.open(url) { success in
                    success ? result(nil) : result(FlutterError(code: "UNAVAILABLE",
                        message: "전화 앱을 열 수 없어요", details: nil))
                }
            } else {
                result(FlutterError(code: "INVALID", message: "연락처가 없어요", details: nil))
            }

        // ── 문자 보내기 ───────────────────────────────────────────────
        case "sendSms":
            let contact = args["contact"] as? String ?? ""
            let message = args["message"] as? String ?? ""
            var urlStr = "sms:\(contact)"
            if !message.isEmpty, let encoded = message.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) {
                urlStr += "&body=\(encoded)"
            }
            if let url = URL(string: urlStr) {
                UIApplication.shared.open(url) { success in
                    success ? result(nil) : result(FlutterError(code: "UNAVAILABLE",
                        message: "문자 앱을 열 수 없어요", details: nil))
                }
            } else {
                result(FlutterError(code: "INVALID", message: "연락처가 없어요", details: nil))
            }

        // ── 지도 열기 ─────────────────────────────────────────────────
        case "openMaps":
            let origin = args["origin"] as? String ?? ""
            let destination = args["destination"] as? String ?? ""
            let mode = args["mode"] as? String ?? "transit"
            openMaps(origin: origin, destination: destination, mode: mode, result: result)

        // ── 음악 검색 ─────────────────────────────────────────────────
        case "openMusicSearch":
            let query = args["query"] as? String ?? ""
            openMusicSearch(query: query, result: result)

        // ── YouTube 검색 ──────────────────────────────────────────────
        case "openYouTube":
            let query = (args["query"] as? String ?? "").addingPercentEncoding(
                withAllowedCharacters: .urlQueryAllowed) ?? ""
            if let url = URL(string: "https://www.youtube.com/results?search_query=\(query)") {
                UIApplication.shared.open(url) { _ in result(nil) }
            } else {
                result(nil)
            }

        // ── 카카오톡 ──────────────────────────────────────────────────
        case "sendKakaoMessage":
            if let url = URL(string: "kakaotalk://"), UIApplication.shared.canOpenURL(url) {
                UIApplication.shared.open(url) { _ in result(nil) }
            } else {
                result(FlutterError(code: "UNAVAILABLE",
                    message: "카카오톡이 설치되지 않았어요", details: nil))
            }

        // ── 스마트홈 ──────────────────────────────────────────────────
        case "smartHomeControl":
            // iOS: HomeKit 또는 Google Home 앱으로 리다이렉트
            if let url = URL(string: "googlegooglehome://"), UIApplication.shared.canOpenURL(url) {
                UIApplication.shared.open(url) { _ in result(nil) }
            } else if let url = URL(string: "x-apple-home://"),
                       UIApplication.shared.canOpenURL(url) {
                UIApplication.shared.open(url) { _ in result(nil) }
            } else {
                result(FlutterError(code: "UNAVAILABLE",
                    message: "스마트홈 앱이 없어요", details: nil))
            }

        // ── 위젯 리마인더 업데이트 ────────────────────────────────────
        case "updateWidgetReminder":
            let text = args["text"] as? String ?? ""
            updateWidgetSharedData(reminderText: text)
            result(nil)

        // ── 위젯 새로고침 ─────────────────────────────────────────────
        case "refreshWidget":
            // iOS 위젯(WidgetKit)은 SwiftUI 기반. 여기서는 App Group UserDefaults를 갱신.
            result(nil)

        default:
            result(FlutterMethodNotImplemented)
        }
    }

    // MARK: - Helpers

    private func buildPhoneURL(contact: String) -> URL? {
        let isNumber = contact.range(of: "^[0-9+\\-() ]+$", options: .regularExpression) != nil
        if isNumber {
            let digits = contact.replacingOccurrences(of: " ", with: "")
            return URL(string: "tel:\(digits)")
        }
        // 연락처 앱 열기 (이름 검색 불가 → 연락처 앱 오픈)
        return URL(string: "contacts://")
    }

    private func openMaps(origin: String, destination: String, mode: String, result: @escaping FlutterResult) {
        let modeParam: String = {
            switch mode {
            case "driving": return "d"
            case "walking": return "w"
            case "bicycling": return "b"
            default: return "r"  // transit
            }
        }()

        var urlStr: String
        let encDest = destination.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
        if origin.isEmpty {
            urlStr = "https://maps.google.com/maps?daddr=\(encDest)&dirflg=\(modeParam)"
        } else {
            let encOrig = origin.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
            urlStr = "https://maps.google.com/maps?saddr=\(encOrig)&daddr=\(encDest)&dirflg=\(modeParam)"
        }

        // Google Maps 앱 우선, 없으면 Apple Maps
        let googleMapsAppURL = URL(string: "comgooglemaps://\(urlStr.dropFirst("https://maps.google.com".count))")!
        if UIApplication.shared.canOpenURL(googleMapsAppURL) {
            UIApplication.shared.open(googleMapsAppURL) { _ in result(nil) }
        } else if let url = URL(string: urlStr) {
            UIApplication.shared.open(url) { _ in result(nil) }
        } else {
            result(FlutterError(code: "UNAVAILABLE", message: "지도 앱을 열 수 없어요", details: nil))
        }
    }

    private func openMusicSearch(query: String, result: @escaping FlutterResult) {
        let encoded = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
        // Spotify 앱 딥링크
        if let spotifyURL = URL(string: "spotify:search:\(encoded)"),
           UIApplication.shared.canOpenURL(spotifyURL) {
            UIApplication.shared.open(spotifyURL) { _ in result(nil) }
        } else if let appleMusic = URL(string: "music://music.apple.com/search?term=\(encoded)"),
                  UIApplication.shared.canOpenURL(appleMusic) {
            UIApplication.shared.open(appleMusic) { _ in result(nil) }
        } else {
            result(FlutterError(code: "UNAVAILABLE", message: "음악 앱을 열 수 없어요", details: nil))
        }
    }

    /// App Group UserDefaults로 위젯에 리마인더 텍스트를 공유합니다.
    private func updateWidgetSharedData(reminderText: String) {
        let defaults = UserDefaults(suiteName: "group.com.yourname.louis")
        defaults?.set(reminderText, forKey: "next_reminder")
        defaults?.synchronize()
    }
}
