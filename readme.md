S3M to MIDI Converter GUI v1.0

<img width="736" height="492" alt="imagen" src="https://github.com/user-attachments/assets/07a2e62e-4cda-4e84-bba7-243a93a619f3" />


A high-fidelity S3M (Scream Tracker 3) to MIDI converter. Unlike standard converters, this tool focuses on preserving the "feel" of tracker music by accurately translating portamento, legato, and volume slides using high-resolution pitch wheel data.
Features

    High-Resolution Pitch Tracking: Automatically calculates pitch wheel values based on a 24-semitone range (±24st) to capture smooth slides and vibrato.

    Intuitive Sample Mapper:

        Map S3M samples to specific General MIDI (GM) instruments or drum hits.

        Solo/Mute specific channels before exporting.

        Octave Shift: Adjust individual instruments by ±8 octaves.

    Audio Preview: Built-in sample player to hear the raw S3M samples while mapping.

    Auto-Save Presets: Generates a .config file next to your S3M to remember your mappings for future sessions.

    Drag & Drop: Simply drop your .s3m file into the app to start.

Dependencies

To run this project from source, you will need Python 3.8+ and the following libraries:
Library	Purpose
mido	MIDI file generation
libxmplite	S3M module parsing/playback engine
pygame	Audio preview engine
tkinterdnd2	Drag and Drop functionality
Installation

Install the required packages via pip:
Bash

pip install mido libxmplite pygame tkinterdnd2

How to Use

    Launch the App: Open "s3mToMid GUI v1.0 .py" or run the script using python "s3mToMid GUI v1.0 .py"

    Import: Drag an .s3m file onto the main window.

    Configure: * Use the Play button to hear a sample, change sample speed % to hear it a different pitch.

        Select if the sample is an Instrument or a Drum.

        Assign the desired General Midi Sound and adjust the Octave if necessary.

    Preview/Export:

        Click PREVIEW to generate a temporary MIDI and open it immediately, combine this with solo and mute functions to properly detect right octave and instrument.

        Click SAVE CONFIG to store your instrument/drum/octave/solo/mute choices in .config file next to where your .s3m file is located.

        Click EXPORT FINAL to save the finished .mid file in your source folder.

Technical Details

This converter maps S3M channels to MIDI channels dynamically. It uses RPN 0 (Pitch Bend Sensitivity) to set MIDI channels to a 24-semitone range. This allows the converter to translate the S3M "Period" values into precise MIDI Pitch Wheel movements

All instruments have 127 velocity and 127 CC7 Volume, the volume conversion is controlled by the use of CC11 Expression

For drums it's different, they get Velocity conversion instead of CC11 since the CC11 approach doesn't work if you have several drums at once

This converter was specifically designed to convert .S3M Krawall GBA files (specifically the Sims Bustin' Out, URBZ and Sims 2 gba games) exported with https://github.com/MCJack123/UnkrawerterGBA , but it should work with any standard .S3M from what I've tested


