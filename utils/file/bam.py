"""

{'_io': <bamnostic.base.AlignmentFile object at 0x0000014C2CE31100>,
 '_byte_stream': bytearray(b''),
 '_raw_stream': bytearray(b'\x0f\x01\x00\x004\x00\x00\x00\x8aM\x00\x00'
                          b'$\x00J\x12\x01\x00\x10\x00P\x00\x00\x00'...
 'refID': 52,
 'pos': 19850,
 '_bin_mq_nl': 306839588,
 '_flag_nc': 1048577,
 'bin': 4682,
 'mapq': 0,
 '_l_read_name': 36,
 'flag': 16,
 '_n_cigar_op': 1,
 'l_seq': 80,
 'next_refID': -1,
 'next_pos': -1,
 'tlen': 0,
 'tid': 52,
 'reference_id': 52,
 'reference_name': 'chr15_KI270727v1_random',
 '_cigar': (1280,),

              ...
 'query_qualities': array('B', [255, 255, ...
 'tags': {'ms': ('C', 80),
          'AS': ('C', 80),
 'cigarstring': '80M',
 '_cigartuples': [Cigar(op_code=0, n_op=80, op_id='M', op_name='BAM_CMATCH')],
 'cigartuples': [(0, 80)],
 'cigar': [(0, 80)],


last e:❌ Error reading BAM read: 'str' object has no attribute 'readlines'

"""
import asyncio
import itertools
import bamnostic

"""from ggoogle.spanner.acore import ASpannerManager
from qbrain.utils.utils import GraphUtils"""


class BAMReadsProcessor(
    #ASpannerManager
):


    """
    Todo:
    eges für EDQ sind extrem fehlerhaft. beim übernehmen in spanner eges neu definieren

    """

    def __init__(self, bam_path, table):
        #ASpannerManager.__init__(self)
        self.ref_file_ckpt = "ref_file_ckpt.json"
        self.bam_path = bam_path

        self.g_utils = None #GraphUtils(table_name=table, upload_to="bq")
        self.all_ids = self.g_utils.get_ids()

        print("create bam object from", bam_path)
        self.bam_file = bamnostic.AlignmentFile(
            filepath_or_object=bam_path
        )
        print("Raw bam file set")

        self.gene_stuff = self.g_utils.get_gene_id_name(chrom=True)

        self.layer = table
        print("Table set:", self.layer)
        self.read_annotations = {}

        self.max_concurrent_tasks = 10000
        self.loop_count = 0



    def classify_chrom(self, eattrs, nattrs, read):
        chrom = self.get_chrom(read.reference_name)
        nattrs["id"] = read.read_name
        if chrom.startswith("ERCC"):
            eattrs["trt"] = chrom
            eattrs["trgt_layer"] = "ERCC"
            eattrs["rel"] = "artificial_sequence"
        else:
            nattrs["chrom"] = chrom
            eattrs["trt"] = self.find_gene_by_position(pos=read.pos, chrom=chrom)
            eattrs["trgt_layer"] = "GENE"
            eattrs["rel"] = "expressed_in"
        return nattrs, eattrs


    def main(self):
        print("Creating tasks")
        while True:
            batch_chunk = list(itertools.islice(self.bam_file, self.max_concurrent_tasks))
            if not batch_chunk:
                break
            for read in batch_chunk:
                self._process(read)

        print("Finished")

    def _process(self, read):
        """returns dict and bq schema"""
        #pprint.pp(read.__dict__)
        #await asyncio.sleep(99)
        try:
            if read.read_name in self.all_ids:
                print("Skipping", read.read_name)
                return

            print("Appending", read.read_name)
            nattrs=dict()
            eattrs=dict()

            nattrs, eattrs=self.classify_chrom(nattrs, eattrs, read)

            nattrs.update(dict(
                id=read.read_name,
                type=self.layer,
                seq=read.seq,
                start=read.pos,
                end=read.pos+read.l_seq,
                strand_flag=read.flag,
                quality=self.compute_quality_score(read.query_qualities),
                cigar=[f"{op}_{length}" for op, length in read.cigar if read.cigar and len(read.cigar)>0]
            ))

            eattrs.update(dict(
                src=nattrs["id"],
                src_layer=self.layer,
            ))
            #pprint.pp(nattrs)
            #pprint.pp(eattrs)

            self.g_utils.add_node(attrs=nattrs)
            self.g_utils.add_edge(attrs=eattrs)

            if self.loop_count >= self.max_concurrent_tasks:
                asyncio.run(self.g_utils.abatch_commit())
                self.loop_count = 0
            self.loop_count += 1
        except Exception as e:
            print(f"❌ Error reading BAM read: {e}")


    def get_chrom(self, rname):
        chrom = rname.split("_")[0].replace("chr", "")
        print("chrom", chrom)
        return chrom


    def find_gene_by_position(self, pos: int, chrom):
        for row in self.gene_stuff:
            try:
                start = row.get('start')
                end = row.get('end')
                print("start", start, end)
                if start and end and str(chrom) == str(row.get("chrom", "")) and start <= pos <= end:
                    gene_id= row.get("id", None)
                    print("Found gene", gene_id)
                    return gene_id
            except Exception as e:
                print("Skipping invalid row", row, e)
        return None


    def compute_quality_score(self, qualities):
        if not qualities:
            return 0
        return round(sum(qualities) / len(qualities), 2)


if __name__ == "__main__":
    pass
