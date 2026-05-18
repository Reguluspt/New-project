import asyncio
from src.gemini_extractor import extract_land_certificate_with_gemini
from src.telegram_server import load_telegram_settings
from src.image_annotator import annotate_document_with_bounding_boxes
from pathlib import Path
import os

async def main():
    settings = load_telegram_settings()
    # Find any file that has CI_715018 in its name
    import glob
    files = glob.glob(str(Path(settings.upload_dir) / "*CI_715018.pdf"))
    if not files:
        print("File not found")
        return
    f = files[0]
    print(f"Extracting {f}...")
    try:
        ext = extract_land_certificate_with_gemini(f, api_key=settings.gemini_api_key, model=settings.gemini_model)
        for asset in getattr(ext, "assets", []):
            print("Asset:")
            for k, v in asset.model_dump().items():
                if isinstance(v, dict) and "bounding_box" in v and v["bounding_box"]:
                    print(f"  {k}: {v['value']} -> box: {v['bounding_box']}")
        
        # Test annotating
        out_dir = Path("test_annotated")
        out_dir.mkdir(exist_ok=True)
        annotated_path = annotate_document_with_bounding_boxes(f, ext, str(out_dir))
        print(f"Annotated saved to {annotated_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
