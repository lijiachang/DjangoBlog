from django.db import models

# Create your models here.
class AMDCPU:
    def __init__(self, row):
        # Ensure row has enough elements
        while len(row) < 25:
            row.append('')

        self.id = row[0]
        self.name = row[1]
        self.code1 = row[2]
        self.code2 = row[3]
        self.code3 = row[4]
        self.cores = row[5]
        self.threads = row[6]
        self.gpu_cores = row[7]
        self.base_clock = row[8]
        self.boost_clock = row[9]
        self.l1_cache = row[10]
        self.l2_cache = row[11]
        self.l3_cache = row[12]
        self.unlocked = row[13]
        self.process = row[14]
        self.socket = row[15]
        self.pcie = row[16]
        self.tdp = row[17]
        self.cTDP = row[18]
        self.max_temp = row[19]
        self.memory = row[20]
        self.memory_type = row[21]
        self.memory_channels = row[22]
        self.gpu_clock = row[23]
        self.gpu_name = row[24]

    def matches_search(self, search_term):
        search_term = str(search_term).strip().lower()
        print(search_term)
        print([self.code1, self.code2, self.code3])

        for code in [self.code1, self.code2, self.code3]:
            if code and search_term in str(code).lower():
                return True
        return False