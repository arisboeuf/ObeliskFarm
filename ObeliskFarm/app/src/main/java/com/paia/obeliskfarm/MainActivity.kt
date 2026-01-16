package com.paia.obeliskfarm

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {
    
    private lateinit var toggleButton: Button
    private lateinit var statusText: TextView
    private lateinit var countText: TextView
    private lateinit var lastProcessedText: TextView
    
    private val isMonitoring = MutableStateFlow(false)
    private val processedCount = MutableStateFlow(0)
    private val lastProcessed = MutableStateFlow<String?>(null)
    
    private val PERMISSION_REQUEST_CODE = 100

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        toggleButton = findViewById(R.id.toggleButton)
        statusText = findViewById(R.id.statusText)
        countText = findViewById(R.id.countText)
        lastProcessedText = findViewById(R.id.lastProcessedText)
        
        // UI-Status beobachten
        lifecycleScope.launch {
            isMonitoring.collect { monitoring ->
                toggleButton.text = if (monitoring) {
                    getString(R.string.stop_monitoring)
                } else {
                    getString(R.string.start_monitoring)
                }
                statusText.text = if (monitoring) {
                    getString(R.string.service_running)
                } else {
                    getString(R.string.service_stopped)
                }
            }
        }
        
        lifecycleScope.launch {
            processedCount.collect { count ->
                countText.text = count.toString()
            }
        }
        
        lifecycleScope.launch {
            lastProcessed.collect { time ->
                lastProcessedText.text = time ?: getString(R.string.no_images)
            }
        }
        
        toggleButton.setOnClickListener {
            if (isMonitoring.value) {
                stopMonitoring()
            } else {
                startMonitoring()
            }
        }
        
        // Prüfe Berechtigungen
        checkPermissions()
    }
    
    private fun checkPermissions() {
        val permissions = mutableListOf<String>()
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_MEDIA_IMAGES) 
                != PackageManager.PERMISSION_GRANTED) {
                permissions.add(Manifest.permission.READ_MEDIA_IMAGES)
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) 
                != PackageManager.PERMISSION_GRANTED) {
                permissions.add(Manifest.permission.POST_NOTIFICATIONS)
            }
        } else {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE) 
                != PackageManager.PERMISSION_GRANTED) {
                permissions.add(Manifest.permission.READ_EXTERNAL_STORAGE)
            }
        }
        
        if (permissions.isNotEmpty()) {
            ActivityCompat.requestPermissions(
                this,
                permissions.toTypedArray(),
                PERMISSION_REQUEST_CODE
            )
        }
    }
    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERMISSION_REQUEST_CODE) {
            val allGranted = grantResults.all { it == PackageManager.PERMISSION_GRANTED }
            if (!allGranted) {
                Toast.makeText(this, "Berechtigungen werden benötigt!", Toast.LENGTH_LONG).show()
            }
        }
    }
    
    private fun startMonitoring() {
        if (checkPermissionsGranted()) {
            val serviceIntent = Intent(this, ScreenshotMonitorService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                ContextCompat.startForegroundService(this, serviceIntent)
            } else {
                startService(serviceIntent)
            }
            isMonitoring.value = true
        } else {
            Toast.makeText(this, "Bitte Berechtigungen erteilen!", Toast.LENGTH_SHORT).show()
            checkPermissions()
        }
    }
    
    private fun stopMonitoring() {
        val serviceIntent = Intent(this, ScreenshotMonitorService::class.java)
        stopService(serviceIntent)
        isMonitoring.value = false
    }
    
    private fun checkPermissionsGranted(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(this, Manifest.permission.READ_MEDIA_IMAGES) == 
                PackageManager.PERMISSION_GRANTED &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == 
                PackageManager.PERMISSION_GRANTED
        } else {
            ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE) == 
                PackageManager.PERMISSION_GRANTED
        }
    }
}

