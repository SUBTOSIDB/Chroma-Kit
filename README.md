# Chroma Kit

UI theme presets for Krita by SubToSidb.

Retints the entire Krita interface with QSS themes, Gradients,
glow accents, rounded controls, letter-spaced labels. Ships 29 themes, plus a live preview panel.

## Install

**Windows:**

1. Copy the `chroma_kit` folder into:

   `C:\Users\<you>\AppData\Roaming\krita\pykrita\`

2. Copy `kritapykrita_chroma_kit.desktop` into the same `pykrita` folder.

   (No admin needed. If you installed Krita for all users instead, use
   `<Krita install>\share\krita\pykrita\` — but the AppData path is the normal
   one and doesn't require write access to Program Files.)

3. Restart Krita.

4. Settings -> Configure Krita -> Python Plugin Manager -> tick "Chroma Kit"
   -> OK.

5. Restart Krita again.

6. Tools -> Settings -> Chroma Kit: Load Theme. Pick a theme; it previews
   live in the picker and applies on Load. Your last choice is remembered
   across restarts.

**Linux:**

1. Copy `chroma_kit` into `~/.local/share/krita/pykrita/`.
2. Copy `kritapykrita_chroma_kit.desktop` there too.
3. Restart Krita, enable the plugin in the Python Plugin Manager, restart.


## Notes

- Switching Presets CAN sometimes crash Krita, which then gets applied on the next reload.
  Save every single time you are going to change your Preset, Some things the Plugin cannot touch are Themes
  You can mix match Kritas Themes to work with it, this applies to a handful of tiny UI elements.
  But for the most part the Presets work on everything including custom dockers and anything UI related. 

- Themes are plain JSON in `chroma_kit/presets/`. Drop a new `.json` file in
  and restart Krita to add your own — each needs a `name` key and either
  `custom_qss` (raw QSS) or the base color keys (`bg`, `accent`, `accent_bright`,
  `text`, ...). Look at any shipped preset for the shape.
- "Chroma Kit: Re-apply Theme" in Tools -> Settings re-runs the theme if
  Krita's UI ever gets visually stuck.
- Uninstalling: pick "No Preset" in the picker first, then delete the folder
  and the .desktop file.
- Requires Krita 5.x with PyQt5 (standard for current Krita builds).

- You will most likely have to use AI to create your own Presets, the Preset Files are massive
  and would take you days to create a whole custom Preset by Hand lmao. Use the ones already made as References if you do so.

- If you have any issues just Join my server and msg me! 
  Or for just supportin ♥

  https://discord.gg/xXbYg5b8Nj

  https://x.com/subtosidbyt
 
