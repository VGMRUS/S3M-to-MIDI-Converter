import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo
import libxmplite
import struct
import io
import wave
import os
import math
import pygame
import tempfile
import json
import tkinter as tk
from tkinter import ttk, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD

# --- CONSTANTS ---
GM_INST_NAMES = ["Acoustic Grand Piano", "Bright Acoustic Piano", "Electric Grand Piano", "Honky-tonk Piano", "Electric Piano 1", "Electric Piano 2", "Harpsichord", "Clavi", "Celesta", "Glockenspiel", "Music Box", "Vibraphone", "Marimba", "Xylophone", "Tubular Bells", "Dulcimer", "Drawbar Organ", "Percussive Organ", "Rock Organ", "Church Organ", "Reed Organ", "Accordion", "Harmonica", "Tango Accordion", "Acoustic Guitar (nylon)", "Acoustic Guitar (steel)", "Electric Guitar (jazz)", "Electric Guitar (clean)", "Electric Guitar (muted)", "Overdriven Guitar", "Distortion Guitar", "Guitar harmonics", "Acoustic Bass", "Electric Bass (finger)", "Electric Bass (pick)", "Fretless Bass", "Slap Bass 1", "Slap Bass 2", "Synth Bass 1", "Synth Bass 2", "Violin", "Viola", "Cello", "Contrabass", "Tremolo Strings", "Pizzicato Strings", "Orchestral Harp", "Timpani", "String Ensemble 1", "String Ensemble 2", "SynthStrings 1", "SynthStrings 2", "Choir Aahs", "Voice Oohs", "Synth Voice", "Orchestra Hit", "Trumpet", "Trombone", "Tuba", "Muted Trumpet", "French Horn", "Brass Section", "SynthBrass 1", "SynthBrass 2", "Soprano Sax", "Alto Sax", "Tenor Sax", "Baritone Sax", "Oboe", "English Horn", "Bassoon", "Clarinet", "Piccolo", "Flute", "Recorder", "Pan Flute", "Blown Bottle", "Shakuhachi", "Whistle", "Ocarina", "Lead 1 (square)", "Lead 2 (sawtooth)", "Lead 3 (calliope)", "Lead 4 (chiff)", "Lead 5 (charang)", "Lead 6 (voice)", "Lead 7 (fifths)", "Lead 8 (bass + lead)", "Pad 1 (new age)", "Pad 2 (warm)", "Pad 3 (polysynth)", "Pad 4 (choir)", "Pad 5 (bowed)", "Pad 6 (metallic)", "Pad 7 (halo)", "Pad 8 (sweep)", "FX 1 (rain)", "FX 2 (soundtrack)", "FX 3 (crystal)", "FX 4 (atmosphere)", "FX 5 (brightness)", "FX 6 (goblins)", "FX 7 (echoes)", "FX 8 (sci-fi)", "Sitar", "Banjo", "Shamisen", "Koto", "Kalimba", "Bag pipe", "Fiddle", "Shanai", "Tinkle Bell", "Agogo", "Steel Drums", "Woodblock", "Taiko Drum", "Melodic Tom", "Synth Drum", "Reverse Cymbal", "Guitar Fret Noise", "Breath Noise", "Seashore", "Bird Tweet", "Telephone Ring", "Helicopter", "Applause", "Gunshot"]
GM_DRUM_NAMES = {35: "Acoustic Bass Drum", 36: "Bass Drum 1", 37: "Side Stick", 38: "Acoustic Snare", 39: "Hand Clap", 40: "Electric Snare", 41: "Low Floor Tom", 42: "Closed Hi Hat", 43: "High Floor Tom", 44: "Pedal Hi-Hat", 45: "Low Tom", 46: "Open Hi Hat", 47: "Low-Mid Tom", 48: "Hi-Mid Tom", 49: "Crash Cymbal 1", 50: "High Tom", 51: "Ride Cymbal 1", 52: "Chinese Cymbal", 53: "Ride Bell", 54: "Tambourine", 55: "Splash Cymbal", 56: "Cowbell", 57: "Crash Cymbal 2", 58: "Vibraslap", 59: "Ride Cymbal 2", 60: "Hi Bongo", 61: "Low Bongo", 62: "Mute Hi Conga", 63: "Open Hi Conga", 64: "Low Conga", 65: "High Timbale", 66: "Low Timbale", 67: "High Agogo", 68: "Low Agogo", 69: "Cabasa", 70: "Maracas", 71: "Short Whistle", 72: "Long Whistle", 73: "Short Guiro", 74: "Long Guiro", 75: "Claves", 76: "Hi Wood Block", 77: "Low Wood Block", 78: "Mute Cuica", 79: "Open Cuica", 80: "Mute Triangle", 81: "Open Triangle"}
GM_INST_LIST = [f"{i}: {name}" for i, name in enumerate(GM_INST_NAMES)]
GM_DRUMS_LIST = [f"{k}: {v}" for k, v in sorted(GM_DRUM_NAMES.items())]

def clamp(v, mn=0, mx=127): return max(mn, min(mx, int(v)))

# --- AUDIO PREVIEW ENGINE ---
try:
    pygame.mixer.pre_init(44100, -16, 1, 1024); pygame.mixer.init()
    HAS_AUDIO = True
except: HAS_AUDIO = False

def play_sample(path, audio_ptr, size, spd):
    """Plays the raw S3M sample data for preview purposes."""
    if not HAS_AUDIO or size <= 0: return
    try:
        sf = max(5, min(500, int(spd))) / 100.0
        with open(path, 'rb') as f: f.seek(audio_ptr); raw = f.read(size)
        bio = io.BytesIO()
        with wave.open(bio, 'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(1); wf.setframerate(int(16000*sf)); wf.writeframes(raw)
        bio.seek(0); pygame.mixer.Sound(bio).play()
    except: pass

def deep_scan_s3m(path):
    """Scans the S3M binary to extract sample names and pointers."""
    samps = []
    try:
        with open(path, 'rb') as f: data = f.read()
        p = 0
        while True:
            p = data.find(b'SCRS', p)
            if p == -1: break
            bp = p - 0x4C
            if bp >= 0:
                h = data[bp : bp + 80]
                name = h[0x30:0x4C].decode('latin-1', 'ignore').strip()
                sz = struct.unpack('<H', h[0x10:0x12])[0] + (h[0x12] << 16)
                ptr = (struct.unpack('<H', h[0x0D:0x0F])[0] + (h[0x0F] << 16)) // 16
                if ptr < len(data) and sz > 0: samps.append({'name': name if name else f"Smp {len(samps)+1}", 'size': sz, 'audio_ptr': ptr})
            p += 4
    except: pass
    return samps

# --- CONVERSION LOGIC ---
def run_high_res_conversion(path, mapping, is_preview=False):
    try:
        xmp = libxmplite.Xmp(); xmp.load(path); mod_info = xmp.module_info()
        out = os.path.join(tempfile.gettempdir(), "s3m_preview.mid") if is_preview else path.replace(".s3m", "_Converted_v1.mid")
        
        any_solo = any(m['solo'] for m in mapping.values())
        
        PPQ, TICKS_PER_ROW = 960, 240
        mid = MidiFile(ticks_per_beat=PPQ)
        num_s3m_chn = mod_info.chn

        xmp.start(44100)
        channels_to_export = set()
        
        while True:
            fi = xmp.play_frame()
            if fi.loop_count > 0: break
            for ch in range(num_s3m_chn):
                c_info = fi.channel_info[ch]
                if c_info and c_info.event and c_info.event.note > 0:
                    ins_id = c_info.event.ins - 1
                    m = mapping.get(ins_id, {'type': 'inst', 'solo': False, 'mute': False})
                    if any_solo: active = m.get('solo', False)
                    else: active = not m.get('mute', False)
                    if active and m['type'] == 'inst': channels_to_export.add(ch)

        sorted_melodic = sorted(list(channels_to_export))
        s3m_to_midi, pool = {}, [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15]
        for i, s_ch in enumerate(sorted_melodic):
            if i < len(pool): s3m_to_midi[s_ch] = pool[i]
        
        xmp.restart()
        tempo_tr = MidiTrack(); tempo_tr.append(MetaMessage('track_name', name="Tempo", time=0)); mid.tracks.append(tempo_tr)

        mel_tracks, drum_tracks = {}, {}
        act_note, ref_per, last_p, last_v, last_pan, last_i = [-1]*num_s3m_chn, [0.0]*num_s3m_chn, [None]*num_s3m_chn, [-1]*num_s3m_chn, [-1]*num_s3m_chn, [-1]*num_s3m_chn
        t_mel, t_drum, t_tempo = [0]*num_s3m_chn, [0]*num_s3m_chn, 0
        l_bpm, l_row, first = -1.0, -1, True

        while True:
            fi = xmp.play_frame()
            if fi.loop_count > 0: break
            tpf = TICKS_PER_ROW // max(1, fi.speed)
            if not first:
                t_tempo += tpf
                for i in range(num_s3m_chn): t_mel[i] += tpf; t_drum[i] += tpf
            
            bpm = (float(fi.bpm) * 6.0 / float(max(1, fi.speed))) * 1.001001001
            if abs(bpm - l_bpm) > 0.0001:
                tempo_tr.append(MetaMessage('set_tempo', tempo=bpm2tempo(bpm), time=t_tempo))
                t_tempo, l_bpm = 0, bpm

            new_row = (fi.row != l_row)
            for ch in range(num_s3m_chn):
                c_info = fi.channel_info[ch]
                if not c_info: continue
                ev = c_info.event 

                if new_row and ev and ev.note > 0:
                    ins_id = ev.ins - 1
                    m = mapping.get(ins_id, {'type': 'inst', 'val': 0, 'octave': 0, 'solo': False, 'mute': False})
                    
                    if any_solo: is_active = m.get('solo', False)
                    else: is_active = not m.get('mute', False)

                    if not is_active:
                        if act_note[ch] != -1 and ch in s3m_to_midi:
                            m_ch = s3m_to_midi[ch]
                            mel_tracks[ch].append(Message('note_off', note=act_note[ch], time=t_mel[ch], channel=m_ch))
                            act_note[ch], t_mel[ch] = -1, 0
                        continue

                    if m['type'] == 'drum':
                        if ch not in drum_tracks:
                            drum_tracks[ch] = MidiTrack(); drum_tracks[ch].append(MetaMessage('track_name', name=f"Drums {ch+1}", time=0))
                        dn, dv = clamp(m['val']), clamp((c_info.volume / 64.0) * 127, 1, 127)
                        drum_tracks[ch].append(Message('note_on', note=dn, velocity=dv, time=t_drum[ch], channel=9))
                        drum_tracks[ch].append(Message('note_off', note=dn, velocity=0, time=60, channel=9)); t_drum[ch] = -60
                    
                    elif ch in s3m_to_midi:
                        m_ch = s3m_to_midi[ch]
                        if ch not in mel_tracks:
                            mel_tracks[ch] = MidiTrack(); mel_tracks[ch].append(MetaMessage('track_name', name=f"Ch {ch+1}", time=0))
                            for cc, val in [(101,0), (100,0), (6,24), (7,127)]:
                                mel_tracks[ch].append(Message('control_change', control=cc, value=val, time=0, channel=m_ch))
                        
                        is_port = (ev.fxt == 3 or ev.fxt == 7)
                        if not is_port:
                            if act_note[ch] != -1:
                                mel_tracks[ch].append(Message('note_off', note=act_note[ch], time=t_mel[ch], channel=m_ch)); t_mel[ch] = 0
                            if ins_id >= 0 and ins_id != last_i[ch]:
                                mel_tracks[ch].append(Message('program_change', program=clamp(m['val']), time=t_mel[ch], channel=m_ch))
                                t_mel[ch], last_i[ch] = 0, ins_id
                            mn = clamp(ev.note + 11 + (m['octave'] * 12))
                            mel_tracks[ch].append(Message('note_on', note=mn, velocity=127, time=t_mel[ch], channel=m_ch))
                            act_note[ch], ref_per[ch], last_p[ch], t_mel[ch] = mn, float(c_info.period), 0, 0
                            mel_tracks[ch].append(Message('pitchwheel', pitch=0, time=0, channel=m_ch))

                if ch in mel_tracks and act_note[ch] != -1:
                    m_ch = s3m_to_midi[ch]
                    mv = clamp((c_info.volume / 64.0) * 127)
                    if mv != last_v[ch]: mel_tracks[ch].append(Message('control_change', control=11, value=mv, time=t_mel[ch], channel=m_ch)); t_mel[ch], last_v[ch] = 0, mv
                    mp = clamp(c_info.pan / 2)
                    if mp != last_pan[ch]: mel_tracks[ch].append(Message('control_change', control=10, value=mp, time=t_mel[ch], channel=m_ch)); t_mel[ch], last_pan[ch] = 0, mp
                    if c_info.period > 0 and ref_per[ch] > 0:
                        try:
                            diff_st = math.log2(ref_per[ch] / float(c_info.period)) * 12.0
                            pv = int((diff_st / 24.0) * 8191)
                            pv = max(-8192, min(8191, pv))
                            if pv != last_p[ch]:
                                mel_tracks[ch].append(Message('pitchwheel', pitch=pv, time=t_mel[ch], channel=m_ch))
                                t_mel[ch], last_p[ch] = 0, pv
                        except: pass
            l_row, first = fi.row, False

        for c in sorted(mel_tracks.keys()): mid.tracks.append(mel_tracks[c])
        for c in sorted(drum_tracks.keys()): mid.tracks.append(drum_tracks[c])
        mid.save(out); xmp.release()
        return True, out
    except Exception as e: return False, str(e)

# --- GUI INTERFACE ---
class SampleMapper(tk.Toplevel):
    def __init__(self, parent, path):
        super().__init__(parent)
        self.path = path
        self.config_path = os.path.splitext(self.path)[0] + ".config"
        self.samples = deep_scan_s3m(path)
        
        self.title("S3M to MIDI Converter GUI v1.0 - Mapping"); self.geometry("1180x700"); self.config(bg="#111")
        mf = tk.Frame(self, bg="#111"); mf.pack(fill="both", expand=True)
        canvas = tk.Canvas(mf, bg="#111", highlightthickness=0); scroll = ttk.Scrollbar(mf, orient="vertical", command=canvas.yview)
        sf = tk.Frame(canvas, bg="#111"); sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=sf, anchor="nw"); canvas.configure(yscrollcommand=scroll.set); canvas.pack(side="left", fill="both", expand=True); scroll.pack(side="right", fill="y")
        
        self.rows = []
        for i, s in enumerate(self.samples):
            f = tk.Frame(sf, bg="#222", pady=3); f.pack(fill="x", padx=10, pady=1)
            tk.Label(f, text=f"{i+1:02}", fg="#777", bg="#222", width=3).pack(side="left")
            tk.Label(f, text=s['name'][:18], fg="#00ffcc", bg="#222", width=18, anchor="w", font=("Arial", 9, "bold")).pack(side="left")
            
            s_var = tk.BooleanVar(value=False); m_var = tk.BooleanVar(value=False)
            def t_s(v=s_var, b=None): v.set(not v.get()); b.config(bg="#E6DB74" if v.get() else "#444", fg="black" if v.get() else "white")
            def t_m(v=m_var, b=None): v.set(not v.get()); b.config(bg="#F92672" if v.get() else "#444")
            
            btn_s = tk.Button(f, text="S", width=2, bg="#444", fg="white", font=("Arial", 8, "bold")); btn_s.config(command=lambda v=s_var, b=btn_s: t_s(v,b)); btn_s.pack(side="left", padx=2)
            btn_m = tk.Button(f, text="M", width=2, bg="#444", fg="white", font=("Arial", 8, "bold")); btn_m.config(command=lambda v=m_var, b=btn_m: t_m(v,b)); btn_m.pack(side="left", padx=2)
            
            spd_var = tk.IntVar(value=100); tk.Label(f, text="Spd%:", fg="#aaa", bg="#222").pack(side="left", padx=2)
            tk.Spinbox(f, from_=5, to=500, increment=10, textvariable=spd_var, width=4, bg="#333", fg="yellow").pack(side="left", padx=2)
            tk.Button(f, text="▶", bg="#444", fg="white", width=2, command=lambda p=path, ptr=s['audio_ptr'], sz=s['size'], sv=spd_var: play_sample(p, ptr, sz, sv.get())).pack(side="left", padx=5)
            
            t_v = tk.StringVar(value="Inst"); cb_t = ttk.Combobox(f, textvariable=t_v, values=["Inst", "Drum"], width=5, state="readonly"); cb_t.pack(side="left", padx=5)
            o_v = tk.IntVar(value=0); tk.Label(f, text="Oct:", fg="#aaa", bg="#222").pack(side="left", padx=2)
            
            sp_o = tk.Spinbox(f, from_=-8, to=8, textvariable=o_v, width=3, bg="#333", fg="white"); sp_o.pack(side="left", padx=2)
            v_v = tk.StringVar(); cb_v = ttk.Combobox(f, textvariable=v_v, width=30, state="readonly"); cb_v.pack(side="left", padx=5)
            
            def upd(e, cv=cb_v, tv=t_v, sp=sp_o):
                cv['values'] = GM_DRUMS_LIST if tv.get() == "Drum" else GM_INST_LIST
                cv.current(0); sp.config(state="normal" if tv.get() == "Inst" else "disabled")
            cb_t.bind("<<ComboboxSelected>>", upd); upd(None)
            
            self.rows.append((i, t_v, v_v, o_v, s_var, m_var, spd_var, btn_s, btn_m, cb_v, sp_o))

        btn_f = tk.Frame(self, bg="#111", pady=15); btn_f.pack(fill="x", side="bottom")
        
        tk.Button(btn_f, text="PREVIEW", bg="#3498db", fg="white", width=15, command=self.preview).pack(side="left", padx=15)
        tk.Button(btn_f, text="SAVE CONFIG", bg="#f39c12", fg="white", width=20, command=self.save_config).pack(side="left", padx=15)
        tk.Button(btn_f, text="EXPORT FINAL", bg="#2ecc71", fg="white", width=15, command=self.generate).pack(side="right", padx=15)

        self.load_config()

    def get_mapping(self):
        return {r[0]: {'type': r[1].get().lower(), 'val': int(r[2].get().split(':')[0]), 'octave': r[3].get(), 'solo': r[4].get(), 'mute': r[5].get()} for r in self.rows}

    def save_config(self):
        data = {}
        for r in self.rows:
            i, t_v, v_v, o_v, s_var, m_var, spd_var, btn_s, btn_m, cb_v, sp_o = r
            data[str(i)] = {
                'type': t_v.get(),
                'val_str': v_v.get(),
                'octave': o_v.get(),
                'solo': s_var.get(),
                'mute': m_var.get(),
                'speed': spd_var.get()
            }
        try:
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=4)
            messagebox.showinfo("Config Saved", f"Saved successfully to:\n{self.config_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save:\n{e}")

    def load_config(self):
        if not os.path.exists(self.config_path): return
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            for r in self.rows:
                i, t_v, v_v, o_v, s_var, m_var, spd_var, btn_s, btn_m, cb_v, sp_o = r
                idx = str(i)
                if idx in data:
                    c = data[idx]
                    t_v.set(c.get('type', 'Inst'))
                    cb_v['values'] = GM_DRUMS_LIST if t_v.get() == "Drum" else GM_INST_LIST
                    sp_o.config(state="normal" if t_v.get() == "Inst" else "disabled")
                    v_v.set(c.get('val_str', cb_v['values'][0]))
                    o_v.set(c.get('octave', 0))
                    is_solo = c.get('solo', False)
                    s_var.set(is_solo); btn_s.config(bg="#E6DB74" if is_solo else "#444", fg="black" if is_solo else "white")
                    is_mute = c.get('mute', False)
                    m_var.set(is_mute); btn_m.config(bg="#F92672" if is_mute else "#444")
                    spd_var.set(c.get('speed', 100))
        except: pass

    def preview(self):
        ok, res = run_high_res_conversion(self.path, self.get_mapping(), True)
        if ok: os.startfile(res)
        else: messagebox.showerror("Error", res)

    def generate(self):
        ok, res = run_high_res_conversion(self.path, self.get_mapping(), False)
        if ok: messagebox.showinfo("Success", f"File saved:\n{res}")
        else: messagebox.showerror("Error", res)

root = TkinterDnD.Tk(); root.title("S3M to MIDI Converter GUI v1.0"); root.geometry("400x250"); root.config(bg="#1a1a1a")
tk.Label(root, text="S3M to MIDI Converter GUI", fg="#00ffcc", bg="#1a1a1a", font=("Arial", 14, "bold")).pack(pady=20)
tk.Label(root, text="Drop your .S3M file below", fg="#888", bg="#1a1a1a").pack()
root.drop_target_register(DND_FILES); root.dnd_bind('<<Drop>>', lambda e: SampleMapper(root, e.data.strip('{} ')))
root.mainloop()