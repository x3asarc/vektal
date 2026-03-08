import base64
import json
import os
import sys
import re
from pathlib import Path
from urllib import request as urllib_request
from urllib.error import HTTPError

def extract_key_from_env(env_path: Path, key_name: str) -> str:
    """Regex-based key extraction to avoid shell/parsing issues."""
    if not env_path.exists():
        return ""
    content = env_path.read_text(encoding="utf-8", errors="ignore")
    # Match key=value, handling quotes and potential trailing comments
    pattern = rf'^{key_name}\s*=\s*["\']?([^"\']\S+)["\']?.*$'
    match = re.search(pattern, content, re.MULTILINE)
    return match.group(1).strip() if match else ""

def encode_image(image_path: Path) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def main():
    repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / ".env"
    
    # Target the specific NEW OpenRouter key labeled for design process
    api_key = extract_key_from_env(env_path, "DESIGN_AUDIT_OPENROUTER_KEY")
    
    if not api_key:
        print("Error: DESIGN_AUDIT_OPENROUTER_KEY not found in .env. Checking fallback...")
        api_key = extract_key_from_env(env_path, "OPENROUTER_API_KEY")
    
    if not api_key:
        print("Error: No OpenRouter API key found in .env via regex extraction.")
        sys.exit(1)

    print(f"API Key located (starts with: {api_key[:10]}...)")

    images = [
        {"path": ".ooda/search_today.png", "label": "Search (Gold Standard)"},
        {"path": ".ooda/chat_today.png", "label": "Chat (Gold Standard)"},
        {"path": ".ooda/dashboard_polished.png", "label": "Current Dashboard (Remediated)"}
    ]

    content = [
        {
            "type": "text",
            "text": "You are a master Forensic Design Architect. I am providing you with three screenshots of a 'Forensic OS' dashboard. Two are 'Gold Standards' (Search and Chat) which have the desired high-fidelity visual DNA. The third is the 'Current Dashboard' which was recently remediated but the user is still unhappy with it.\n\nYour task:\n1. Perform a deep comparative analysis of the Visual DNA (Borders, Backgrounds, Spacing, Typography, Component Primitives).\n2. Identify exactly why the Dashboard still doesn't 'feel right' compared to the Gold Standards.\n3. Specifically address the 'randomness' and clutter at the top of the dashboard (the system pips and ribbon).\n4. Provide concrete, technical CSS/Tailwind recommendations to bridge the gap and achieve 100% congruence.\n5. Focus on 'the soul' of the design - the subtle glows, inner shadows, and vertical rhythm."
        }
    ]

    images_added = 0
    for img in images:
        img_path = repo_root / img["path"]
        if img_path.exists():
            print(f"Adding image: {img['label']} ({img['path']})")
            base64_image = encode_image(img_path)
            content.append({"type": "text", "text": f"--- {img['label']} ---"})
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
            })
            images_added += 1

    if images_added < 3:
        print(f"Warning: Only {images_added} images found. Audit may be incomplete.")

    payload = {
        "model": "google/gemini-3.1-flash-image-preview",
        "messages": [{"role": "user", "content": content}]
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://vektal.systems", # Updated to project domain
        "X-Title": "Vektal Design Architect Audit"
    }

    print("Calling OpenRouter (Gemini Nano Banana 2)...")
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
                output_file = repo_root / "reports/design/nano_banana_audit_v2.md"
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(analysis, encoding="utf-8")
                print(f"\nAnalysis complete. Report saved to: {output_file}")
                print("\n--- PREVIEW ---\n")
                print(analysis[:1000] + "...")
            else:
                print("Error: Unexpected response format from OpenRouter")
                print(json.dumps(result, indent=2))
    except HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode()}")
        sys.exit(1)
    except Exception as e:
        print(f"Error calling OpenRouter: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
