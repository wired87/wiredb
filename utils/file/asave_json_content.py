import os

import aiofiles



async def asave_json_content(path, content, mode="w", bucket_path=None):
    print("🔹 Saving Data Checkpoint...")

    # Ensure the directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)

    try:
        # 🔥 FIXED: Remove double `json.dumps()`
        async with aiofiles.open(path, mode=mode) as json_file:
            await json_file.write(content)  # <- `content` is already a string!

        print(f"✅ Checkpoint saved successfully at {path}")

    except Exception as e:
        print(f"❌ Error saving JSON: {e}")