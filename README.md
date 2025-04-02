# Spotify Hub for Raspberry Pi

A sleek, Spotify-inspired dashboard for Raspberry Pi with 1024x600 displays. Monitor your currently playing music, view track history, check system stats, and display time in a beautiful dark interface.

## ✨ Features

### 🎧 Spotify Integration
- Real-time display of currently playing track with album artwork
- Live progress bar with time indicators
- Playback status (playing/paused)
- History of recently played tracks

### 📊 System Monitoring
- CPU temperature
- CPU load percentage
- Memory usage
- Disk space

### 🕒 Digital Clock
- Live updating time with animated colons
- Current date with day of week
- Spotify-themed styling

### 🎨 Responsive Design
- Optimized for 1024x600 Raspberry Pi displays
- Adaptive layout for different screen sizes
- Spotify-inspired dark theme with gradient accents

## 📸 Screenshots

[*(Screenshot)*](https://ibb.co/KcgRnYTJ)

## 📋 Requirements

- Raspberry Pi (3 or 4 recommended)
- 1024x600 display
- Python 3.6+
- Spotify Premium account
- Spotify Developer API credentials

## Limiting recent tracks
- To limit recent tracks you can edit these lines for better viewing
         `if (trackHistory.length > 6) {
                    trackHistory = trackHistory.slice(0, 6);
                }
            }`