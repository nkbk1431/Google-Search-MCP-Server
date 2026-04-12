package com.yourname.louis

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews

/**
 * 루이스 홈 화면 위젯
 *
 * 표시 정보:
 *  - 다가오는 리마인더 제목
 *  - 음성 입력 버튼 (앱을 열고 웨이크워드 모드 진입)
 *  - 앱 열기 버튼
 *
 * 위젯 → 앱 통신: MainActivity.handleWidgetIntent()가 "widget_action" Extra를 처리합니다.
 */
class LouisWidget : AppWidgetProvider() {

    companion object {
        const val ACTION_MIC = "com.yourname.louis.widget.ACTION_MIC"
        const val ACTION_OPEN = "com.yourname.louis.widget.ACTION_OPEN"

        /** SharedPreferences 키 — Flutter 앱이 이 값을 업데이트합니다. */
        private const val PREFS_NAME = "LouisWidgetPrefs"
        private const val KEY_REMINDER = "next_reminder"

        /** 위젯을 외부에서 강제 갱신할 때 호출합니다. */
        fun forceUpdate(context: Context) {
            val manager = AppWidgetManager.getInstance(context)
            val ids = manager.getAppWidgetIds(
                ComponentName(context, LouisWidget::class.java)
            )
            val intent = Intent(context, LouisWidget::class.java).apply {
                action = AppWidgetManager.ACTION_APPWIDGET_UPDATE
                putExtra(AppWidgetManager.EXTRA_APPWIDGET_IDS, ids)
            }
            context.sendBroadcast(intent)
        }

        /** Flutter 앱이 SharedPreferences에 리마인더 텍스트를 저장할 때 사용하는 헬퍼 */
        fun saveNextReminder(context: Context, text: String) {
            context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                .edit()
                .putString(KEY_REMINDER, text)
                .apply()
            forceUpdate(context)
        }
    }

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray,
    ) {
        for (id in appWidgetIds) {
            updateWidget(context, appWidgetManager, id)
        }
    }

    private fun updateWidget(
        context: Context,
        appWidgetManager: AppWidgetManager,
        widgetId: Int,
    ) {
        val views = RemoteViews(context.packageName, R.layout.louis_widget_layout)

        // ── 리마인더 텍스트 ──────────────────────────────────────────
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val reminderText = prefs.getString(KEY_REMINDER, null)
            ?: "예정된 리마인더가 없어요"
        views.setTextViewText(R.id.widget_reminder_text, reminderText)

        // ── 음성 입력 버튼 PendingIntent ────────────────────────────
        val micIntent = Intent(context, MainActivity::class.java).apply {
            action = ACTION_MIC
            putExtra("widget_action", "mic")
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val micPi = PendingIntent.getActivity(
            context, 0, micIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        views.setOnClickPendingIntent(R.id.widget_btn_mic, micPi)

        // ── 앱 열기 버튼 PendingIntent ────────────────────────────
        val openIntent = Intent(context, MainActivity::class.java).apply {
            action = ACTION_OPEN
            putExtra("widget_action", "open")
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val openPi = PendingIntent.getActivity(
            context, 1, openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        views.setOnClickPendingIntent(R.id.widget_btn_open, openPi)

        appWidgetManager.updateAppWidget(widgetId, views)
    }
}
