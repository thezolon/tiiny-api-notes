# Models in the Tiiny Model Store

All 92 models the Model Store offered on 2026-11-06, read from the device's own catalogue (`GET /api/v1/models/online_models`). Regenerate with `python tools/model_list.py`.

- **NPU** = share of the Tiiny's NPU memory the model takes when loaded. Models that add up to more than 100% can't be loaded together; TiinyOS (or the API's `unload_candidate`) tells you what has to go.
- **Size** = download size. **Context** = the longest prompt + reply it takes, in tokens.
- Use any loaded chat model from other apps with the model name `default` (see [RECIPES.md](RECIPES.md)).

## Licenses with limits (checked 2026-11-06)

Most models are Apache-2.0 or MIT. These are the exceptions (⚠ in the tables). This is a summary of each license as published, not legal advice: read the license itself before relying on a model.

**Not licensed in some regions:**

- `lightx2v/MiniMax-H3-Turbo`: **not licensed in the EU, the UK, South Korea or the USA** (MiniMax H3 Community license)
- `Tencent/Hunyuan3d-2.1`: **not licensed in the EU, the UK or South Korea**; over 1M monthly users needs a license from Tencent (Tencent Hunyuan 3D Community license)

**Other limits:**

- `Qwen/Qwen-Image-2.1`: non-commercial (research/evaluation only without a separate license) (Qwen Research)
- `k2-fsa/OmniVoice`: non-commercial (the model weights; the code is Apache-2.0) (CC-BY-NC)
- `YeiYeiArt/Z-Image-Turbo-CharacterDesignSheet`: source not found on Hugging Face (?)
- `krea/Krea-2-Turbo`: commercial use only below USD 1M annual revenue (worldwide, no regions excluded) (Krea 2 Community)
- `m-a-p/YuE2-3B`: non-commercial (CC-BY-NC-4.0)
- `abenzerps/Qwen-Image-2.1-Uncensored-Quantized`: non-commercial (research/evaluation only without a separate license) (Qwen Research)
- `Qwen/Qwen-Image-2.1-PE-T2I`: non-commercial (research/evaluation only without a separate license) (Qwen Research)
- `Qwen/Qwen-Image-2.1-PE-I2I`: non-commercial (research/evaluation only without a separate license) (Qwen Research)
- `tencent/SongGeneration-v2-large`: not checked: the license page needs a Hugging Face login; Tencent's other licenses exclude regions, so check before use (Tencent (custom))
- `RoyalCities/Foundation-1`: commercial use only below USD 1M annual revenue (Stability AI Community)

Models built on another model (Tiiny's "Turbo" builds, LoRAs) link to the base model's license. Licenses ending in `?` come from the likely source repo, not a confirmed one.

## Chat with vision (17)

| model | params | NPU | size | context | can do | license |
|---|---|---|---|---|---|---|
| `Qwen/Qwen-Image-2.1-PE-I2I` | 7B | 24% | 5.9 GB | 256K | Vision, Prompt Enhance | [Qwen Research](https://huggingface.co/Qwen/Qwen-Image-2.1-PE-I2I) ⚠ |
| `Qwen/Qwen3.5-9B-Turbo` | 9B | 28% | 6.5 GB | 128K | Vision, Reasoning, Tool Use | [Apache-2.0](https://huggingface.co/Qwen/Qwen3.5-9B) |
| `Qwen/Qwen3.5-9B` | 9B | 29% | 6.2 GB | 128K | Vision, Reasoning, Tool Use | [Apache-2.0](https://huggingface.co/Qwen/Qwen3.5-9B) |
| `google/gemma-4-26B-A4B-it` | 26B | 37% | 13.8 GB | 128K | Vision, Reasoning, Tool Use | [Apache-2.0](https://huggingface.co/google/gemma-4-26B-A4B-it) |
| `Qwen/Qwen3.5-35B-A3B` | 35B | 45% | 16.9 GB | 128K | Vision, Reasoning, Tool Use | [Apache-2.0](https://huggingface.co/Qwen/Qwen3.5-35B-A3B) |
| `Qwen/Qwen3.6-35B-A3B-Turbo` | 35B | 46% | 17.7 GB | 256K | Vision, Reasoning, Tool Use | [Apache-2.0](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) |
| `Qwen/Qwen3.6-35B-A3B` | 35B | 47% | 17.4 GB | 256K | Vision, Reasoning, Tool Use | [Apache-2.0](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) |
| `InternScience/Sage-A1.5-Turbo` | 35B | 48% | 17.5 GB | 256K | Vision, Reasoning, Tool Use | [Apache-2.0](https://huggingface.co/InternScience/Sage-A1.5) |
| `Qwen/Qwen3.6-27B` | 27B | 48% | 15.6 GB | 128K | Vision, Reasoning, Tool Use | [Apache-2.0](https://huggingface.co/Qwen/Qwen3.6-27B) |
| `huihui-ai/Huihui-Ornith-1.5-35B-A3B-abliterated-Turbo` | 35B | 48% | 17.5 GB | 256K | Vision, Reasoning, Tool Use | [MIT](https://huggingface.co/huihui-ai/Huihui-Ornith-1.5-35B-A3B-abliterated) |
| `deepreinforce-ai/Ornith-1.0-35B` | 35B | 50% | 18.0 GB | 128K | Vision, Reasoning, Tool Use | [MIT](https://huggingface.co/deepreinforce-ai/Ornith-1.0-35B) |
| `Qwen/Qwen3.8-27B` | 27B | 52% | 15.9 GB | 256K | Vision, Reasoning, Tool Use | [Apache-2.0](https://huggingface.co/Qwen/Qwen3.8-27B) |
| `google/gemma-4-31B-it` | 31B | 53% | 17.7 GB | 128K | Vision, Reasoning, Tool Use | [Apache-2.0](https://huggingface.co/google/gemma-4-31B-it) |
| `endless-frontier/BigBang-v1-Turbo` | 36B | 54% | 17.9 GB | 128K | Vision, Reasoning, Tool Use | [Apache-2.0](https://huggingface.co/endless-frontier/BigBang-v1) |
| `ornith-ai/Ornith-1.5-35B-A3B-Turbo` | 35B | 54% | 17.6 GB | 256K | Vision, Reasoning, Tool Use | [MIT](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B) |
| `Qwen/Qwen3.6-27B-Turbo` | 27B | 55% | 15.7 GB | 128K | Vision, Reasoning, Tool Use | [Apache-2.0](https://huggingface.co/Qwen/Qwen3.6-27B) |
| `trohrbaugh/Qwen3.8-27B-heretic-ara-Turbo` | 27B | 56% | 15.9 GB | 128K | Vision, Reasoning, Tool Use | [Apache-2.0](https://huggingface.co/trohrbaugh/Qwen3.8-27B-heretic-ara) |

## Chat (text only) (11)

| model | params | NPU | size | context | can do | license |
|---|---|---|---|---|---|---|
| `Qwen/Qwen-Image-2.1-PE-T2I` | 7B | 23% | 5.9 GB | 256K | Prompt Enhance | [Qwen Research](https://huggingface.co/Qwen/Qwen-Image-2.1-PE-T2I) ⚠ |
| `Qwen/Qwen3-4B-Instruct-2507` | 4B | 25% | 2.3 GB | 128K | Tool Use | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) |
| `openai/gpt-oss-20b` | 20B | 27% | 10.3 GB | 128K | Reasoning, Tool Use | [Apache-2.0](https://huggingface.co/openai/gpt-oss-20b) |
| `Qwen/Qwen3-8B` | 8B | 28% | 4.3 GB | 128K | Reasoning, Tool Use | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-8B) |
| `Qwen/Qwen3-30B-A3B-Instruct` | 30B | 55% | 14.7 GB | 128K | Tool Use | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507) |
| `Qwen/Qwen3-Coder-30B-A3B-Instruct` | 30B | 55% | 14.6 GB | 64K | Tool Use | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct) |
| `Qwen/Qwen3-Coder-30B-A3B-Instruct-Turbo` | 31B | 55% | 15.2 GB | 64K | Tool Use | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct) |
| `zai-org/GLM-4.7-Flash` | 31B | 57% | 15.8 GB | 64K | Reasoning, Tool Use | [MIT](https://huggingface.co/zai-org/GLM-4.7-Flash) |
| `Qwen/Qwen3-30B-A3B-Thinking` | 30B | 58% | 14.5 GB | 128K | Tool Use, Thinking | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-30B-A3B-Thinking-2507) |
| `Qwen/Qwen3-Coder-Next` | 80B | 94% | 37.7 GB | 128K | Tool Use | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-Coder-Next) |
| `openai/gpt-oss-120b` | 120B | 100% | 67.3 GB | 128K | Reasoning, Tool Use | [Apache-2.0](https://huggingface.co/openai/gpt-oss-120b) |

## Image creation and editing (15)

| model | params | NPU | size | context | can do | license |
|---|---|---|---|---|---|---|
| `abenzerps/Qwen-Image-2.1-Uncensored-Quantized` | 7B | 0% | 15.6 GB |  | Image Editing | [Qwen Research](https://huggingface.co/abenzerps/Qwen-Image-2.1-Uncensored-Quantized) ⚠ |
| `black-forest-labs/FLUX.2-klein-4B` | 4B | 19% | 7.2 GB |  |  | [Apache-2.0](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) |
| `fal/FLUX.2-klein-4B-Background-Remove` | 4B | 19% | 7.2 GB |  | Image Editing | [Apache-2.0](https://huggingface.co/fal/flux-2-klein-4B-background-remove-lora) |
| `fal/FLUX.2-klein-4B-Object-Remove` | 4B | 19% | 7.2 GB |  | Image Editing | [Apache-2.0](https://huggingface.co/fal/flux-2-klein-4B-object-remove-lora) |
| `fal/FLUX.2-klein-4B-Outpaint` | 4B | 20% | 7.2 GB |  | Image Editing | [Apache-2.0](https://huggingface.co/fal/flux-2-klein-4B-outpaint-lora) |
| `fal/FLUX.2-klein-4B-Zoom` | 4B | 20% | 7.2 GB |  | Image Editing | [Apache-2.0](https://huggingface.co/fal/flux-2-klein-4B-zoom-lora) |
| `TaoBaiBai2025/Z-Image-Turbo-Creating-Realistic` | 10B | 23% | 10.2 GB |  |  | [Apache-2.0?](https://huggingface.co/long12256/Z-image-turbo_Creating-Realistic) |
| `Tongyi-MAI/Z-Image-Turbo` | 10B | 23% | 10.2 GB |  |  | [Apache-2.0](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) |
| `Tongyi-MAI/Z-Image-Turbo-Children-Drawing` | 10B | 23% | 10.2 GB |  |  | [Apache-2.0?](https://huggingface.co/ostris/z_image_turbo_childrens_drawings) |
| `YeiYeiArt/Z-Image-Turbo-CharacterDesignSheet` | 10B | 23% | 10.2 GB |  |  | ? ⚠ |
| `baidu/ERNIE-Image-Turbo` | 8B | 27% | 11.4 GB |  |  | [Apache-2.0](https://huggingface.co/baidu/ERNIE-Image-Turbo) |
| `HiDream-ai/HiDream-O1-Image-Dev` | 9B | 30% | 15.2 GB |  |  | [MIT](https://huggingface.co/HiDream-ai/HiDream-O1-Image-Dev) |
| `krea/Krea-2-Turbo` | 13B | 36% | 16.5 GB |  |  | [Krea 2 Community](https://huggingface.co/krea/Krea-2-Turbo) ⚠ |
| `SenseTime/SenseNova-U1.5-8B-MoT` | 8B | 48% | 26.2 GB |  |  | [Apache-2.0](https://huggingface.co/sensenova/SenseNova-U1.5-8B-MoT) |
| `Qwen/Qwen-Image-2.1` | 7B | 62% | 15.6 GB |  | Image Editing | [Qwen Research](https://huggingface.co/Qwen/Qwen-Image-2.1) ⚠ |

## Reading text in images (OCR) (4)

| model | params | NPU | size | context | can do | license |
|---|---|---|---|---|---|---|
| `PaddlePaddle/PP-OCRv6-Small` | 2.48M | 0% | 0.1 GB |  |  | [Apache-2.0](https://huggingface.co/PaddlePaddle/PP-OCRv6_small_rec) |
| `PaddlePaddle/PP-OCRv6-Medium` | 22M | 1% | 0.1 GB |  |  | [Apache-2.0](https://huggingface.co/PaddlePaddle/PP-OCRv6_medium_rec) |
| `zai-org/GLM-OCR` | 0.9B | 4% | 1.9 GB | 64K |  | [MIT](https://huggingface.co/zai-org/GLM-OCR) |
| `PaddlePaddle/PP-DocLayoutV3` | 1B | 20% | 0.2 GB |  |  | [Apache-2.0](https://huggingface.co/PaddlePaddle/PP-DocLayoutV3) |

## Speech to text (6)

| model | params | NPU | size | context | can do | license |
|---|---|---|---|---|---|---|
| `nvidia/Parakeet-TDT-0.6B-V3` | 0.6B | 5% | 1.3 GB |  |  | [CC-BY-4.0](https://huggingface.co/nvidia/Parakeet-TDT-0.6B-V3) |
| `openai/Whisper-large-v3-turbo` | 0.8B | 5% | 2.5 GB |  |  | [MIT](https://huggingface.co/openai/Whisper-large-v3-turbo) |
| `FunAudioLLM/Fun-ASR-MLT-Nano` | 1B | 6% | 2.7 GB |  |  | [Apache-2.0](https://huggingface.co/FunAudioLLM/Fun-ASR-MLT-Nano-2512) |
| `OpenMOSS-Team/MOSS-Transcribe-Diarize` | 0.9B | 6% | 2.8 GB |  |  | [Apache-2.0](https://huggingface.co/OpenMOSS-Team/MOSS-Transcribe-Diarize) |
| `FunAudioLLM/Fun-ASR-Nano` | 1B | 7% | 2.6 GB |  |  | [Apache-2.0](https://huggingface.co/FunAudioLLM/Fun-ASR-Nano-2512) |
| `Qwen/Qwen3-ASR-1.7B` | 1.7B | 7% | 4.1 GB |  |  | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-ASR-1.7B) |

## Text to speech (10)

| model | params | NPU | size | context | can do | license |
|---|---|---|---|---|---|---|
| `OpenMOSS-Team/MOSS-TTS-Nano-100M` | 0.1B | 0% | 0.3 GB |  | Voice Clone | [Apache-2.0](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Nano-100M) |
| `Supertone/supertonic-3` | 0.1B | 0% | 0.2 GB |  | Custom Voice | [OpenRAIL](https://huggingface.co/Supertone/supertonic-3) |
| `hexgrad/Kokoro-82M` | 82M | 0% | 0.2 GB |  | Custom Voice | [Apache-2.0](https://huggingface.co/hexgrad/Kokoro-82M) |
| `k2-fsa/OmniVoice` | 0.6B | 2% | 1.7 GB |  | Voice Clone, Voice Design | [CC-BY-NC](https://huggingface.co/k2-fsa/OmniVoice) ⚠ |
| `microsoft/VibeVoice-Realtime-0.5B` | 0.5B | 2% | 1.1 GB |  | Custom Voice | [MIT](https://huggingface.co/microsoft/VibeVoice-Realtime-0.5B) |
| `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | 1.7B | 5% | 2.5 GB |  | Voice Clone | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base) |
| `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` | 1.7B | 5% | 2.4 GB |  | Voice Design | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign) |
| `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | 1.7B | 7% | 2.4 GB |  | Custom Voice | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice) |
| `openbmb/VoxCPM2` | 2B | 7% | 4.0 GB |  | Voice Clone, Voice Design | [Apache-2.0](https://huggingface.co/openbmb/VoxCPM2) |
| `microsoft/VibeVoice-1.5B` | 1.5B | 8% | 3.8 GB |  | Voice Clone, Multi-Speaker Dialogue | [MIT](https://huggingface.co/microsoft/VibeVoice-1.5B) |

## Music (5)

| model | params | NPU | size | context | can do | license |
|---|---|---|---|---|---|---|
| `RoyalCities/Foundation-1` | 2B | 5% | 1.4 GB |  |  | [Stability AI Community](https://huggingface.co/RoyalCities/Foundation-1) ⚠ |
| `m-a-p/YuE2-3B` | 3B | 14% | 5.4 GB |  |  | [CC-BY-NC-4.0](https://huggingface.co/m-a-p/YuE2-3B) ⚠ |
| `tencent/SongGeneration-v2-large` | 4B | 28% | 6.9 GB |  |  | [Tencent (custom)](https://huggingface.co/tencent/SongGeneration) ⚠ |
| `ACE-Step/AceStep-XL-Base` | 5B | 40% | 11.5 GB |  |  | [MIT](https://huggingface.co/ACE-Step/acestep-v15-xl-base) |
| `ACE-Step/AceStep-XL-Turbo` | 5B | 40% | 11.8 GB |  |  | [MIT](https://huggingface.co/ACE-Step/acestep-v15-xl-turbo) |

## 3D (2)

| model | params | NPU | size | context | can do | license |
|---|---|---|---|---|---|---|
| `microsoft/TRELLIS.2-4B` | 4B | 6% | 9.8 GB |  |  | [MIT](https://huggingface.co/microsoft/TRELLIS.2-4B) |
| `Tencent/Hunyuan3d-2.1` | 5.3B | 22% | 10.6 GB |  |  | [Tencent Hunyuan 3D Community](https://huggingface.co/Tencent/Hunyuan3d-2.1) ⚠ |

## Video (1)

| model | params | NPU | size | context | can do | license |
|---|---|---|---|---|---|---|
| `lightx2v/MiniMax-H3-Turbo` | 33B | 49% | 48.9 GB |  |  | [MiniMax H3 Community](https://huggingface.co/MiniMaxAI/MiniMax-H3) ⚠ |

## Embeddings (for search and the vault) (8)

| model | params | NPU | size | context | can do | license |
|---|---|---|---|---|---|---|
| `Qwen/Qwen3-Embedding-0.6B` | 0.6B | 2% | 0.9 GB | 8K |  | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) |
| `tencent/R3-embedding-0.6b` | 0.6B | 4% | 0.8 GB | 8K |  | [Apache-2.0](https://huggingface.co/tencent/R3-embedding-0.6b) |
| `nvidia/Nemotron-3-Embed-1B-BF16` | 1B | 7% | 1.3 GB | 4K |  | [OpenMDW-1.1](https://huggingface.co/nvidia/Nemotron-3-Embed-1B-BF16) |
| `Qwen/Qwen3-Vl-Embedding-2b` | 2B | 8% | 2.4 GB | 16K |  | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-Vl-Embedding-2b) |
| `Qwen/Qwen3-Embedding-8b` | 8B | 18% | 7.8 GB | 8K |  | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-Embedding-8b) |
| `nvidia/Nemotron-3-Embed-8b-Bf16` | 8B | 20% | 8.1 GB | 4K |  | [OpenMDW-1.1](https://huggingface.co/nvidia/Nemotron-3-Embed-8b-Bf16) |
| `Qwen/Qwen3-Vl-Embedding-8b` | 8B | 21% | 8.9 GB | 16K |  | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-Vl-Embedding-8b) |
| `Qwen/Qwen3-Embedding-4b` | 4B | 23% | 4.2 GB | 8K |  | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-Embedding-4b) |

## Rerankers (6)

| model | params | NPU | size | context | can do | license |
|---|---|---|---|---|---|---|
| `Qwen/Qwen3-Reranker-0.6B` | 0.6B | 2% | 0.7 GB | 8K |  | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B) |
| `tencent/R3-rerank-0.6b` | 0.6B | 3% | 0.8 GB | 8K |  | [Apache-2.0](https://huggingface.co/tencent/R3-rerank-0.6b) |
| `Qwen/Qwen3-Vl-Reranker-2b` | 2B | 8% | 2.3 GB | 16K |  | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-Vl-Reranker-2b) |
| `Qwen/Qwen3-Reranker-4b` | 4B | 10% | 4.2 GB | 8K |  | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-Reranker-4b) |
| `Qwen/Qwen3-Reranker-8b` | 8B | 16% | 7.8 GB | 8K |  | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-Reranker-8b) |
| `Qwen/Qwen3-Vl-Reranker-8b` | 8B | 21% | 8.4 GB | 16K |  | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-Vl-Reranker-8b) |

## Classifiers (Jev / System One, `POST /v1/systemone`) (7)

| model | params | NPU | size | context | can do | license |
|---|---|---|---|---|---|---|
| `vllm-sr/d3-lite` | 0.8B | 7% | 1.2 GB | 16K |  | [Apache-2.0](https://huggingface.co/vllm-sr/d3-lite) |
| `PelaAI/KnowLine-4B-Gen5.5` | 4B | 17% | 3.7 GB | 256K |  | [Apache-2.0](https://huggingface.co/PelaAI/KnowLine-4B-Gen5.5) |
| `vllm-sr/d3-edge` | 0.6B | 21% | 0.8 GB | 16K |  | [Apache-2.0](https://huggingface.co/vllm-sr/d3-edge) |
| `vllm-sr/d3-nano` | 2B | 25% | 2.5 GB | 16K |  | [Apache-2.0](https://huggingface.co/vllm-sr/d3-nano) |
| `vllm-sr/d3-mini` | 4B | 26% | 5.3 GB | 16K |  | [Apache-2.0](https://huggingface.co/vllm-sr/d3-mini) |
| `vllm-sr/d3-flash` | 9B | 34% | 9.9 GB | 16K |  | [Apache-2.0](https://huggingface.co/vllm-sr/d3-flash) |
| `PelaAI/KnowLine-35B-A3B-Gen1.5` | 35B | 48% | 17.7 GB | 256K |  | [Apache-2.0](https://huggingface.co/PelaAI/KnowLine-35B-A3B-Gen1.5) |
