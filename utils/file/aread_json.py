import json

import aiofiles


async def aread_content(path, mode="r", j=True):
    print("READ LOCAL CONTENT FROM", path)
    if not path:
        return None
    async with aiofiles.open(path, mode) as file:
        content = await file.read()
    if j:
        return json.loads(content)
    return content
