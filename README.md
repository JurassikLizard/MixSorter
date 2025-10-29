# MixSorter
Python script to auto sort your Spotify playlist to take advantage of new auto Mix feature.
A smart Spotify playlist organizer that arranges tracks using **harmonic mixing** (Camelot Wheel) and **tempo transitions** for smooth, DJ-style flow.

REQUIRES  Spotify developer app with callback url to http://127.0.0.1:callback
(look up/ask an LLM how to do this)

## Features

- 🎵 **Harmonic compatibility** - Uses Camelot key notation for musical transitions
- 🎚️ **Smart tempo matching** - Handles BPM changes and double/half-time relationships
- 📈 **Energy flow** - Builds momentum early, maintains dynamics, winds down naturally
- 🔄 **Position-aware** - Considers track placement in the overall set

## Example Output

The algorithm analyzes each transition and assigns a score (lower = smoother):

```
81. One Dance                      (3A, 104 BPM) → Stronger                       (3A, 104 BPM) [Score: -0.3]
82. Stronger                       (3A, 104 BPM) → Infinity Repeating (2013 Demo) (3A, 110 BPM) [Score: 23.7]
83. Infinity Repeating (2013 Demo) (3A, 110 BPM) → Instant Crush (feat. Julian Ca (6B, 110 BPM) [Score: 149.9]
84. Instant Crush (feat. Julian Ca (6B, 110 BPM) → Promiscuous                    (6B, 114 BPM) [Score: 11.2]
...
89. Devil In A New Dress           (4B, 80 BPM) → Runaway                        (3B, 85 BPM) [Score: 20.5]
90. Runaway                        (3B, 85 BPM) → Good Life                      (3A, 83 BPM) [Score: 21.3]
91. Good Life                      (3A, 83 BPM) → Homecoming                     (3A, 87 BPM) [Score: 7.7]
92. Homecoming                     (3A, 87 BPM) → Run This Town                  (3A, 87 BPM) [Score: 1.2]
```

**Perfect transitions** (same key, similar BPM) score near 0, while incompatible jumps score 100+.

## Usage

Run the script with your Spotify credentials - it will fetch track features, analyze transitions, and create a new sorted playlist.

---

*Powered by Spotify API and the Camelot Wheel harmonic mixing system*
