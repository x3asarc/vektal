import base64
import json
import os
import sys
import re
from pathlib import Path
from urllib import request as urllib_request
from urllib.error import HTTPError

def extract_key_from_env(env_path: Path, key_name: str) -> str:
    if not env_path.exists():
        return ""
    content = env_path.read_text(encoding="utf-8", errors="ignore")
    pattern = rf'^{key_name}\s*=\s*["\']?([^"\']\S+)["\']?.*$'
    match = re.search(pattern, content, re.MULTILINE)
    return match.group(1).strip() if match else ""

def encode_image(image_path: Path) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def main():
    repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / ".env"
    api_key = extract_key_from_env(env_path, "DESIGN_AUDIT_OPENROUTER_KEY")
    if not api_key:
        api_key = extract_key_from_env(env_path, "OPENROUTER_API_KEY")
    
    if not api_key:
        print("Error: No OpenRouter API key found.")
        sys.exit(1)

    images = [
        {"path": ".ooda/final_search_proof.png", "label": "Search (Anchor Source of Truth)"},
        {"path": ".ooda/final_chat_proof.png", "label": "Chat (Anchor Source of Truth)"},
        {"path": ".ooda/final_dashboard_proof.png", "label": "RE-ANCHORED Dashboard (The Implementation)"}
    ]

    content = [
        {
            "type": "text",
            "text": "You are a master Forensic Design Architect. I have just performed a radical re-anchoring of the Vektal OS Dashboard. Previously, it looked like a 'broken terminal' or 'random text output'.\n\nYour task:\n1. Verify if the Dashboard (image_2.png) is now structurally and visually IDENTICAL in behavior and persona to the Search/Chat anchors (image_0 and image_1).\n2. Look specifically at the LAYOUT: Does it use the correct page-header, page-title, and page-body rhythm?\n3. Look at the COMPONENTS: Are the L-bracket corner pips and inner bevels present and consistent with the design system source of truth?\n4. State clearly if the Dashboard now 'fits' or if it still feels like an outlier."
        }
    ]

    for img in images:
        img_path = repo_root / img["path"]
        if img_path.exists():
            base64_image = encode_image(img_path)
            content.append({"type": "text", "text": f"--- {img['label']} ---"})
            content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}})

    payload = {
        "model": "google/gemini-3.1-flash-image-preview",
        "messages": [{"role": "user", "content": content}]
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://vektal.systems",
        "X-Title": "Vektal Identity Re-Anchoring Audit"
    }

    print("Calling OpenRouter (Gemini Nano Banana 2) for Identity Verification...")
    req = urllib_request.Request(
        url="https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib_request.urlopen(req, timeout=180) as response:
            body = response.read().decode("utf-8", errors="ignore")
            result = json.loads(body)
            if "choices" in result:
                analysis = result["choices"][0]["message"]["content"]
                output_file = repo_root / "reports/design/identity_reanchoring_report.md"
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(analysis, encoding="utf-8")
                print(f"\nIdentity Audit Complete. Report: {output_file}")
                print("\n--- PREVIEW ---\n")
                print(analysis[:1500] + "...")
            else:
                print("Error: Unexpected response format.")
    except Exception as e:
        print(f"Error calling OpenRouter: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
