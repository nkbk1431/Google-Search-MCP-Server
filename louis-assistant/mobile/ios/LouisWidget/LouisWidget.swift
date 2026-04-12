import WidgetKit
import SwiftUI

// MARK: - App Group 식별자
private let appGroupID = "group.com.yourname.louis"
private let reminderKey = "next_reminder"

// MARK: - 타임라인 엔트리

struct LouisEntry: TimelineEntry {
    let date: Date
    let reminderText: String
}

// MARK: - 타임라인 프로바이더

struct LouisProvider: TimelineProvider {

    func placeholder(in context: Context) -> LouisEntry {
        LouisEntry(date: Date(), reminderText: "다음 리마인더: 약 먹기 오후 3시")
    }

    func getSnapshot(in context: Context, completion: @escaping (LouisEntry) -> Void) {
        completion(entry())
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<LouisEntry>) -> Void) {
        let current = entry()
        // 30분마다 타임라인 갱신
        let nextUpdate = Calendar.current.date(byAdding: .minute, value: 30, to: Date())!
        let timeline = Timeline(entries: [current], policy: .after(nextUpdate))
        completion(timeline)
    }

    private func entry() -> LouisEntry {
        let defaults = UserDefaults(suiteName: appGroupID)
        let text = defaults?.string(forKey: reminderKey) ?? "예정된 리마인더가 없어요"
        return LouisEntry(date: Date(), reminderText: text)
    }
}

// MARK: - 위젯 뷰

struct LouisWidgetEntryView: View {
    var entry: LouisEntry
    @Environment(\.widgetFamily) var family

    var body: some View {
        ZStack {
            // 배경 그라디언트
            LinearGradient(
                colors: [Color(hex: "1565C0"), Color(hex: "0D47A1")],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            VStack(alignment: .leading, spacing: 0) {
                // 헤더
                HStack {
                    Text("루이스")
                        .font(.headline)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                    Spacer()
                    Image(systemName: "mic.circle.fill")
                        .foregroundColor(.white.opacity(0.8))
                        .font(.title3)
                }
                .padding(.bottom, 6)

                // 리마인더 텍스트
                Text(entry.reminderText)
                    .font(.subheadline)
                    .foregroundColor(.white.opacity(0.9))
                    .lineLimit(family == .systemSmall ? 2 : 3)
                    .frame(maxWidth: .infinity, alignment: .leading)

                Spacer()

                // 버튼 영역 (medium 이상에서만 표시)
                if family != .systemSmall {
                    HStack {
                        Spacer()
                        // 음성 입력 버튼
                        Link(destination: URL(string: "louisapp://mic")!) {
                            Label("말하기", systemImage: "mic.fill")
                                .font(.caption)
                                .foregroundColor(.white)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 5)
                                .background(Color.white.opacity(0.2))
                                .cornerRadius(12)
                        }
                        // 앱 열기 버튼
                        Link(destination: URL(string: "louisapp://open")!) {
                            Text("앱 열기")
                                .font(.caption)
                                .foregroundColor(.white)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 5)
                                .background(Color.white.opacity(0.2))
                                .cornerRadius(12)
                        }
                    }
                }
            }
            .padding(14)
        }
        .widgetURL(URL(string: "louisapp://open"))
    }
}

// MARK: - 위젯 정의

@main
struct LouisWidget: Widget {
    let kind: String = "LouisWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: LouisProvider()) { entry in
            LouisWidgetEntryView(entry: entry)
        }
        .configurationDisplayName("루이스")
        .description("다음 리마인더와 빠른 음성 입력")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}

// MARK: - 헬퍼

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let r = Double((int >> 16) & 0xFF) / 255
        let g = Double((int >> 8) & 0xFF) / 255
        let b = Double(int & 0xFF) / 255
        self.init(red: r, green: g, blue: b)
    }
}

// MARK: - 미리보기

struct LouisWidget_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            LouisWidgetEntryView(
                entry: LouisEntry(
                    date: Date(),
                    reminderText: "약 먹기 — 3/15 오후 3:00"
                )
            )
            .previewContext(WidgetPreviewContext(family: .systemSmall))
            .previewDisplayName("Small")

            LouisWidgetEntryView(
                entry: LouisEntry(
                    date: Date(),
                    reminderText: "팀 미팅 준비 — 3/15 오전 10:00"
                )
            )
            .previewContext(WidgetPreviewContext(family: .systemMedium))
            .previewDisplayName("Medium")
        }
    }
}
