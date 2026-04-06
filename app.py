import streamlit as st
import numpy as np
import scipy.io.wavfile as wavfile
from pydub import AudioSegment
import librosa
import librosa.display
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import io
import math

st.set_page_config(page_title="Master Forensics Suite", layout="wide")

# Theme colors
CLR_BG = "#0E1117"
CLR_LSB = "#00FFFF"
CLR_PARITY = "#50C878"
CLR_PHASE = "#7851A9"
CLR_PHASE_A = "#CBAACB" # Lighter purple for attenuated
CLR_ORIGINAL = "#FFFFFF"

# -----------------
# DATA PROCESSING
# -----------------
def convert_to_wav(uploaded_file):
    fmt = "mp3" if uploaded_file.name.endswith(".mp3") else "wav"
    audio = AudioSegment.from_file(uploaded_file, format=fmt)
    # Handle stereo to mono conversion as requested in the prompt
    if audio.channels > 1:
        audio = audio.set_channels(1)
    wav_io = io.BytesIO()
    audio.export(wav_io, format="wav")
    wav_io.seek(0)
    return wav_io

def text_to_bits_padded(text):
    delimiter = "#####"
    text += delimiter
    bits = bin(int.from_bytes(text.encode('utf-8', 'surrogatepass'), 'big'))[2:]
    return bits.zfill(8 * ((len(bits) + 7) // 8))

def bits_to_text(bits):
    n = int(bits, 2)
    try:
        return n.to_bytes((n.bit_length() + 7) // 8, 'big').decode('utf-8', 'surrogatepass') or '\0'
    except Exception:
        return ""

def get_delimiter_len():
    return len(text_to_bits_padded(""))

# -----------------
# METHOD 1: LSB
# -----------------
def encode_lsb(audio_array, text):
    bits = text_to_bits_padded(text)
    if len(bits) > len(audio_array):
        raise ValueError("Message too long for LSB.")
    
    encoded = audio_array.copy()
    encoded.setflags(write=1)
    
    for i in range(len(bits)):
        encoded[i] = (int(encoded[i]) & ~1) | int(bits[i])
    return encoded

def decode_lsb(audio_array):
    d_len = get_delimiter_len()
    bits = ""
    delimiter_bits = text_to_bits_padded("")
    for i in range(len(audio_array)):
        bits += str(int(audio_array[i]) & 1)
        if len(bits) >= d_len and bits[-d_len:] == delimiter_bits:
            return bits_to_text(bits[:-d_len])
    return ""

# -----------------
# METHOD 2: PARITY
# -----------------
def encode_parity(audio_array, text, block_size=32):
    bits = text_to_bits_padded(text)
    if len(bits) * block_size > len(audio_array):
        raise ValueError("Message too long for Parity.")
        
    encoded = audio_array.copy()
    encoded.setflags(write=1)
    
    for i in range(len(bits)):
        bit = int(bits[i])
        start = i * block_size
        end = start + block_size
        block = encoded[start:end]
        
        # current parity of the block
        current_parity = np.sum(block & 1) % 2
        
        if current_parity != bit:
            # Flip the LSB of the first sample in the block
            encoded[start] = (int(encoded[start]) & ~1) | (1 - (int(encoded[start]) & 1))
            
    return encoded
    
def decode_parity(audio_array, block_size=32):
    d_len = get_delimiter_len()
    delimiter_bits = text_to_bits_padded("")
    num_blocks = len(audio_array) // block_size
    bits = ""
    
    for i in range(num_blocks):
        start = i * block_size
        end = start + block_size
        block = audio_array[start:end]
        parity = np.sum(block & 1) % 2
        bits += str(parity)
        
        if len(bits) >= d_len and bits[-d_len:] == delimiter_bits:
            return bits_to_text(bits[:-d_len])
    return ""

# -----------------
# METHOD 3/4: PHASE
# -----------------
def encode_phase(audio_array, text, L=2048, strength=math.pi/2):
    bits = text_to_bits_padded(text)
    capacity = (L // 2) - 1
    
    if len(bits) > capacity:
        raise ValueError("Message too long for Phase Coding (Single Block).")
        
    num_blocks = len(audio_array) // L
    if num_blocks == 0:
        raise ValueError("Audio too short for Phase Coding.")
        
    # Provide 10% headroom to prevent phase-shifts from inducing time-domain clipping (>32767)
    encoded = audio_array.copy().astype(np.float64) * 0.9
    # We only modify the first block for this basic implementation to guarantee extraction
    block0 = encoded[:L]
    fft_block = np.fft.fft(block0)
    mags = np.abs(fft_block)
    phases = np.angle(fft_block)
    
    orig_phase_0 = phases.copy()
    
    for i in range(len(bits)):
        idx = i + 1
        bit = int(bits[i])
        phases[idx] = strength if bit == 0 else -strength
        phases[L - idx] = -phases[idx]
        
        # Enforce magnitude boundary to survive 16-bit PCM quantization dropping tiny angles to zero!
        mags[idx] = max(mags[idx], float(L) * 100.0)
        mags[L - idx] = mags[idx]
        
    # Reconstruct block 0
    new_fft = mags * np.exp(1j * phases)
    encoded[:L] = np.real(np.fft.ifft(new_fft))
    
    # Phase offset propagation to remaining blocks to avoid clicks (simplified difference tracking)
    delta = phases - orig_phase_0
    
    for k in range(1, num_blocks):
        start = k * L
        end = start + L
        block = encoded[start:end]
        fft_b = np.fft.fft(block)
        m = np.abs(fft_b)
        p = np.angle(fft_b)
        p_new = p + delta
        new_b_fft = m * np.exp(1j * p_new)
        encoded[start:end] = np.real(np.fft.ifft(new_b_fft))
        
    # converting back to int16
    encoded = np.clip(np.round(encoded), -32768, 32767).astype(np.int16)
    return encoded

def decode_phase(audio_array, L=2048):
    if len(audio_array) < L: return ""
    block0 = audio_array[:L]
    fft_block = np.fft.fft(block0)
    phases = np.angle(fft_block)
    
    bits = ""
    capacity = (L // 2) - 1
    d_len = get_delimiter_len()
    delimiter_bits = text_to_bits_padded("")
    
    for i in range(capacity):
        idx = i + 1
        angle = phases[idx]
        bit = "0" if angle > 0 else "1"
        bits += bit
        
        if len(bits) >= d_len and bits[-d_len:] == delimiter_bits:
            return bits_to_text(bits[:-d_len])
    return ""


# -----------------
# UI COMPONENTS
# -----------------
st.title("🎙️ Multi-Method Audio Forensics Suite")
st.markdown("A professional, research-grade steganography laboratory for multiplexed audio analysis.")

# Input Zone
st.sidebar.header("The Parallel Engine")
uploaded_file = st.sidebar.file_uploader("Upload Cover Audio (.wav/.mp3)", type=["wav", "mp3"])
secret_msg = st.sidebar.text_area("Secret Payload", "Classified Research Data")

if st.sidebar.button("Execute Stego-Engine", type="primary"):
    if not uploaded_file or not secret_msg:
        st.sidebar.error("Upload a file and enter a message.")
    else:
        with st.spinner("Processing Mono-Conversion and generating parallel stego-streams..."):
            wav_io = convert_to_wav(uploaded_file)
            sr, orig_data = wavfile.read(wav_io)
            
            if not np.issubdtype(orig_data.dtype, np.integer):
                st.error("Audio must be 16-bit PCM integer WAV format.")
                st.stop()
                
            orig_flat = orig_data.flatten()
            
            # --- Generate 4 Streams ---
            stego_lsb = encode_lsb(orig_flat, secret_msg)
            stego_par = encode_parity(orig_flat, secret_msg)
            # Standard strength Phase (pi/2 is loud and robust)
            stego_phR = encode_phase(orig_flat, secret_msg, strength=math.pi/2)
            # Attenuated Phase (pi/8 is quieter but riskier mathematically)
            stego_phA = encode_phase(orig_flat, secret_msg, strength=math.pi/8)
            
            # --- Verify Integrity ---
            rec_lsb = decode_lsb(stego_lsb) == secret_msg
            rec_par = decode_parity(stego_par) == secret_msg
            rec_phR = decode_phase(stego_phR) == secret_msg
            rec_phA = decode_phase(stego_phA) == secret_msg
            
            # Save into Session State so tabs can access them without rerunning
            st.session_state['orig'] = orig_flat
            st.session_state['sr'] = sr
            st.session_state['stegos'] = {
                "LSB Engine": {"data": stego_lsb, "color": CLR_LSB, "rec": rec_lsb, "desc": "Bit replacement"},
                "Parity Engine": {"data": stego_par, "color": CLR_PARITY, "rec": rec_par, "desc": "Block-level parity sync"},
                "Phase (Loud)": {"data": stego_phR, "color": CLR_PHASE, "rec": rec_phR, "desc": "+-90° Fourier Shift"},
                "Phase (Stealth)": {"data": stego_phA, "color": CLR_PHASE_A, "rec": rec_phA, "desc": "+-22° Fourier Shift"}
            }
            st.session_state['processed'] = True

if st.session_state.get('processed', False):
    tab1, tab2 = st.tabs(["🎛️ The Studio", "🔬 The Forensic Lab"])
    
    orig = st.session_state['orig']
    sr = st.session_state['sr']
    stegos = st.session_state['stegos']
    
    with tab1:
        st.header("The Studio")
        st.markdown("Listen and export the generated artifacts.")
        
        cols = st.columns(4)
        for i, (name, info) in enumerate(stegos.items()):
            c = cols[i]
            with c:
                st.markdown(f"### <span style='color:{info['color']}'>{name}</span>", unsafe_allow_html=True)
                st.caption(info['desc'])
                
                if info['rec']:
                    st.success("Integrity Verified ✅")
                else:
                    st.error("Extraction Failed ❌ (Quantization noise broke the sequence)")
                    
                # Audio export
                out_io = io.BytesIO()
                wavfile.write(out_io, sr, info['data'])
                out_io.seek(0)
                
                st.audio(out_io, format="audio/wav")
                st.download_button(label=f"Download {name} .wav", data=out_io, file_name=f"{name.replace(' ', '_')}.wav", mime="audio/wav")
                
    with tab2:
        st.header("The Forensic Lab")
        st.markdown("A deep scientific analysis of the digital footprints left by each algorithm.")
        
        # 1. SNR Gauges
        st.subheader("1. Signal-to-Noise Ratio (SNR) Gauges")
        st.info("💡 **Explain it to a kid:** This is like hiding a whisper in a thunderstorm. The higher the number, the better the whisper is hidden!")
        
        cols = st.columns(4)
        for i, (name, info) in enumerate(stegos.items()):
            diff = orig.astype(np.float64) - info['data'].astype(np.float64)
            sig_pwr = np.mean(orig.astype(np.float64)**2) + 1e-10
            noise_pwr = np.mean(diff ** 2) + 1e-10
            snr = 10 * np.log10(sig_pwr / noise_pwr)
            
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = snr,
                title = {'text': name},
                number = {"suffix": " dB"},
                gauge = {
                    'axis': {'range': [0, 100]},
                    'bar': {'color': info['color']},
                    'bgcolor': "rgba(0,0,0,0)"
                }
            ))
            fig.update_layout(height=200, margin=dict(l=10, r=10, t=30, b=10), template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            cols[i].plotly_chart(fig, use_container_width=True)
            
        st.divider()
        
        # 2. Difference Microscope
        st.subheader("2. The Difference Microscope (Residuals)")
        st.info("💡 **Explain it to a kid:** This shows the 'Ghost' of your message. If this line looks like flat silence, your secret is perfectly invisible.")
        
        snippet = min(2000, len(orig))
        fig_diff = go.Figure()
        for name, info in stegos.items():
            diff = orig[:snippet].astype(np.float32) - info['data'][:snippet].astype(np.float32)
            fig_diff.add_trace(go.Scatter(y=diff, mode='lines', name=name, line=dict(color=info['color'], width=1)))
            
        fig_diff.update_layout(title="Residual Amplitude (Original - Stego) over 2000 samples", template="plotly_dark", height=300)
        st.plotly_chart(fig_diff, use_container_width=True)
        
        st.divider()
        
        # 3. Spectrograms
        st.subheader("3. Mel-Spectrogram Comparison")
        st.info("💡 **Explain it to a kid:** This is a 'Heat Map' of the sound. We look for 'Hot Spots' that shouldn't be there. If the colors match entirely, the spy can't find your data!")
        
        # We need a 2x3 grid. 6 axes. Original + 4 stegos = 5 plots. (Leave 6th blank).
        fig_mel, ax_mel = plt.subplots(2, 3, figsize=(12, 6))
        ax_flat = ax_mel.flatten()
        
        # Helper to plot spec
        def plot_spec(ax, y_data, title, sr):
            vis_len = min(5 * sr, len(y_data))
            y_vis = y_data[:vis_len].astype(np.float32) / (np.max(np.abs(y_data[:vis_len])) + 1e-6)
            S = librosa.feature.melspectrogram(y=y_vis, sr=sr, n_mels=128)
            S_db = librosa.power_to_db(S, ref=np.max)
            librosa.display.specshow(S_db, sr=sr, x_axis='time', y_axis='mel', ax=ax, cmap='viridis')
            ax.set_title(title, color="white", fontsize=10)
            ax.tick_params(colors="white", labelsize=8)
            ax.xaxis.label.set_color("white")
            ax.yaxis.label.set_color("white")
            ax.patch.set_alpha(0.0)
            
        plot_spec(ax_flat[0], orig, "Original Cover", sr)
        for i, (name, info) in enumerate(stegos.items()):
            plot_spec(ax_flat[i+1], info['data'], name, sr)
            
        ax_flat[-1].axis('off') # Hide 6th
        fig_mel.patch.set_alpha(0.0)
        plt.tight_layout()
        st.pyplot(fig_mel, clear_figure=True)
        
        st.divider()
        
        # 4. Bit-Level Deep Dive
        st.subheader("4. Bit-Level Deep Dive (The Flipped Pixel Dust)")
        st.info("💡 **Explain it to a kid:** We zoomed in 1,000x to see exactly which digital dust motes we moved. Some methods move a lot, others move very few!")
        
        # Plotly Scatter
        fig_scatter = go.Figure()
        
        max_scatter_len = min(20000, len(orig))
        
        for i, (name, info) in enumerate(stegos.items()):
            # Find indices where samples differ
            diff_indices = np.where(orig[:max_scatter_len] != info['data'][:max_scatter_len])[0]
            
            # Scatter plot at a specific Y level to separate them
            y_levels = np.full(len(diff_indices), len(stegos) - i)
            fig_scatter.add_trace(go.Scatter(
                x=diff_indices, y=y_levels, 
                mode='markers', 
                name=name, 
                marker=dict(color=info['color'], size=4, opacity=0.7)
            ))

        fig_scatter.update_layout(
            title="Modified Sample Indices mapped in the first 20k audio frames",
            xaxis_title="Sample Index",
            yaxis=dict(tickvals=[1,2,3,4], ticktext=list(reversed(list(stegos.keys()))), title="Method"),
            template="plotly_dark",
            height=300
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
