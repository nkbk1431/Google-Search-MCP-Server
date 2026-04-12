package com.yourname.louis

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.ContactsContract
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {

    private val CHANNEL = "com.yourname.louis/intents"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
            .setMethodCallHandler { call, result ->
                when (call.method) {

                    // ── 전화 걸기 ────────────────────────────────────
                    "makePhoneCall" -> {
                        val contact = call.argument<String>("contact") ?: ""
                        try {
                            val intent = if (contact.matches(Regex("[0-9+\\-() ]+")) ) {
                                // 전화번호 직접 다이얼
                                Intent(Intent.ACTION_DIAL, Uri.parse("tel:${Uri.encode(contact)}"))
                            } else {
                                // 연락처 이름으로 검색
                                Intent(Intent.ACTION_PICK, ContactsContract.Contacts.CONTENT_URI)
                            }
                            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
                            startActivity(intent)
                            result.success(null)
                        } catch (e: Exception) {
                            result.error("UNAVAILABLE", "전화 앱을 열 수 없어요: ${e.message}", null)
                        }
                    }

                    // ── 문자 보내기 ──────────────────────────────────
                    "sendSms" -> {
                        val contact = call.argument<String>("contact") ?: ""
                        val message = call.argument<String>("message") ?: ""
                        try {
                            val uri = Uri.parse("smsto:${Uri.encode(contact)}")
                            val intent = Intent(Intent.ACTION_SENDTO, uri).apply {
                                putExtra("sms_body", message)
                                flags = Intent.FLAG_ACTIVITY_NEW_TASK
                            }
                            startActivity(intent)
                            result.success(null)
                        } catch (e: Exception) {
                            result.error("UNAVAILABLE", "문자 앱을 열 수 없어요: ${e.message}", null)
                        }
                    }

                    // ── 지도 열기 ────────────────────────────────────
                    "openMaps" -> {
                        val origin = call.argument<String>("origin") ?: ""
                        val destination = call.argument<String>("destination") ?: ""
                        val mode = call.argument<String>("mode") ?: "transit"
                        try {
                            // Google Maps 길찾기 URI
                            val modeParam = when (mode) {
                                "driving" -> "d"
                                "walking" -> "w"
                                "bicycling" -> "b"
                                else -> "r"  // transit
                            }
                            val uri = if (origin.isNotEmpty()) {
                                "https://maps.google.com/maps?saddr=${Uri.encode(origin)}&daddr=${Uri.encode(destination)}&dirflg=$modeParam"
                            } else {
                                "https://maps.google.com/maps?daddr=${Uri.encode(destination)}&dirflg=$modeParam"
                            }
                            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(uri)).apply {
                                flags = Intent.FLAG_ACTIVITY_NEW_TASK
                            }
                            startActivity(intent)
                            result.success(null)
                        } catch (e: Exception) {
                            result.error("UNAVAILABLE", "지도 앱을 열 수 없어요: ${e.message}", null)
                        }
                    }

                    // ── 음악 검색 ────────────────────────────────────
                    "openMusicSearch" -> {
                        val query = call.argument<String>("query") ?: ""
                        try {
                            // Spotify 앱 → 없으면 웹 검색
                            val spotifyUri = Uri.parse("spotify:search:${Uri.encode(query)}")
                            val intent = Intent(Intent.ACTION_VIEW, spotifyUri).apply {
                                flags = Intent.FLAG_ACTIVITY_NEW_TASK
                            }
                            if (intent.resolveActivity(packageManager) != null) {
                                startActivity(intent)
                            } else {
                                // 기본 미디어 플레이어
                                val mediaIntent = Intent(Intent.ACTION_VIEW).apply {
                                    type = "audio/*"
                                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                                }
                                startActivity(mediaIntent)
                            }
                            result.success(null)
                        } catch (e: Exception) {
                            result.error("UNAVAILABLE", "음악 앱을 열 수 없어요: ${e.message}", null)
                        }
                    }

                    // ── YouTube 검색 ─────────────────────────────────
                    "openYouTube" -> {
                        val query = call.argument<String>("query") ?: ""
                        try {
                            val uri = Uri.parse("https://www.youtube.com/results?search_query=${Uri.encode(query)}")
                            val intent = Intent(Intent.ACTION_VIEW, uri).apply {
                                flags = Intent.FLAG_ACTIVITY_NEW_TASK
                            }
                            startActivity(intent)
                            result.success(null)
                        } catch (e: Exception) {
                            result.error("UNAVAILABLE", "유튜브를 열 수 없어요: ${e.message}", null)
                        }
                    }

                    // ── 카카오톡 메시지 ──────────────────────────────
                    "sendKakaoMessage" -> {
                        try {
                            // 카카오톡 링크 (KakaoTalk SDK 없이 딥링크)
                            val intent = Intent(Intent.ACTION_MAIN).apply {
                                addCategory(Intent.CATEGORY_LAUNCHER)
                                setClassName("com.kakao.talk", "com.kakao.talk.activity.SplashActivity")
                                flags = Intent.FLAG_ACTIVITY_NEW_TASK
                            }
                            if (intent.resolveActivity(packageManager) != null) {
                                startActivity(intent)
                                result.success(null)
                            } else {
                                result.error("UNAVAILABLE", "카카오톡이 설치되지 않았어요.", null)
                            }
                        } catch (e: Exception) {
                            result.error("UNAVAILABLE", "카카오톡을 열 수 없어요: ${e.message}", null)
                        }
                    }

                    // ── 스마트홈 제어 ─────────────────────────────────
                    "smartHomeControl" -> {
                        // Google Home 앱 열기 (실제 제어는 Google Home SDK 필요)
                        try {
                            val intent = packageManager.getLaunchIntentForPackage("com.google.android.apps.chromecast.app")
                            if (intent != null) {
                                intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
                                startActivity(intent)
                                result.success(null)
                            } else {
                                result.error("UNAVAILABLE", "Google Home 앱이 설치되지 않았어요.", null)
                            }
                        } catch (e: Exception) {
                            result.error("UNAVAILABLE", e.message, null)
                        }
                    }

                    // ── 위젯 리마인더 텍스트 업데이트 ───────────────────────────
                    "updateWidgetReminder" -> {
                        val text = call.argument<String>("text") ?: "예정된 리마인더가 없어요"
                        LouisWidget.saveNextReminder(applicationContext, text)
                        result.success(null)
                    }

                    // ── 위젯 강제 새로고침 ────────────────────────────────────
                    "refreshWidget" -> {
                        LouisWidget.forceUpdate(applicationContext)
                        result.success(null)
                    }

                    else -> result.notImplemented()
                }
            }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // 딥링크: 위젯에서 앱 실행 시 특정 탭 열기
        handleWidgetIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleWidgetIntent(intent)
    }

    private fun handleWidgetIntent(intent: Intent?) {
        val action = intent?.getStringExtra("widget_action") ?: return
        flutterEngine?.dartExecutor?.binaryMessenger?.let { messenger ->
            MethodChannel(messenger, CHANNEL).invokeMethod(
                "widgetAction",
                mapOf("action" to action)
            )
        }
    }
}
