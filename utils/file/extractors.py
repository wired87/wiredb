import requests


class FileExtractor:
    def __init__(self, source):
        self.source = source  # Can be a file path or a URL

    async def extract(self):
        raise NotImplementedError("Subclasses must implement this")


class SimpleBigWigAlternative:
    def __init__(self, source):
        self.source = source

    async def extract(self):
        if self.source.startswith("http"):
            resp = requests.get(self.source)
            content = resp.content.decode()
        else:
            with open(self.source, "r") as f:
                content = f.read()

        data = []
        for i, line in enumerate(content.strip().splitlines()):
            parts = line.split()
            if len(parts) == 4:
                chrom, start, end, value = parts
                data.append({
                    "id": f"{chrom}_{start}_{i}",
                    "chrom": chrom,
                    "start": int(start),
                    "end": int(end),
                    "value": float(value)
                })

        return data


class HiCExtractor(FileExtractor):
    async def extract(self):
        # This assumes a simple .hic matrix dump format (external tools might be needed for preprocessing)
        import subprocess
        import tempfile

        if self.source.startswith("http"):
            raise NotImplementedError("Download .hic files first, then pass local path")

        tmp = tempfile.NamedTemporaryFile(delete=False)
        output = subprocess.check_output(["hicDumpMatrix", "--matrix", self.source, "--outFileName", tmp.name])

        data = []
        with open(tmp.name) as f:
            for i, line in enumerate(f):
                data.append({"id": f"entry_{i}", "content": line.strip()})
        return data


class BEPEExtractor(FileExtractor):
    async def extract(self):
        # Assuming it's some form of structured text
        import aiofiles

        data = []
        async with aiofiles.open(self.source, mode='r') as f:
            i = 0
            async for line in f:
                if line.strip():
                    data.append({"id": f"bepe_{i}", "content": line.strip()})
                    i += 1
        return data


class GZExtractor(FileExtractor):
    async def extract(self):
        import gzip
        import aiofiles

        data = []
        with gzip.open(self.source, 'rt') as f:
            for i, line in enumerate(f):
                data.append({"id": f"gz_{i}", "content": line.strip()})
        return data
