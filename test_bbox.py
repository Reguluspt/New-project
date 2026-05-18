import asyncio
from src.gemini_extractor import extract_land_certificate_with_gemini
from src.telegram_server import load_telegram_settings
import sys

async def main():
    settings = load_telegram_settings()
    import os
    from pathlib import Path
    uploads = Path(settings.upload_dir)
    files = list(uploads.glob("*.*"))
    if not files:
        print("No files found.")
        return
    for f in files:
        print(f"Extracting {f}...")
        try:
            ext = extract_land_certificate_with_gemini(str(f), api_key=settings.gemini_api_key, model=settings.gemini_model)
            for asset in getattr(ext, "assets", []):
                print("Asset:")
                for k, v in asset.model_dump().items():
                    if isinstance(v, dict) and "bounding_box" in v and v["bounding_box"]:
                        print(f"  {k}: {v['value']} -> box: {v['bounding_box']}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
