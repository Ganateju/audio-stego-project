# 🔬 Technical Specification: Multi-Method Audio Steganography & Blind Steganalysis

This document presents the **mathematical framework, spectral behavior, and practical intuition** behind the embedding engines used in the **Master Forensics Suite**.

The goal is not just correctness, but clarity — ensuring both **researchers and beginners** can follow the logic.

---

## 1. 🎯 Spatial Domain Transformation: LSB Encoding

### 🧠 Intuition

Think of audio samples like very precise numbers.  
Changing the **last bit** is like slightly nudging a grain of sand on a beach — invisible to humans, but detectable to machines.

---

### 📐 Mathematical Model

For a 16-bit signed integer sample $S_i$, the stego-sample $S'_i$ is:

$$
S'_i = (S_i \text{ AND } 0xFFFE) \lor b_i
$$

where:
- $b_i \in \{0,1\}$ is the payload bit
- `AND 0xFFFE` clears the last bit
- `OR b_i` inserts the message bit

---

### 📉 Noise Analysis

This introduces a bounded quantization noise:

$$
MSE = \frac{1}{N} \sum_{i=1}^{N} (S'_i - S_i)^2 \leq 1
$$

---

### ⚠️ Vulnerability

- Disrupts natural LSB randomness
- Detectable via **RS Steganalysis**
- Leaves statistical fingerprints

---

## 2. ⚖️ Block-Based Parity Coding

### 🧠 Intuition

Instead of touching every sample, we **encode meaning into balance**.

Like adjusting one student in a group so the total count becomes even or odd.

---

### ⚙️ Algorithm

- Divide signal into blocks of size $n = 32$
- Each block carries **1 bit**

---

### 📐 Encoding Logic

For block $B_k$:

$$
P(B_k) = \left( \sum_{j \in B_k} LSB(j) \right) \pmod 2
$$

If:
$$
P(B_k) \neq b_k
$$

→ Flip LSB of first sample in the block

---

### 📊 Significance

- Reduces modifications by **32×**
- Improves SNR
- Smooths statistical anomalies

---

## 3. 🌐 Frequency Domain: Discrete Phase Coding (DPC)

### 🧠 Intuition

Instead of changing loudness (which ears detect),  
we shift **when the wave starts**.

Your ears track amplitude.  
They barely care about absolute phase.

---

### A. ⚙️ Embedding Process

#### 1. Segmentation

Signal divided into segments:
- Length $L = 2048$

---

#### 2. Transformation

Apply DFT:

$$
S_0(\omega) = A(\omega)e^{j\phi(\omega)}
$$

---

#### 3. Phase Mapping

Replace phase based on message bit:

$$
\phi'_{new} =
\begin{cases}
\pi/2 & \text{if bit = 0} \\
-\pi/2 & \text{if bit = 1}
\end{cases}
$$

---

#### 4. Phase Propagation

To avoid audible artifacts:

$$
\Delta \phi = \phi'_{new} - \phi_{old}
$$

Apply $\Delta \phi$ to all subsequent segments.

---

### B. 🧩 Robustness vs. Stealth

| Mode | Phase Shift | Behavior |
|------|------------|----------|
| Loud | $\pm \pi/2$ | Strong separation, easy decoding |
| Stealth | $\pm \pi/8$ | Minimal distortion, harder detection |

---

### 📊 Significance

- Highly robust to:
  - Resampling
  - Volume scaling
- Operates in **frequency domain**
- Avoids direct amplitude distortion

---

## 4. 🔬 Forensic Methodology (The Lab Layer)

---

### 🌈 Spectral Analysis (Mel-Spectrogram)

### 🧠 Intuition

Humans don’t hear frequencies linearly.  
Mel-scale mimics how we actually perceive sound.

---

### 📐 Equation

$$
M(f) = 2595 \log_{10}(1 + f/700)
$$

---

### 🎯 Objective

Detect **Energy Leakage** in high-frequency bands ($>15kHz$)

- Clean spectrogram → perceptually transparent
- Visible spikes → detectable manipulation

---

### 📉 Statistical Transparency (PSNR)

### 🧠 Intuition

Compare:
- Original signal power
- Noise introduced by embedding

---

### 📐 Formula

$$
PSNR = 10 \cdot \log_{10}\left(\frac{MAX_I^2}{MSE}\right)
$$

---

### 🎯 Interpretation

- > 70 dB → Technically invisible
- Matches natural recording noise floor

---

## 5. 🧠 Blind Steganalysis (Universal Decryptor)

### 🧠 Intuition

Instead of asking:
> "How was this hidden?"

We ask:
> "What patterns exist, regardless of method?"

---

### ⚙️ Multi-Stage Detection

#### 1. Time-Domain Probe
- Scans LSB patterns
- Validates payload using delimiters (e.g., `#####`)

---

#### 2. Structural Probe
- Detects parity patterns
- Tests common block sizes:
  - 8, 16, 32

---

#### 3. Spectral Probe
- Extracts phase of first 2048 samples
- Analyzes angle distributions across frequency bins

---

### 📊 Interpretation

Acts as a **multi-class classifier**:
- Identifies embedding method
- Recovers hidden payload
- Requires zero prior knowledge

---

## 🚀 Summary for Researchers

Audio steganography is fundamentally a trade-off:

| Factor | LSB | Parity | Phase |
|--------|-----|--------|-------|
| Capacity | High | Medium | Low |
| Stealth | Low | Medium | Ultra High |
| Robustness | Fragile | Moderate | Strong |

---

### 🧬 Key Insight

- **LSB** → High capacity, low security  
- **Parity** → Balanced compromise  
- **Phase Coding** → Maximum stealth and robustness  

---

### 🧠 Final Observation

By introducing **Phase Propagation**, this system resolves a long-standing issue:

> Frequency-domain methods no longer produce audible discontinuities.

---

## 🧩 Closing Thought

Good steganography hides data.  
Great steganography leaves no trace.

This system doesn’t just embed information —  
it ensures the signal behaves as if nothing ever happened.
