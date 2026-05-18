import asyncio
from src.gemini_extractor import extract_land_certificate_with_gemini
from src.telegram_server import load_telegram_settings

async def main():
    settings = load_telegram_settings()
    f = r"data\uploads\089a557481db4ba7b386ee480b1e1d3e_1._AP_959405.pdf"
    print(f"Extracting {f}...")
    try:
        ext = extract_land_certificate_with_gemini(f, api_key=settings.gemini_api_key, model=settings.gemini_model)
        for asset in getattr(ext, "assets", []):
            print("Asset:")
            for k, v in asset.model_dump().items():
                if isinstance(v, dict) and "bounding_box" in v and v["bounding_box"]:
                    print(f"  {k}: {v['value']} -> box: {v['bounding_box']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
