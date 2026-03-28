"""
Step 3: Use Qwen2-VL to analyze transcript + keyframes and decide where to cut.
This is the brain of the pipeline — it reads your editing prompts and outputs
structured JSON with cut points and editing instructions.
"""

import json
import re
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import torch


# ─── Default editing prompts (customize these!) ───────────────────────────────
DEFAULT_SYSTEM_PROMPT = """You are an expert video editor analyzing a seminar recording.
Your job is to split the video into logical, self-contained segments and identify any parts to remove.

You will receive:
1. A transcript with timestamps
2. Keyframe images from the video at regular intervals

OUTPUT RULES:
- Respond ONLY with valid JSON, no explanation, no markdown
- All timestamps must be in seconds (float)
- Be precise with cut points — prefer cutting at natural pauses in speech
"""

DEFAULT_USER_PROMPT = """Analyze this seminar video and return a JSON object with this exact structure:

{
  "segments": [
    {
      "title": "Short descriptive title",
      "start_seconds": 0.0,
      "end_seconds": 120.5,
      "keep": true,
      "reason": "Why this is a good segment"
    }
  ],
  "cuts_to_remove": [
    {
      "start_seconds": 45.2,
      "end_seconds": 67.8,
      "reason": "Filler / silence / off-topic"
    }
  ],
  "summary": "One paragraph summary of the full video"
}

EDITING INSTRUCTIONS:
- Split video into segments of 5-15 minutes each, by topic
- Remove any awkward silences longer than 5 seconds
- Remove filler introductions (e.g., speaker adjusting mic, waiting for audience)
- Remove Q&A sections that go off-topic
- Each segment should start and end at natural speech boundaries
- Mark segments as keep: false if they are low quality or off-topic
"""
# ──────────────────────────────────────────────────────────────────────────────


class VideoAnalyzer:
    def __init__(self, model_name: str = "Qwen/Qwen2-VL-7B-Instruct"):
        """Load Qwen2-VL model."""
        print(f"[Qwen2-VL] Loading model: {model_name}")
        print("[Qwen2-VL] This may take a few minutes on first run...")

        self.processor = AutoProcessor.from_pretrained(model_name)
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16,   # Memory efficient
            device_map="auto"              # Use GPU if available
        )
        print("[Qwen2-VL] Model loaded!")

    def analyze(
        self,
        transcript_text: str,
        keyframes: list[dict],
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        user_prompt: str = DEFAULT_USER_PROMPT,
        max_frames_to_send: int = 20
    ) -> dict:
        """
        Send transcript + keyframes to Qwen2-VL and get cut decisions.

        Args:
            transcript_text: Formatted transcript with timestamps
            keyframes: List of keyframe dicts (from keyframe_extractor)
            system_prompt: System instructions for the model
            user_prompt: Editing instructions / what to output
            max_frames_to_send: Limit frames sent (to manage token count)

        Returns:
            Parsed JSON dict with segments and cut decisions
        """
        # Sample frames evenly if too many
        if len(keyframes) > max_frames_to_send:
            step = len(keyframes) // max_frames_to_send
            keyframes = keyframes[::step][:max_frames_to_send]

        print(f"[Qwen2-VL] Sending {len(keyframes)} frames + transcript to model...")

        # Build message content: images + text
        content = []

        # Add keyframes
        for kf in keyframes:
            content.append({
                "type": "image",
                "image": f"data:image/jpeg;base64,{kf['base64']}",
            })
            content.append({
                "type": "text",
                "text": f"[Frame at {kf['timestamp_fmt']}]"
            })

        # Add transcript
        content.append({
            "type": "text",
            "text": f"\n\nTRANSCRIPT WITH TIMESTAMPS:\n{transcript_text}\n\n{user_prompt}"
        })

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]

        # Process inputs
        text_input = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text_input],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt"
        ).to(self.model.device)

        # Generate response
        print("[Qwen2-VL] Generating edit decisions...")
        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=2048,
                temperature=0.1,    # Low temp for consistent structured output
                do_sample=True
            )

        # Decode output
        trimmed = output_ids[:, inputs.input_ids.shape[1]:]
        response_text = self.processor.batch_decode(
            trimmed, skip_special_tokens=True
        )[0]

        print("[Qwen2-VL] Response received. Parsing JSON...")
        return self._parse_response(response_text)

    def _parse_response(self, response_text: str) -> dict:
        """Extract and parse JSON from model response."""
        # Strip markdown code blocks if present
        cleaned = re.sub(r"```(?:json)?", "", response_text).strip()
        cleaned = cleaned.strip("`").strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find JSON object within the text
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass

            print("[Qwen2-VL] WARNING: Could not parse JSON. Returning raw text.")
            return {"raw_response": response_text, "segments": [], "cuts_to_remove": []}