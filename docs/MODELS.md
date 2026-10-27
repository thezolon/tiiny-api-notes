# Models in the Tiiny Model Store

All 73 models the Model Store offered on 2026-10-27, read from the device's own catalogue (`GET /api/v1/models/online_models`). Regenerate with `python tools/model_list.py`.

- **NPU** = share of the Tiiny's NPU memory the model takes when loaded. Models that add up to more than 100% can't be loaded together; TiinyOS (or the API's `unload_candidate`) tells you what has to go.
- **Size** = download size. **Context** = the longest prompt + reply it takes, in tokens.
- Use any loaded chat model from other apps with the model name `default` (see [RECIPES.md](RECIPES.md)).

## Chat with vision (15)

| model | params | NPU | size | context | can do |
|---|---|---|---|---|---|
| `Qwen/Qwen-Image-2.1-PE-I2I` | 7B | 24% | 5.9 GB | 256K | Vision, Prompt Enhance |
| `Qwen/Qwen3.5-9B-Turbo` | 9B | 28% | 6.5 GB | 128K | Vision, Reasoning, Tool Use |
| `Qwen/Qwen3.5-9B` | 9B | 29% | 6.2 GB | 128K | Vision, Reasoning, Tool Use |
| `Qwen/Qwen3.5-35B-A3B` | 35B | 45% | 16.9 GB | 128K | Vision, Reasoning, Tool Use |
| `Qwen/Qwen3.6-35B-A3B-Turbo` | 35B | 46% | 17.7 GB | 256K | Vision, Reasoning, Tool Use |
| `Qwen/Qwen3.6-27B` | 27B | 48% | 15.6 GB | 128K | Vision, Reasoning, Tool Use |
| `deepreinforce-ai/Ornith-1.0-35B` | 35B | 50% | 18.0 GB | 128K | Vision, Reasoning, Tool Use |
| `google/gemma-4-31B-it` | 31B | 51% | 16.7 GB | 128K | Vision, Reasoning, Tool Use |
| `Qwen/Qwen3.8-27B` | 27B | 52% | 15.9 GB | 256K | Vision, Reasoning, Tool Use |
| `endless-frontier/BigBang-v1-Turbo` | 36B | 54% | 17.9 GB | 128K | Vision, Thinking (toggle) |
| `ornith-ai/Ornith-1.5-35B-A3B-Turbo` | 35B | 54% | 17.9 GB | 128K | Vision, Thinking |
| `Qwen/Qwen3.6-27B-Turbo` | 27B | 55% | 15.7 GB | 128K | Vision, Reasoning, Tool Use |
| `Qwen/Qwen3.6-35B-A3B` | 35B | 55% | 17.6 GB | 128K | Vision, Reasoning, Tool Use |
| `trohrbaugh/Qwen3.8-27B-heretic-ara-Turbo` | 27B | 56% | 15.9 GB | 128K | Vision, Reasoning, Tool Use |
| `google/gemma-4-26B-A4B-it` | 26B | 78% | 13.4 GB | 128K | Reasoning, Tool Use |

## Chat (text only) (11)

| model | params | NPU | size | context | can do |
|---|---|---|---|---|---|
| `Qwen/Qwen-Image-2.1-PE-T2I` | 7B | 23% | 5.9 GB | 256K | Prompt Enhance |
| `Qwen/Qwen3-4B-Instruct-2507` | 4B | 25% | 2.3 GB | 128K | Tool Use |
| `openai/gpt-oss-20b` | 20B | 27% | 10.3 GB | 128K | Reasoning, Tool Use |
| `Qwen/Qwen3-8B` | 8B | 28% | 4.3 GB | 128K | Reasoning, Tool Use |
| `Qwen/Qwen3-30B-A3B-Instruct` | 30B | 55% | 14.7 GB | 128K | Tool Use |
| `Qwen/Qwen3-Coder-30B-A3B-Instruct` | 30B | 55% | 14.6 GB | 64K | Tool Use |
| `Qwen/Qwen3-Coder-30B-A3B-Instruct-Turbo` | 31B | 55% | 15.2 GB | 64K | Tool Use |
| `zai-org/GLM-4.7-Flash` | 31B | 57% | 15.8 GB | 64K | Reasoning, Tool Use |
| `Qwen/Qwen3-30B-A3B-Thinking` | 30B | 58% | 14.5 GB | 128K | Tool Use, Thinking |
| `Qwen/Qwen3-Coder-Next` | 80B | 94% | 37.7 GB | 128K | Tool Use |
| `openai/gpt-oss-120b` | 120B | 100% | 67.3 GB | 128K | Reasoning, Tool Use |

## Image creation and editing (13)

| model | params | NPU | size | context | can do |
|---|---|---|---|---|---|
| `TaoBaiBai2025/Z-Image-Turbo-Creating-Realistic` | 10B | 26% | 10.2 GB |  |  |
| `Tongyi-MAI/Z-Image-Turbo` | 10B | 26% | 10.2 GB |  |  |
| `Tongyi-MAI/Z-Image-Turbo-Children-Drawing` | 10B | 26% | 10.2 GB |  |  |
| `YeiYeiArt/Z-Image-Turbo-CharacterDesignSheet` | 10B | 26% | 10.2 GB |  |  |
| `black-forest-labs/FLUX.2-klein-4B` | 4B | 26% | 7.2 GB |  |  |
| `fal/FLUX.2-klein-4B-Background-Remove` | 4B | 26% | 7.3 GB |  | Image Editing |
| `fal/FLUX.2-klein-4B-Object-Remove` | 4B | 26% | 7.2 GB |  | Image Editing |
| `fal/FLUX.2-klein-4B-Outpaint` | 4B | 26% | 7.2 GB |  | Image Editing |
| `fal/FLUX.2-klein-4B-Zoom` | 4B | 26% | 7.2 GB |  | Image Editing |
| `baidu/ERNIE-Image-Turbo` | 8B | 27% | 11.4 GB |  |  |
| `HiDream-ai/HiDream-O1-Image-Dev` | 9B | 30% | 15.2 GB |  |  |
| `SenseTime/SenseNova-U1.5-8B-MoT` | 8B | 48% | 26.2 GB |  |  |
| `Qwen/Qwen-Image-2.1` | 7B | 58% | 15.6 GB |  | Image Editing |

## Reading text in images (OCR) (4)

| model | params | NPU | size | context | can do |
|---|---|---|---|---|---|
| `PaddlePaddle/PP-OCRv6-Small` | 2.48M | 0% | 0.1 GB |  |  |
| `PaddlePaddle/PP-OCRv6-Medium` | 22M | 1% | 0.1 GB |  |  |
| `zai-org/GLM-OCR` | 0.9B | 4% | 1.9 GB | 64K |  |
| `PaddlePaddle/PP-DocLayoutV3` | 1B | 20% | 0.2 GB |  |  |

## Speech to text (6)

| model | params | NPU | size | context | can do |
|---|---|---|---|---|---|
| `nvidia/Parakeet-TDT-0.6B-V3` | 0.6B | 5% | 1.3 GB |  |  |
| `openai/Whisper-large-v3-turbo` | 0.8B | 5% | 2.5 GB |  |  |
| `FunAudioLLM/Fun-ASR-MLT-Nano` | 1B | 6% | 2.7 GB |  |  |
| `OpenMOSS-Team/MOSS-Transcribe-Diarize` | 0.9B | 6% | 2.8 GB |  |  |
| `FunAudioLLM/Fun-ASR-Nano` | 1B | 7% | 2.6 GB |  |  |
| `Qwen/Qwen3-ASR-1.7B` | 1.7B | 7% | 4.1 GB |  |  |

## Text to speech (4)

| model | params | NPU | size | context | can do |
|---|---|---|---|---|---|
| `Supertone/supertonic-3` | 0.1B | 0% | 1.0 GB |  | Custom Voice |
| `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | 1.7B | 5% | 2.5 GB |  | Voice Clone |
| `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` | 1.7B | 5% | 2.4 GB |  | Voice Design |
| `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | 1.7B | 7% | 2.4 GB |  | Custom Voice |

## Music (4)

| model | params | NPU | size | context | can do |
|---|---|---|---|---|---|
| `RoyalCities/Foundation-1` | 2B | 5% | 1.4 GB |  |  |
| `tencent/SongGeneration-v2-large` | 4B | 28% | 6.9 GB |  |  |
| `ACE-Step/AceStep-XL-Base` | 5B | 40% | 11.5 GB |  |  |
| `ACE-Step/AceStep-XL-Turbo` | 5B | 40% | 11.8 GB |  |  |

## 3D (2)

| model | params | NPU | size | context | can do |
|---|---|---|---|---|---|
| `microsoft/TRELLIS.2-4B` | 4B | 6% | 9.8 GB |  |  |
| `Tencent/Hunyuan3d-2.1` | 5.3B | 22% | 10.6 GB |  |  |

## Embeddings (for search and the vault) (8)

| model | params | NPU | size | context | can do |
|---|---|---|---|---|---|
| `Qwen/Qwen3-Embedding-0.6B` | 0.6B | 2% | 0.9 GB | 8K |  |
| `tencent/R3-embedding-0.6b` | 0.6B | 4% | 0.8 GB | 8K |  |
| `nvidia/Nemotron-3-Embed-1B-BF16` | 1B | 7% | 1.3 GB | 4K |  |
| `Qwen/Qwen3-Vl-Embedding-2b` | 2B | 8% | 2.4 GB | 16K |  |
| `Qwen/Qwen3-Embedding-8b` | 8B | 18% | 7.8 GB | 8K |  |
| `nvidia/Nemotron-3-Embed-8b-Bf16` | 8B | 20% | 8.1 GB | 4K |  |
| `Qwen/Qwen3-Vl-Embedding-8b` | 8B | 21% | 8.9 GB | 16K |  |
| `Qwen/Qwen3-Embedding-4b` | 4B | 23% | 4.2 GB | 8K |  |

## Rerankers (6)

| model | params | NPU | size | context | can do |
|---|---|---|---|---|---|
| `Qwen/Qwen3-Reranker-0.6B` | 0.6B | 2% | 0.7 GB | 8K |  |
| `tencent/R3-rerank-0.6b` | 0.6B | 3% | 0.8 GB | 8K |  |
| `Qwen/Qwen3-Vl-Reranker-2b` | 2B | 8% | 2.3 GB | 16K |  |
| `Qwen/Qwen3-Reranker-4b` | 4B | 10% | 4.2 GB | 8K |  |
| `Qwen/Qwen3-Reranker-8b` | 8B | 16% | 7.8 GB | 8K |  |
| `Qwen/Qwen3-Vl-Reranker-8b` | 8B | 21% | 8.4 GB | 16K |  |
