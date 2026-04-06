# Multi-Method Audio Steganography & Forensics Suite

## Introduction

This repository contains a professional, research-grade steganography laboratory for multiplexed audio analysis. The application is capable of hiding a secret text payload within a digital audio host using three distinct theoretical and mathematical approaches simultaneously, while also featuring an elite "Forensic Lab" for deep comparative analysis of the resulting signals.

The system is built visually via Streamlit to operate as an interactive dashboard, ideal for security researchers, cryptographers, and academics.

## How LSB (Least Significant Bit) Works

The Least Significant Bit (LSB) embedding technique relies on substituting the lowest-order bit of successive audio integer samples with the binary representation of the secret payload. Because digital audio is continuously sampled (commonly at 44.1 kHz, 16-bit PCM), the modification of the $0^\text{th}$ bit typically alters the amplitude of a sample by a negligible quantization step ($\pm 1 / 32768$).

Given the host audio array $A$ of discrete time samples $a_i$, and an encoded binary secret message $M$ composed of discrete bits $m_i \in \{0, 1\}$, the steganographic embedding function $E$ can be modeled as:

$$
E(a_i, m_i) = (a_i \land \sim 1) \lor m_i
$$

Where:
- $\land$ represents the bitwise AND operator.
- $\sim$ represents the bitwise NOT operator.
- $\lor$ represents the bitwise OR operator.

By systematically applying this formula, the original LSB structure is overwritten while preserving the macroscopic spectral properties of the sound envelope. The retrieval of the payload (extraction process) simply inverses this to isolate the hidden trace:

$$
m_i = a'_i \land 1
$$

In addition to traditional LSB, this application features block-based **Parity Coding** and frequency-domain **Phase Coding** (via Discrete Fourier Transform phase shifting), allowing researchers to compare the noise resiliency and footprint differences of competing methodologies.
## 📚 Documentation

For deeper understanding of the system, refer to:

- 🧠 [Concept & Features](./FEATURES_AND_SIGNIFICANCE.md)  
  → Intuition, design philosophy, and system-level thinking  

- 🔬 [Technical Specification](./TECHNICAL_ANALYSIS.md)  
  → Mathematical models, spectral analysis, and formal framework  
## 🚀 Try the Live App
Click the link below to test the audio steganography engines in your browser:
**[👉 Launch Master Forensics Suite 👈](https://audio-stego-project.streamlit.app/)**
## Setup and Development

### Prerequisites

You must have `ffmpeg` installed on your machine so `pydub` can perform necessary decoding on standard audio file formats (such as `.mp3`). 
- **Debian / Ubuntu**: `sudo apt install ffmpeg libavcodec-extra`
- **Windows**: Install static binaries (via winget or direct download) and add to PATH.

### Installation

Clone the repository and install the Python dependencies:

```bash
git clone https://github.com/Ganateju/audio-stego-project
cd audio-stego-project
pip install -r requirements.txt
```

### Usage

To launch the dashboard locally via the Streamlit web server:

```bash
streamlit run app.py
```

The app will map to `http://localhost:8501`. 

### Features

1. **The Studio (Encoder)**: Generates 4 parallel channels of audio (`LSB`, `Parity`, `Phase Loud`, `Phase Stealth`) containing the secret payload.
2. **The Forensic Lab**: Includes Signal-To-Noise Ratio (SNR) Gauges, the "Difference Microscope" to evaluate the signal residue, Mel-Spectrogram grids, and Bit-Level scatter plot mapping.
