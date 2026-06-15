# Analizador de Potencial de Viralidad

Sistema para puntuar el potencial de viralidad de un reel/video, construido sobre
**FStats**. Todo el análisis usa **motores open source y locales** — sin APIs pagas.

## Las 3 partes

1. **Analizador** (`pages/7_Analizador.py`): subís un video y obtenés un **score 0-100 +
   explicación**, a partir de features de video y audio.
2. **Base** (tablas `raw_analyzer_runs` / `raw_analyzer_outcomes` en MotherDuck): guarda
   cada análisis (features, score) y, más adelante, el resultado real.
3. **Realimentación + entrenamiento** (`pages/8_Realimentacion.py`): trae reels reales del
   warehouse (ganadores y perdedores por percentil de reach/plays) y **entrena un regresor**
   que aprende qué funciona.

## Motores (todos locales / gratis)

| Modalidad   | Motor |
|-------------|-------|
| Video       | OpenCV (cortes de escena, gancho, movimiento, formato, primer frame) |
| Audio       | ffmpeg + librosa (loudness, energía, tempo, onsets, voz/silencio) |
| Transcripción | faster-whisper (Whisper open source, local) |
| Scoring     | **heurístico** (default) · **regresor** scikit-learn · **Ollama** (VLM local, opcional) |

## Instalación

```bash
pip install -r requirements.txt
```

Además, instalar el binario **ffmpeg** (habilita audio, transcripción y descarga de reels):

- Windows: `winget install Gyan.FFmpeg`
- macOS: `brew install ffmpeg`  ·  Linux: `apt install ffmpeg`

(Opcional) Para el motor LLM: instalar [Ollama](https://ollama.com) y un modelo de visión
(`ollama pull llava`). Requiere >8 GB de RAM o GPU; en máquinas chicas usá `heuristic` o `model`.

## Configuración

Copiá `.env.example` a `.env` y completá `MOTHERDUCK_TOKEN`, los tokens de Meta por portal,
y `ANALYZER_BACKEND` (`heuristic` | `model` | `ollama`).

## Uso

```bash
streamlit run app.py
```

- **🚀 Analizador**: subí un mp4 → score + subscores (gancho/ritmo/audio/claridad) + explicación.
- **🔁 Realimentación**: elegí portal y percentiles, **ingestá un bloque** (baja y analiza
  ganadores y perdedores), repetí hasta tener ≥5 de cada clase, y **entrená el modelo**.
  Después poné `ANALYZER_BACKEND=model` para que el analizador use el regresor.

## Elegir el motor de scoring

- `heuristic` — reglas sobre las features. Instantáneo y estable. **Default.**
- `model` — regresor entrenado con tus reels reales. Liviano (corre sin GPU), mejora con datos.
- `ollama` — LLM de visión local con explicación rica. Necesita hardware (RAM/GPU) o un
  `OLLAMA_HOST` remoto.

## Desarrollo / pruebas sin nube

```bash
FSTATS_DB_LOCAL=1 streamlit run app.py   # usa un DuckDB local en vez de MotherDuck
```

## Notas

- Los videos descargados/subidos se guardan en `data/analyzer/<sha>.mp4` (gitignoreado);
  la base solo referencia el hash. El modelo entrenado vive en `data/analyzer/model.joblib`.
- Las dependencias pesadas (cv2, librosa, faster-whisper, scikit-learn) se importan de forma
  perezosa: si falta alguna, el sistema degrada en vez de romper.
