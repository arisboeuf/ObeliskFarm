package com.paia.obeliskfarm

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.database.ContentObserver
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.provider.MediaStore
import android.util.Log
import androidx.core.app.NotificationCompat
import java.io.File

class ScreenshotMonitorService : Service() {
    
    private var contentObserver: ContentObserver? = null
    private val handler = Handler(Looper.getMainLooper())
    private val imageProcessor = ImageProcessor(this)
    private var lastProcessedPath: String? = null
    
    companion object {
        private const val TAG = "ScreenshotMonitor"
        private const val CHANNEL_ID = "screenshot_monitor_channel"
        private const val NOTIFICATION_ID = 1
    }
    
    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startMonitoring()
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(NOTIFICATION_ID, createNotification())
        return START_STICKY // Service wird automatisch neu gestartet, wenn er beendet wird
    }
    
    override fun onBind(intent: Intent?): IBinder? = null
    
    override fun onDestroy() {
        super.onDestroy()
        stopMonitoring()
    }
    
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                getString(R.string.notification_channel_name),
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = getString(R.string.notification_channel_description)
            }
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }
    
    private fun createNotification(): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(getString(R.string.service_running))
            .setSmallIcon(android.R.drawable.ic_menu_camera)
            .setOngoing(true)
            .build()
    }
    
    private fun startMonitoring() {
        val uri = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            MediaStore.Images.Media.EXTERNAL_CONTENT_URI
        } else {
            MediaStore.Images.Media.EXTERNAL_CONTENT_URI
        }
        
        contentObserver = object : ContentObserver(handler) {
            override fun onChange(selfChange: Boolean, uri: Uri?) {
                super.onChange(selfChange, uri)
                uri?.let { checkForNewScreenshot(it) }
            }
        }
        
        contentResolver.registerContentObserver(
            uri,
            true,
            contentObserver!!
        )
        
        Log.d(TAG, "Screenshot-Überwachung gestartet")
    }
    
    private fun stopMonitoring() {
        contentObserver?.let {
            contentResolver.unregisterContentObserver(it)
            contentObserver = null
        }
        Log.d(TAG, "Screenshot-Überwachung gestoppt")
    }
    
    private fun checkForNewScreenshot(uri: Uri) {
        try {
            val cursor = contentResolver.query(
                uri,
                arrayOf(
                    MediaStore.Images.Media._ID,
                    MediaStore.Images.Media.DATA,
                    MediaStore.Images.Media.DATE_ADDED,
                    MediaStore.Images.Media.DISPLAY_NAME
                ),
                null,
                null,
                "${MediaStore.Images.Media.DATE_ADDED} DESC LIMIT 1"
            )
            
            cursor?.use {
                if (it.moveToFirst()) {
                    val pathIndex = it.getColumnIndex(MediaStore.Images.Media.DATA)
                    val nameIndex = it.getColumnIndex(MediaStore.Images.Media.DISPLAY_NAME)
                    val dateIndex = it.getColumnIndex(MediaStore.Images.Media.DATE_ADDED)
                    
                    if (pathIndex >= 0 && nameIndex >= 0 && dateIndex >= 0) {
                        val path = it.getString(pathIndex)
                        val name = it.getString(nameIndex)
                        val dateAdded = it.getLong(dateIndex)
                        
                        // Prüfe, ob es ein Screenshot ist (Name enthält "Screenshot" oder "screen")
                        if (path != null && name != null && 
                            (name.contains("Screenshot", ignoreCase = true) || 
                             name.contains("screen", ignoreCase = true) ||
                             path.contains("Screenshot", ignoreCase = true))) {
                            
                            // Verhindere doppelte Verarbeitung
                            if (path != lastProcessedPath) {
                                lastProcessedPath = path
                                Log.d(TAG, "Neuer Screenshot gefunden: $name")
                                
                                // Verarbeite das Bild
                                processImage(path, name)
                            }
                        }
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Fehler beim Prüfen auf Screenshots", e)
        }
    }
    
    private fun processImage(imagePath: String, imageName: String) {
        Thread {
            try {
                val file = File(imagePath)
                if (file.exists()) {
                    Log.d(TAG, "Verarbeite Bild: $imageName")
                    
                    // Rufe die Bildverarbeitungslogik auf
                    val result = imageProcessor.processImage(imagePath)
                    
                    if (result.success) {
                        Log.d(TAG, "Bild erfolgreich verarbeitet: ${result.message}")
                        // Hier könntest du weitere Aktionen durchführen, z.B. eine Benachrichtigung senden
                    } else {
                        Log.w(TAG, "Bildverarbeitung fehlgeschlagen: ${result.message}")
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Fehler bei der Bildverarbeitung", e)
            }
        }.start()
    }
}

